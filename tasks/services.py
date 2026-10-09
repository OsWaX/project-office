"""Task workflow: who may do what, and the side effects of each step.

    NEW ──start──▶ IN_PROGRESS ──submit──▶ ON_REVIEW ──approve──▶ DONE
     │                ▲                      │
     └──submit──┐     └──start── RETURNED ◀──return
                ▼
            ON_REVIEW
    Managers may also cancel any unfinished task, accept work directly
    (e.g. reported on paper) and reopen finished or cancelled tasks.
"""

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.permissions import is_manager
from tasks.models import Notification, Task, TaskEvent

S = Task.Status

ACTION_LABELS = {
    "start": _("Start work"),
    "submit": _("Submit for review"),
    "approve": _("Accept"),
    "return": _("Return for revision"),
    "cancel": _("Cancel task"),
    "reopen": _("Reopen"),
}


class WorkflowError(Exception):
    pass


def display_name(user):
    if user is None:
        return ""
    return user.get_full_name() or user.username


def available_actions(task, user):
    manager = is_manager(user)
    executor = task.assignee_id == user.pk
    actions = []
    if executor and task.status in (S.NEW, S.RETURNED):
        actions.append("start")
    if executor and task.status in Task.OPEN_STATUSES:
        actions.append("submit")
    if manager and task.status in Task.ACTIVE_STATUSES:
        actions.append("approve")
    if manager and task.status == S.ON_REVIEW:
        actions.append("return")
    if manager and task.status in Task.ACTIVE_STATUSES:
        actions.append("cancel")
    if manager and task.status in Task.CLOSED_STATUSES:
        actions.append("reopen")
    return actions


def notify(recipient, actor, task, verb):
    if recipient is None or (actor is not None and recipient.pk == actor.pk):
        return None
    if not recipient.is_active:
        return None
    return Notification.objects.create(recipient=recipient, actor=actor, task=task, verb=verb)


def log(task, actor, kind, **data):
    return TaskEvent.objects.create(task=task, actor=actor, kind=kind, data=data)


@transaction.atomic
def perform_action(task, user, action, rating=None, comment=""):
    if action not in available_actions(task, user):
        raise WorkflowError(_("This action is not available for the task in its current state."))

    old_status = task.status
    now = timezone.now()
    event_data = {}

    if action == "start":
        task.status = S.IN_PROGRESS
        task.started_at = task.started_at or now

    elif action == "submit":
        task.status = S.ON_REVIEW
        task.submitted_at = now
        task.progress = 100
        notify(task.created_by, user, task, Notification.Verb.SUBMITTED)

    elif action == "approve":
        if rating is None or not 1 <= int(rating) <= 5:
            raise WorkflowError(_("Please rate the quality of the work from 1 to 5."))
        task.status = S.DONE
        task.quality_rating = int(rating)
        task.completed_at = now
        # Work accepted without a formal submission counts as handed in now.
        task.submitted_at = task.submitted_at if old_status == S.ON_REVIEW else now
        task.progress = 100
        task.review_comment = comment
        event_data["rating"] = task.quality_rating
        notify(task.assignee, user, task, Notification.Verb.APPROVED)

    elif action == "return":
        if not comment.strip():
            raise WorkflowError(_("Please explain what needs to be corrected."))
        task.status = S.RETURNED
        task.revision_count += 1
        task.review_comment = comment
        notify(task.assignee, user, task, Notification.Verb.RETURNED)

    elif action == "cancel":
        task.status = S.CANCELLED
        notify(task.assignee, user, task, Notification.Verb.CANCELLED)

    elif action == "reopen":
        task.status = S.IN_PROGRESS
        task.completed_at = None
        task.quality_rating = None
        notify(task.assignee, user, task, Notification.Verb.REOPENED)

    task.save()
    log(task, user, TaskEvent.Kind.STATUS, old=old_status, new=task.status, **event_data)
    if comment.strip():
        task.comments.create(author=user, text=comment.strip())
    return task


@transaction.atomic
def add_comment(task, user, text):
    comment = task.comments.create(author=user, text=text)
    if user.pk == task.assignee_id:
        notify(task.created_by, user, task, Notification.Verb.COMMENTED)
    else:
        notify(task.assignee, user, task, Notification.Verb.COMMENTED)
    return comment


@transaction.atomic
def update_progress(task, user, progress):
    if task.assignee_id != user.pk and not is_manager(user):
        raise WorkflowError(_("Only the executor can update progress."))
    if not task.is_open:
        raise WorkflowError(_("Progress can only be updated while the task is in work."))
    old = task.progress
    task.progress = progress
    if task.status == S.NEW and user.pk == task.assignee_id:
        log(task, user, TaskEvent.Kind.STATUS, old=task.status, new=S.IN_PROGRESS)
        task.status = S.IN_PROGRESS
        task.started_at = task.started_at or timezone.now()
    task.save()
    if old != progress:
        log(task, user, TaskEvent.Kind.PROGRESS, old=old, new=progress)
    return task


@transaction.atomic
def create_tasks(data, assignees, created_by, files=()):
    """Create one task per assignee (the same assignment given to several people)."""
    from tasks.forms import save_attachment

    tasks = []
    for assignee in assignees:
        task = Task.objects.create(created_by=created_by, assignee=assignee, **data)
        log(task, created_by, TaskEvent.Kind.CREATED)
        for f in files:
            save_attachment(task, created_by, f)
        notify(assignee, created_by, task, Notification.Verb.ASSIGNED)
        tasks.append(task)
    return tasks


@transaction.atomic
def save_task_edit(form, user):
    """Save the edit form, logging deadline/executor changes and notifying people."""
    task = form.instance
    before = Task.objects.get(pk=task.pk)
    task = form.save()
    if before.deadline != task.deadline:
        log(
            task,
            user,
            TaskEvent.Kind.DEADLINE,
            old=before.deadline.strftime("%d.%m.%Y"),
            new=task.deadline.strftime("%d.%m.%Y"),
        )
        notify(task.assignee, user, task, Notification.Verb.DEADLINE_CHANGED)
    if before.assignee_id != task.assignee_id:
        log(
            task,
            user,
            TaskEvent.Kind.ASSIGNEE,
            old=display_name(before.assignee),
            new=display_name(task.assignee),
        )
        notify(task.assignee, user, task, Notification.Verb.ASSIGNED)
    other_fields = set(form.changed_data) - {"deadline", "assignee"}
    if other_fields:
        log(task, user, TaskEvent.Kind.EDITED, fields=sorted(other_fields))
    return task
