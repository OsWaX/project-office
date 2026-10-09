import os
import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from accounts.permissions import is_manager


class Category(models.Model):
    """A type of work, e.g. "Analytical report", "Letter response", "Field visit"."""

    name = models.CharField(_("name"), max_length=200, unique=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("task type")
        verbose_name_plural = _("task types")

    def __str__(self):
        return self.name


class TaskQuerySet(models.QuerySet):
    def visible_to(self, user):
        if is_manager(user):
            return self
        return self.filter(assignee=user)

    def active(self):
        return self.filter(status__in=Task.ACTIVE_STATUSES)

    def overdue(self, today=None):
        today = today or timezone.localdate()
        return self.filter(status__in=Task.OPEN_STATUSES, deadline__lt=today)


class Task(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        IN_PROGRESS = "in_progress", _("In progress")
        ON_REVIEW = "on_review", _("On review")
        RETURNED = "returned", _("Returned for revision")
        DONE = "done", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    class Complexity(models.IntegerChoices):
        SIMPLE = 1, _("Simple")
        MEDIUM = 2, _("Medium")
        COMPLEX = 3, _("Complex")
        VERY_COMPLEX = 4, _("Very complex")

    class Priority(models.IntegerChoices):
        LOW = 1, _("Low")
        NORMAL = 2, _("Normal")
        HIGH = 3, _("High")
        URGENT = 4, _("Urgent")

    # Work is with the executor.
    OPEN_STATUSES = (Status.NEW, Status.IN_PROGRESS, Status.RETURNED)
    # Not finished yet (includes waiting for the manager's review).
    ACTIVE_STATUSES = OPEN_STATUSES + (Status.ON_REVIEW,)
    CLOSED_STATUSES = (Status.DONE, Status.CANCELLED)

    title = models.CharField(_("title"), max_length=300)
    description = models.TextField(_("description"), blank=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_("task type"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("executor"),
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("assigned by"),
        on_delete=models.PROTECT,
        related_name="created_tasks",
    )
    complexity = models.PositiveSmallIntegerField(
        _("complexity"), choices=Complexity.choices, default=Complexity.MEDIUM
    )
    priority = models.PositiveSmallIntegerField(
        _("priority"), choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        _("status"), max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    deadline = models.DateField(_("deadline"), db_index=True)
    original_deadline = models.DateField(_("original deadline"), editable=False)
    progress = models.PositiveSmallIntegerField(
        _("progress, %"), default=0, validators=[MaxValueValidator(100)]
    )
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    submitted_at = models.DateTimeField(
        _("submitted at"),
        null=True,
        blank=True,
        help_text=_("When the executor last handed the work in. Used to judge timeliness."),
    )
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    quality_rating = models.PositiveSmallIntegerField(
        _("quality rating"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    review_comment = models.TextField(_("review comment"), blank=True)
    revision_count = models.PositiveSmallIntegerField(_("times returned"), default=0)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["deadline", "-priority", "id"]
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        indexes = [models.Index(fields=["assignee", "deadline"])]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def save(self, *args, **kwargs):
        if not self.original_deadline:
            self.original_deadline = self.deadline
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("tasks:detail", args=[self.pk])

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def is_closed(self):
        return self.status in self.CLOSED_STATUSES

    @property
    def is_overdue(self):
        return self.is_open and self.deadline < timezone.localdate()

    @property
    def days_left(self):
        return (self.deadline - timezone.localdate()).days

    @property
    def submitted_on_time(self):
        if not self.submitted_at:
            return None
        return timezone.localdate(self.submitted_at) <= self.deadline

    @property
    def completed_on_time(self):
        return self.status == self.Status.DONE and bool(self.submitted_on_time)

    @property
    def deadline_extended(self):
        return self.deadline != self.original_deadline

    def can_view(self, user):
        return is_manager(user) or self.assignee_id == user.pk


def attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"attachments/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    file = models.FileField(_("file"), upload_to=attachment_upload_to)
    original_name = models.CharField(_("file name"), max_length=255)
    size = models.PositiveBigIntegerField(_("size"), default=0)
    created_at = models.DateTimeField(_("uploaded at"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __str__(self):
        return self.original_name


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    text = models.TextField(_("comment"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self):
        return self.text[:50]


class TaskEvent(models.Model):
    """Audit trail of everything that happened to a task."""

    class Kind(models.TextChoices):
        CREATED = "created", _("Created")
        STATUS = "status", _("Status changed")
        DEADLINE = "deadline", _("Deadline changed")
        ASSIGNEE = "assignee", _("Executor changed")
        PROGRESS = "progress", _("Progress updated")
        EDITED = "edited", _("Edited")
        ATTACHMENT = "attachment", _("File attached")

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def describe(self):
        """Human-readable, translated description (rendered in the reader's language)."""
        d = self.data
        if self.kind == self.Kind.CREATED:
            return gettext("Task created")
        if self.kind == self.Kind.STATUS:
            text = gettext("Status: %(old)s → %(new)s") % {
                "old": Task.Status(d["old"]).label,
                "new": Task.Status(d["new"]).label,
            }
            if d.get("rating"):
                text += " · " + gettext("quality %(rating)s/5") % {"rating": d["rating"]}
            return text
        if self.kind == self.Kind.DEADLINE:
            return gettext("Deadline: %(old)s → %(new)s") % d
        if self.kind == self.Kind.ASSIGNEE:
            return gettext("Executor: %(old)s → %(new)s") % d
        if self.kind == self.Kind.PROGRESS:
            return gettext("Progress: %(old)s%% → %(new)s%%") % d
        if self.kind == self.Kind.ATTACHMENT:
            return gettext("File attached: %(name)s") % d
        if self.kind == self.Kind.EDITED:
            return gettext("Task details edited")
        return self.get_kind_display()


class Notification(models.Model):
    class Verb(models.TextChoices):
        ASSIGNED = "assigned", _("assigned")
        SUBMITTED = "submitted", _("submitted")
        APPROVED = "approved", _("approved")
        RETURNED = "returned", _("returned")
        CANCELLED = "cancelled", _("cancelled")
        REOPENED = "reopened", _("reopened")
        COMMENTED = "commented", _("commented")
        DEADLINE_CHANGED = "deadline_changed", _("deadline changed")
        DUE_SOON = "due_soon", _("due soon")
        OVERDUE = "overdue", _("overdue")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="notifications")
    verb = models.CharField(max_length=30, choices=Verb.choices)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def message(self):
        actor = (self.actor.get_full_name() or self.actor.username) if self.actor else ""
        texts = {
            self.Verb.ASSIGNED: gettext("%(actor)s assigned you a new task"),
            self.Verb.SUBMITTED: gettext("%(actor)s submitted a task for review"),
            self.Verb.APPROVED: gettext("%(actor)s accepted your task"),
            self.Verb.RETURNED: gettext("%(actor)s returned your task for revision"),
            self.Verb.CANCELLED: gettext("%(actor)s cancelled a task"),
            self.Verb.REOPENED: gettext("%(actor)s reopened a task"),
            self.Verb.COMMENTED: gettext("%(actor)s commented on a task"),
            self.Verb.DEADLINE_CHANGED: gettext("%(actor)s changed the deadline of a task"),
            self.Verb.DUE_SOON: gettext("Task deadline is tomorrow"),
            self.Verb.OVERDUE: gettext("Task is overdue"),
        }
        return texts[self.verb] % {"actor": actor}
