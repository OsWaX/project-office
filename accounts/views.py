from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.forms import CategoryForm, DepartmentForm, MemberForm
from accounts.models import Department
from accounts.permissions import is_manager, manager_required
from kpi import services as kpi
from tasks.models import Category, Task

User = get_user_model()


@manager_required
def team_list(request):
    today = timezone.localdate()
    month = kpi.first_of_month(today)
    show_inactive = request.GET.get("inactive") == "1"
    members = (
        User.objects.select_related("profile", "profile__department")
        .annotate(
            active=Count("assigned_tasks", filter=Q(assigned_tasks__status__in=Task.ACTIVE_STATUSES)),
            overdue=Count(
                "assigned_tasks",
                filter=Q(
                    assigned_tasks__status__in=Task.OPEN_STATUSES,
                    assigned_tasks__deadline__lt=today,
                ),
            ),
            done_month=Count(
                "assigned_tasks",
                filter=Q(
                    assigned_tasks__status=Task.Status.DONE,
                    assigned_tasks__completed_at__date__gte=month,
                ),
            ),
        )
        .order_by("profile__department__name", "last_name", "first_name")
    )
    if not show_inactive:
        members = members.filter(is_active=True)
    rows, _period = kpi.month_results(month, today)
    scores = {row["user_id"]: row for row in rows}
    for member in members:
        member.kpi = scores.get(member.pk)
    return render(
        request,
        "accounts/team_list.html",
        {
            "members": members,
            "month": month,
            "show_inactive": show_inactive,
            "departments": Department.objects.annotate(n=Count("members")),
            "categories": Category.objects.filter(is_active=True).annotate(n=Count("tasks")),
            "department_form": DepartmentForm(),
            "kpi_settings": kpi.KPISettings.load(),
        },
    )


@login_required
def member_detail(request, pk):
    member = get_object_or_404(User.objects.select_related("profile", "profile__department"), pk=pk)
    if not (is_manager(request.user) or request.user.pk == member.pk):
        raise PermissionDenied
    today = timezone.localdate()
    tasks = Task.objects.filter(assignee=member).select_related("category")
    history = kpi.history(member, 6, today)
    return render(
        request,
        "accounts/member_detail.html",
        {
            "member": member,
            "history": history,
            "current": kpi.employee_result(member, kpi.first_of_month(today), today),
            "active_tasks": tasks.active().order_by("deadline"),
            "recent_done": tasks.filter(status=Task.Status.DONE).order_by("-completed_at")[:10],
            "stats": tasks.aggregate(
                total=Count("id"),
                done=Count("id", filter=Q(status=Task.Status.DONE)),
                overdue=Count("id", filter=Q(status__in=Task.OPEN_STATUSES, deadline__lt=today)),
            ),
        },
    )


@manager_required
def member_create(request):
    form = MemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, _("Team member added. Give them their login and password."))
        return redirect("accounts:member", pk=user.pk)
    return render(request, "accounts/member_form.html", {"form": form})


@manager_required
def member_edit(request, pk):
    member = get_object_or_404(User, pk=pk)
    if member.is_superuser and not request.user.is_superuser:
        raise PermissionDenied
    form = MemberForm(request.POST or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Changes saved."))
        return redirect("accounts:member", pk=member.pk)
    return render(request, "accounts/member_form.html", {"form": form, "member": member})


@manager_required
def department_create(request):
    return _add_named(request, DepartmentForm, _("Department added."))


@manager_required
def category_create(request):
    return _add_named(request, CategoryForm, _("Task type added."))


def _add_named(request, form_class, success_message):
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, success_message)
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    return redirect("accounts:team")
