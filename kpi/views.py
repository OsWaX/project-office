from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.permissions import is_manager, manager_required
from kpi import services
from kpi.export import build_workbook
from kpi.forms import AdjustmentForm, KPISettingsForm
from kpi.models import KPIAdjustment, KPISettings
from tasks.models import Task

User = get_user_model()


def _month_context(request):
    today = timezone.localdate()
    month = services.parse_month(request.GET.get("month") or request.POST.get("month"), today)
    current = services.first_of_month(today)
    return {
        "month": month,
        "month_param": month.strftime("%Y-%m"),
        "month_label": formats.date_format(month, "F Y"),
        "prev_month": services.shift_month(month, -1).strftime("%Y-%m"),
        "next_month": services.shift_month(month, 1).strftime("%Y-%m") if month < current else None,
        "is_current_month": month == current,
        "today": today,
    }


def _kpi_url(name, month, **kwargs):
    return f"{reverse(name, kwargs=kwargs or None)}?month={month:%Y-%m}"


def _summary(rows):
    scored = [row["score"] for row in rows if row["score"] is not None]
    return {
        "people": len(scored),
        "average": round(sum(scored) / len(scored), 1) if scored else None,
        "pending": sum(row["pending"] for row in rows),
        "grades": {
            grade: sum(1 for row in rows if row["grade"] == grade) for grade in services.GRADE_LABELS
        },
    }


@manager_required
def kpi_month(request):
    ctx = _month_context(request)
    rows, period = services.month_results(ctx["month"], ctx["today"])
    ctx.update(
        rows=rows,
        period=period,
        summary=_summary(rows),
        grade_labels=services.GRADE_LABELS,
        kpi_settings=period.settings_snapshot if period else KPISettings.load().as_dict(),
    )
    return render(request, "kpi/month.html", ctx)


@login_required
def kpi_employee(request, user_id):
    if not (is_manager(request.user) or request.user.pk == user_id):
        raise PermissionDenied
    member = get_object_or_404(User.objects.select_related("profile", "profile__department"), pk=user_id)
    ctx = _month_context(request)
    period = services.get_period(ctx["month"])
    row = services.employee_result(member, ctx["month"], ctx["today"], period=period)
    kpi_settings = KPISettings.load()
    ctx.update(
        member=member,
        row=row,
        period=period,
        kpi_settings=period.settings_snapshot if period else kpi_settings.as_dict(),
        component_labels=services.COMPONENT_LABELS,
        outcome_labels=services.OUTCOME_LABELS,
        grade_labels=services.GRADE_LABELS,
        complexity_labels=dict(Task.Complexity.choices),
        status_labels=dict(Task.Status.choices),
        adjustment_form=AdjustmentForm(max_points=kpi_settings.max_adjustment),
        history=services.history(member, 6, ctx["today"]),
    )
    return render(request, "kpi/employee.html", ctx)


@manager_required
@require_POST
def kpi_adjust(request, user_id):
    member = get_object_or_404(User, pk=user_id)
    ctx = _month_context(request)
    if services.get_period(ctx["month"]):
        messages.error(request, _("This month is finalised. Reopen it to make changes."))
    else:
        form = AdjustmentForm(request.POST, max_points=KPISettings.load().max_adjustment)
        if form.is_valid():
            KPIAdjustment.objects.create(
                employee=member,
                month=ctx["month"],
                points=form.cleaned_data["points"],
                reason=form.cleaned_data["reason"],
                created_by=request.user,
            )
            messages.success(request, _("Adjustment saved."))
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    return redirect(_kpi_url("kpi:employee", ctx["month"], user_id=member.pk))


@manager_required
@require_POST
def kpi_adjust_delete(request, pk):
    adjustment = get_object_or_404(KPIAdjustment, pk=pk)
    if services.get_period(adjustment.month):
        messages.error(request, _("This month is finalised. Reopen it to make changes."))
    else:
        adjustment.delete()
        messages.success(request, _("Adjustment removed."))
    return redirect(_kpi_url("kpi:employee", adjustment.month, user_id=adjustment.employee_id))


@manager_required
@require_POST
def kpi_finalize(request):
    ctx = _month_context(request)
    if services.get_period(ctx["month"]):
        messages.info(request, _("This month is already finalised."))
    elif ctx["is_current_month"]:
        messages.error(request, _("The current month can be finalised once it is over."))
    else:
        services.finalize(ctx["month"], request.user, ctx["today"])
        messages.success(request, _("KPI for %(month)s finalised.") % {"month": ctx["month_label"]})
    return redirect(_kpi_url("kpi:month", ctx["month"]))


@manager_required
@require_POST
def kpi_reopen(request):
    ctx = _month_context(request)
    services.reopen(ctx["month"])
    messages.success(
        request, _("%(month)s reopened: results are live again.") % {"month": ctx["month_label"]}
    )
    return redirect(_kpi_url("kpi:month", ctx["month"]))


@manager_required
def kpi_export(request):
    ctx = _month_context(request)
    rows, period = services.month_results(ctx["month"], ctx["today"])
    content = build_workbook(ctx["month_label"], rows, period, settings.ORGANIZATION_NAME)
    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="kpi-{ctx["month_param"]}.xlsx"'
    return response


@manager_required
def kpi_print(request):
    ctx = _month_context(request)
    rows, period = services.month_results(ctx["month"], ctx["today"])
    ctx.update(rows=rows, period=period, grade_labels=services.GRADE_LABELS, summary=_summary(rows))
    return render(request, "kpi/print.html", ctx)


@manager_required
def kpi_settings(request):
    instance = KPISettings.load()
    form = KPISettingsForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request, _("KPI settings saved. Finalised months keep the settings they were calculated with.")
        )
        return redirect("kpi:settings")
    return render(request, "kpi/settings.html", {"form": form})


@login_required
def methodology(request):
    return render(
        request,
        "kpi/methodology.html",
        {"kpi_settings": KPISettings.load(), "grade_labels": services.GRADE_LABELS},
    )
