"""Monthly KPI calculation.

The method is deliberately simple so every employee can check their own score
(it is also explained on the in-portal "Methodology" page):

* A task belongs to the month in which its deadline falls. Cancelled tasks are
  ignored. Each task is worth complexity points (by default 1/2/3/5).
* A task is *assessed* once it is completed, or once its deadline has passed
  without completion (then it counts as failed). Tasks still waiting for the
  manager's review are *pending* and not assessed yet, so an employee is never
  penalised for a slow review.
* Components, each 0–100:
    execution   = points of completed tasks / points of assessed tasks
    timeliness  = points of tasks handed in by the deadline / points assessed
    quality     = average manager rating (1–5) weighted by points, as a share of 5
    workload    = points completed / monthly norm (capped at 100; the norm is
                  pro-rated for the current month)
* Base score = weighted average of the components (weights from settings).
* Final KPI = base score + manager adjustments, kept within 0–100.
"""

import calendar
from dataclasses import asdict, dataclass, field
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Profile
from kpi.models import KPIAdjustment, KPIPeriod, KPISettings
from tasks.models import Task

User = get_user_model()

COMPONENTS = ("completion", "timeliness", "quality", "workload")

COMPONENT_LABELS = {
    "completion": _("Execution"),
    "timeliness": _("Timeliness"),
    "quality": _("Quality"),
    "workload": _("Workload"),
}

GRADE_LABELS = {
    "excellent": _("Excellent"),
    "good": _("Good"),
    "satisfactory": _("Satisfactory"),
    "unsatisfactory": _("Unsatisfactory"),
}

OUTCOME_LABELS = {
    "on_time": _("Done on time"),
    "late": _("Done late"),
    "failed": _("Not done by deadline"),
    "pending": _("Awaiting review"),
    "upcoming": _("Deadline not reached"),
}


# --- month helpers -------------------------------------------------------------------------


def first_of_month(d):
    return d.replace(day=1)


def month_end(month):
    return month.replace(day=calendar.monthrange(month.year, month.month)[1])


def shift_month(month, delta):
    index = month.year * 12 + month.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


def parse_month(value, today=None):
    """Parse "YYYY-MM"; fall back to the current month and never go into the future."""
    current = first_of_month(today or timezone.localdate())
    try:
        year, month = (int(part) for part in (value or "").split("-"))
        parsed = date(year, month, 1)
    except (TypeError, ValueError):
        return current
    return min(parsed, current)


# --- calculation ---------------------------------------------------------------------------


@dataclass
class KPIResult:
    user_id: int
    name: str
    position: str = ""
    department: str = ""
    month: str = ""
    tasks_total: int = 0
    assessed: int = 0
    done: int = 0
    on_time: int = 0
    late: int = 0
    failed: int = 0
    pending: int = 0
    upcoming: int = 0
    points_assessed: int = 0
    points_done: int = 0
    points_on_time: int = 0
    quality_avg: float | None = None
    norm: float | None = None
    norm_full: int = 0
    completion: float | None = None
    timeliness: float | None = None
    quality: float | None = None
    workload: float | None = None
    base_score: float | None = None
    adjustment: int = 0
    score: float | None = None
    grade: str | None = None
    tasks: list = field(default_factory=list)
    adjustments: list = field(default_factory=list)


def grade_for(score, kpi_settings):
    if score is None:
        return None
    if score >= kpi_settings.grade_excellent:
        return "excellent"
    if score >= kpi_settings.grade_good:
        return "good"
    if score >= kpi_settings.grade_satisfactory:
        return "satisfactory"
    return "unsatisfactory"


def task_outcome(task, today):
    if task.status == Task.Status.DONE:
        return "on_time" if task.submitted_on_time else "late"
    if task.status == Task.Status.ON_REVIEW:
        return "pending"
    return "failed" if task.deadline < today else "upcoming"


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else None


def calculate(user, month, tasks, adjustments, kpi_settings, today):
    """KPI of one person for one month, from that month's tasks and adjustments."""
    points = kpi_settings.complexity_points()
    profile = getattr(user, "profile", None)
    result = KPIResult(
        user_id=user.pk,
        name=user.get_full_name() or user.username,
        position=getattr(profile, "position", "") or "",
        department=str(profile.department) if profile and profile.department else "",
        month=month.strftime("%Y-%m"),
    )

    rating_points = rating_sum = 0
    for task in tasks:
        outcome = task_outcome(task, today)
        weight = points[task.complexity]
        result.tasks_total += 1
        setattr(result, outcome, getattr(result, outcome) + 1)
        if outcome in ("on_time", "late", "failed"):
            result.assessed += 1
            result.points_assessed += weight
        if outcome in ("on_time", "late"):
            result.done += 1
            result.points_done += weight
            if task.quality_rating:
                rating_points += weight
                rating_sum += weight * task.quality_rating
        if outcome == "on_time":
            result.points_on_time += weight
        result.tasks.append(
            {
                "id": task.pk,
                "title": task.title,
                "complexity": task.complexity,
                "points": weight,
                "deadline": task.deadline.isoformat(),
                "submitted": timezone.localdate(task.submitted_at).isoformat()
                if task.submitted_at
                else None,
                "status": task.status,
                "outcome": outcome,
                "rating": task.quality_rating,
            }
        )

    norm_full = kpi_settings.default_monthly_norm
    if profile and profile.monthly_norm is not None:
        norm_full = profile.monthly_norm
    result.norm_full = norm_full

    if result.assessed:
        result.completion = _pct(result.points_done, result.points_assessed)
        result.timeliness = _pct(result.points_on_time, result.points_assessed)
        if rating_points:
            result.quality_avg = round(rating_sum / rating_points, 2)
            result.quality = round(rating_sum / rating_points / 5 * 100, 1)
        if norm_full:
            norm = float(norm_full)
            if first_of_month(today) == month:
                days = calendar.monthrange(month.year, month.month)[1]
                norm = norm * today.day / days
            result.norm = round(norm, 1)
            result.workload = min(100.0, _pct(result.points_done, norm))

    weights = {
        "completion": kpi_settings.weight_completion,
        "timeliness": kpi_settings.weight_timeliness,
        "quality": kpi_settings.weight_quality,
        "workload": kpi_settings.weight_workload,
    }
    available = {
        name: weights[name]
        for name in COMPONENTS
        if weights[name] and getattr(result, name) is not None
    }
    if available:
        total = sum(available.values())
        result.base_score = round(
            sum(getattr(result, name) * w for name, w in available.items()) / total, 1
        )

    result.adjustments = [
        {
            "id": adj.pk,
            "points": adj.points,
            "reason": adj.reason,
            "by": adj.created_by.get_full_name() or adj.created_by.username,
            "at": timezone.localtime(adj.created_at).strftime("%d.%m.%Y"),
        }
        for adj in adjustments
    ]
    result.adjustment = sum(adj.points for adj in adjustments)
    if result.base_score is not None:
        result.score = round(max(0.0, min(100.0, result.base_score + result.adjustment)), 1)
    result.grade = grade_for(result.score, kpi_settings)
    return result


def _month_tasks(month):
    return (
        Task.objects.filter(deadline__gte=month, deadline__lte=month_end(month))
        .exclude(status=Task.Status.CANCELLED)
        .order_by("deadline", "id")
    )


def _month_adjustments(month):
    return KPIAdjustment.objects.filter(month=month).select_related("created_by")


def live_results(month, today=None, kpi_settings=None):
    today = today or timezone.localdate()
    kpi_settings = kpi_settings or KPISettings.load()
    tasks_by_user, adjustments_by_user = {}, {}
    for task in _month_tasks(month):
        tasks_by_user.setdefault(task.assignee_id, []).append(task)
    for adj in _month_adjustments(month):
        adjustments_by_user.setdefault(adj.employee_id, []).append(adj)

    people = (
        User.objects.filter(
            Q(is_active=True, profile__role=Profile.Role.EMPLOYEE)
            | Q(pk__in=tasks_by_user.keys())
            | Q(pk__in=adjustments_by_user.keys())
        )
        .select_related("profile", "profile__department")
        .distinct()
    )
    results = [
        calculate(
            person,
            month,
            tasks_by_user.get(person.pk, []),
            adjustments_by_user.get(person.pk, []),
            kpi_settings,
            today,
        )
        for person in people
    ]
    results.sort(key=lambda r: (r.score is None, -(r.score or 0), r.name))
    return [asdict(r) for r in results]


def get_period(month):
    return KPIPeriod.objects.filter(month=month).select_related("finalized_by").first()


def month_results(month, today=None):
    """Rows for the KPI table: frozen if the month is finalised, live otherwise."""
    period = get_period(month)
    if period:
        return period.rows, period
    return live_results(month, today), None


def employee_result(user, month, today=None, period=None):
    period = period if period is not None else get_period(month)
    if period:
        for row in period.rows:
            if row["user_id"] == user.pk:
                return row
    today = today or timezone.localdate()
    tasks = list(_month_tasks(month).filter(assignee=user))
    adjustments = list(_month_adjustments(month).filter(employee=user))
    return asdict(calculate(user, month, tasks, adjustments, KPISettings.load(), today))


def history(user, months=6, today=None):
    today = today or timezone.localdate()
    current = first_of_month(today)
    rows = []
    for offset in range(months - 1, -1, -1):
        month = shift_month(current, -offset)
        row = employee_result(user, month, today)
        rows.append({"month": month, "score": row["score"], "grade": row["grade"]})
    return rows


@transaction.atomic
def finalize(month, user, today=None):
    rows = live_results(month, today)
    return KPIPeriod.objects.create(
        month=month,
        finalized_by=user,
        settings_snapshot=KPISettings.load().as_dict(),
        rows=rows,
    )


def reopen(month):
    KPIPeriod.objects.filter(month=month).delete()
