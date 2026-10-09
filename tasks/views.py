from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.permissions import is_manager, manager_required
from kpi import services as kpi
from tasks import services
from tasks.forms import (
    COMPLEXITY_HELP,
    ApproveForm,
    AttachmentForm,
    CommentForm,
    ProgressForm,
    ReturnForm,
    SimpleActionForm,
    TaskCreateForm,
    TaskEditForm,
    TaskFilterForm,
    save_attachment,
)
from tasks.models import Notification, Task, TaskAttachment

SORTS = {
    "deadline": ("deadline", "-priority", "id"),
    "-deadline": ("-deadline", "-priority", "-id"),
    "priority": ("-priority", "deadline", "id"),
    "complexity": ("-complexity", "deadline", "id"),
    "created": ("-created_at", "-id"),
    "assignee": ("assignee__last_name", "assignee__first_name", "deadline"),
}


def _task_queryset(user):
    return (
        Task.objects.visible_to(user)
        .select_related("assignee", "assignee__profile", "category", "created_by")
    )


@login_required
def dashboard(request):
    user = request.user
    today = timezone.localdate()
    month = kpi.first_of_month(today)
    manager = is_manager(user)
    tasks = _task_queryset(user)
    week_ahead = today + timedelta(days=7)

    status_counts = {
        row["status"]: row["n"]
        for row in tasks.active().order_by().values("status").annotate(n=Count("id"))
    }
    active_breakdown = [
        {"status": status, "label": Task.Status(status).label, "count": status_counts.get(status, 0)}
        for status in Task.ACTIVE_STATUSES
    ]
    active_total = sum(item["count"] for item in active_breakdown)
    for item in active_breakdown:
        item["share"] = round(100 * item["count"] / active_total, 1) if active_total else 0

    context = {
        "today": today,
        "month": month,
        "active_total": active_total,
        "active_breakdown": active_breakdown,
        "overdue_count": tasks.overdue(today).count(),
        "review_count": tasks.filter(status=Task.Status.ON_REVIEW).count(),
        "done_this_month": tasks.filter(
            status=Task.Status.DONE, completed_at__date__gte=month
        ).count(),
        "overdue_tasks": tasks.overdue(today).order_by("deadline")[:8],
        "upcoming_tasks": tasks.filter(
            status__in=Task.OPEN_STATUSES, deadline__gte=today, deadline__lte=week_ahead
        ).order_by("deadline", "-priority")[:8],
    }

    if manager:
        context["review_tasks"] = tasks.filter(status=Task.Status.ON_REVIEW).order_by("submitted_at")[:8]
        rows, period = kpi.month_results(month, today)
        load = {
            row["assignee"]: row
            for row in Task.objects.order_by().values("assignee").annotate(
                active=Count("id", filter=Q(status__in=Task.ACTIVE_STATUSES)),
                overdue=Count("id", filter=Q(status__in=Task.OPEN_STATUSES, deadline__lt=today)),
                review=Count("id", filter=Q(status=Task.Status.ON_REVIEW)),
            )
        }
        for row in rows:
            counts = load.get(row["user_id"], {})
            row["active_now"] = counts.get("active", 0)
            row["overdue_now"] = counts.get("overdue", 0)
            row["review_now"] = counts.get("review", 0)
        context["team_rows"] = rows
        context["kpi_settings"] = kpi.KPISettings.load()
    else:
        context["my_kpi"] = kpi.employee_result(user, month, today)
        context["my_tasks"] = tasks.active().order_by("deadline", "-priority")[:10]

    return render(request, "tasks/dashboard.html", context)


@login_required
def task_list(request):
    manager = is_manager(request.user)
    form = TaskFilterForm(request.GET or None, manager=manager)
    qs = form.filter(_task_queryset(request.user))
    sort = request.GET.get("sort", "deadline")
    qs = qs.order_by(*SORTS.get(sort, SORTS["deadline"]))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    query_without_sort = query.copy()
    query_without_sort.pop("sort", None)
    return render(
        request,
        "tasks/task_list.html",
        {
            "form": form,
            "page": page,
            "sort": sort,
            "query": query.urlencode(),
            "query_without_sort": query_without_sort.urlencode(),
            "total": page.paginator.count,
        },
    )


@manager_required
def task_create(request):
    form = TaskCreateForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        data = {
            name: form.cleaned_data[name]
            for name in ("title", "description", "category", "complexity", "priority", "deadline")
        }
        created = services.create_tasks(
            data, form.cleaned_data["assignees"], request.user, form.cleaned_data["files"]
        )
        if len(created) == 1:
            messages.success(request, _("Task created and sent to the executor."))
            return redirect(created[0])
        messages.success(
            request, _("%(count)s tasks created, one for each executor.") % {"count": len(created)}
        )
        return redirect("tasks:list")
    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "complexity_help": COMPLEXITY_HELP,
            "complexity_points": kpi.KPISettings.load().complexity_points(),
            "creating": True,
        },
    )


def _get_visible_task(request, pk):
    task = get_object_or_404(
        Task.objects.select_related("assignee", "assignee__profile", "created_by", "category"), pk=pk
    )
    if not task.can_view(request.user):
        raise PermissionDenied
    return task


@login_required
def task_detail(request, pk):
    task = _get_visible_task(request, pk)
    actions = services.available_actions(task, request.user)
    can_progress = task.is_open and (
        task.assignee_id == request.user.pk or is_manager(request.user)
    )
    context = {
        "task": task,
        "actions": actions,
        "action_labels": services.ACTION_LABELS,
        "approve_form": ApproveForm(),
        "return_form": ReturnForm(),
        "simple_form": SimpleActionForm(),
        "progress_form": ProgressForm(initial={"progress": task.progress}) if can_progress else None,
        "comment_form": CommentForm(),
        "attachment_form": AttachmentForm(),
        "comments": task.comments.select_related("author"),
        "attachments": task.attachments.select_related("uploaded_by"),
        "events": task.events.select_related("actor")[:50],
        "complexity_points": kpi.KPISettings.load().complexity_points()[task.complexity],
    }
    Notification.objects.filter(recipient=request.user, task=task, is_read=False).update(is_read=True)
    return render(request, "tasks/task_detail.html", context)


@manager_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    form = TaskEditForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        services.save_task_edit(form, request.user)
        messages.success(request, _("Task updated."))
        return redirect(task)
    return render(
        request,
        "tasks/task_form.html",
        {
            "form": form,
            "task": task,
            "complexity_help": COMPLEXITY_HELP,
            "complexity_points": kpi.KPISettings.load().complexity_points(),
            "creating": False,
        },
    )


@login_required
@require_POST
def task_action(request, pk, action):
    task = _get_visible_task(request, pk)
    form_class = {"approve": ApproveForm, "return": ReturnForm}.get(action, SimpleActionForm)
    form = form_class(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect(task)
    try:
        services.perform_action(
            task,
            request.user,
            action,
            rating=form.cleaned_data.get("rating"),
            comment=form.cleaned_data.get("comment", ""),
        )
    except services.WorkflowError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("Done: %(action)s.") % {"action": services.ACTION_LABELS[action]})
    return redirect(task)


@login_required
@require_POST
def task_progress(request, pk):
    task = _get_visible_task(request, pk)
    form = ProgressForm(request.POST)
    if form.is_valid():
        try:
            services.update_progress(task, request.user, form.cleaned_data["progress"])
            messages.success(request, _("Progress saved."))
        except services.WorkflowError as exc:
            messages.error(request, str(exc))
    return redirect(task)


@login_required
@require_POST
def task_comment(request, pk):
    task = _get_visible_task(request, pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        services.add_comment(task, request.user, form.cleaned_data["text"])
    return redirect(f"{task.get_absolute_url()}#comments")


@login_required
@require_POST
def task_attach(request, pk):
    task = _get_visible_task(request, pk)
    if task.is_closed and not is_manager(request.user):
        raise PermissionDenied
    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        for f in form.cleaned_data["files"]:
            save_attachment(task, request.user, f)
        messages.success(request, _("Files attached."))
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect(f"{task.get_absolute_url()}#files")


@login_required
def attachment_download(request, pk):
    attachment = get_object_or_404(TaskAttachment.objects.select_related("task"), pk=pk)
    if not attachment.task.can_view(request.user):
        raise PermissionDenied
    try:
        handle = attachment.file.open("rb")
    except FileNotFoundError:
        raise Http404
    return FileResponse(handle, as_attachment=True, filename=attachment.original_name)


@login_required
@require_POST
def attachment_delete(request, pk):
    attachment = get_object_or_404(TaskAttachment.objects.select_related("task"), pk=pk)
    task = attachment.task
    if not (is_manager(request.user) or attachment.uploaded_by_id == request.user.pk):
        raise PermissionDenied
    if task.is_closed and not is_manager(request.user):
        raise PermissionDenied
    attachment.file.delete(save=False)
    attachment.delete()
    messages.success(request, _("File deleted."))
    return redirect(f"{task.get_absolute_url()}#files")


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("actor", "task")[:100]
    return render(request, "tasks/notifications.html", {"notifications": notifications})


@login_required
def notification_open(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return redirect(notification.task)


@login_required
@require_POST
def notification_read_all(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect("tasks:notifications")
