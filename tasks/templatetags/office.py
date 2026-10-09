from datetime import date

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from kpi.services import GRADE_LABELS, OUTCOME_LABELS
from tasks.models import Task

register = template.Library()

ICONS = {
    "dashboard": '<path d="M3 13h8V3H3zm0 8h8v-6H3zm10 0h8V11h-8zm0-18v6h8V3z"/>',
    "tasks": '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "team": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "kpi": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5V21h16"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
    "arrow-up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "clip": '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    "print": '<path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v8H6z"/>',
    "edit": '<path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
}


@register.simple_tag
def icon(name, css="icon"):
    return format_html(
        '<svg class="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>',
        css,
        mark_safe(ICONS.get(name, "")),  # constant markup defined above
    )


@register.filter
def person(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


@register.filter
def initials(user):
    name = person(user)
    parts = [p for p in name.split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.filter
def pct(value):
    if value is None or value == "":
        return "—"
    return f"{float(value):.1f}".rstrip("0").rstrip(".")


@register.filter
def iso_date(value):
    """Turn an ISO date string (as stored in KPI snapshots) back into a date."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@register.filter
def signed(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return value
    return f"+{value}" if value > 0 else str(value)


@register.filter
def grade_label(grade):
    return GRADE_LABELS.get(grade, "—") if grade else _("No data")


@register.filter
def outcome_label(outcome):
    return OUTCOME_LABELS.get(outcome, outcome)


@register.filter
def meter_level(score, kpi_settings=None):
    """Severity of a KPI meter: accent above "Good", warning down to "Satisfactory", then critical."""
    if not isinstance(score, (int, float)):
        return ""
    if kpi_settings is not None and not isinstance(kpi_settings, dict):
        kpi_settings = kpi_settings.as_dict()
    kpi_settings = kpi_settings or {}
    good = kpi_settings.get("grade_good", 75)
    satisfactory = kpi_settings.get("grade_satisfactory", 60)
    if score >= good:
        return "lvl-good"
    if score >= satisfactory:
        return "lvl-warning"
    return "lvl-critical"


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    return mapping.get(key)


@register.filter
def status_label(status):
    try:
        return Task.Status(status).label
    except ValueError:
        return status


@register.filter
def complexity_label(value):
    try:
        return Task.Complexity(int(value)).label
    except (TypeError, ValueError):
        return value


@register.inclusion_tag("includes/status_badge.html")
def status_badge(status):
    return {"status": status, "label": status_label(status)}


@register.inclusion_tag("includes/complexity.html")
def complexity(value):
    value = int(value)
    return {"value": value, "label": complexity_label(value), "range": range(1, 5)}


@register.inclusion_tag("includes/priority.html")
def priority_flag(value):
    return {"value": int(value), "label": Task.Priority(int(value)).label}


@register.simple_tag(takes_context=True)
def nav_active(context, *prefixes):
    path = context["request"].path
    for prefix in prefixes:
        if prefix == "/" and path == "/":
            return "active"
        if prefix != "/" and path.startswith(prefix):
            return "active"
    return ""


@register.filter
def deadline_hint(task):
    """Short relative description of a task deadline."""
    if not task.is_active:
        return ""
    days = task.days_left
    if task.status == Task.Status.ON_REVIEW:
        return ""
    if days < 0:
        return _("%(n)s d overdue") % {"n": -days}
    if days == 0:
        return _("today")
    if days == 1:
        return _("tomorrow")
    return _("in %(n)s d") % {"n": days}
