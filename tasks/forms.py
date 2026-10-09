import os

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Department
from tasks.models import Category, Task, TaskAttachment, TaskEvent

User = get_user_model()


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [validate_upload(super(MultipleFileField, self).clean(f, initial)) for f in files]


def validate_upload(f):
    ext = os.path.splitext(f.name)[1].lower().lstrip(".")
    if ext not in settings.ATTACHMENT_ALLOWED_EXTENSIONS:
        raise forms.ValidationError(
            _("File type .%(ext)s is not allowed."), params={"ext": ext or "?"}
        )
    if f.size > settings.ATTACHMENT_MAX_SIZE_MB * 1024 * 1024:
        raise forms.ValidationError(
            _("File %(name)s is larger than %(max)s MB."),
            params={"name": f.name, "max": settings.ATTACHMENT_MAX_SIZE_MB},
        )
    return f


def save_attachment(task, user, f):
    name = os.path.basename(f.name)[:255]
    attachment = TaskAttachment(task=task, uploaded_by=user, original_name=name, size=f.size)
    attachment.file.save(name, f, save=False)
    attachment.save()
    TaskEvent.objects.create(
        task=task, actor=user, kind=TaskEvent.Kind.ATTACHMENT, data={"name": name}
    )
    return attachment


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        return person_label(user)


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, user):
        return person_label(user)


def person_label(user):
    name = user.get_full_name() or user.username
    position = getattr(getattr(user, "profile", None), "position", "")
    return f"{name} — {position}" if position else name


def assignable_users():
    return (
        User.objects.filter(is_active=True)
        .select_related("profile")
        .order_by("last_name", "first_name", "username")
    )


COMPLEXITY_HELP = {
    Task.Complexity.SIMPLE: _("Routine work, up to one day: a short letter, a reference, a phone survey."),
    Task.Complexity.MEDIUM: _("A few days of work: a report from available data, preparing a meeting."),
    Task.Complexity.COMPLEX: _("Analysis or coordination with other bodies: a draft regulation, a sector study."),
    Task.Complexity.VERY_COMPLEX: _("Multi-week strategic work: a programme, an investment project, a large inspection."),
}


class TaskBaseForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "category", "complexity", "priority", "deadline"]
        widgets = {
            "deadline": DateInput(),
            "description": forms.Textarea(attrs={"rows": 5}),
            "complexity": forms.RadioSelect,
            "priority": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = Category.objects.filter(is_active=True)
        if self.instance.pk and self.instance.category_id:
            categories = Category.objects.filter(pk=self.instance.category_id) | categories
        self.fields["category"].queryset = categories
        self.fields["complexity"].choices = Task.Complexity.choices
        self.fields["priority"].choices = Task.Priority.choices


class TaskCreateForm(TaskBaseForm):
    assignees = UserMultipleChoiceField(
        label=_("Executors"),
        queryset=User.objects.none(),
        help_text=_("Choose several people to give each of them their own copy of this task."),
        widget=forms.SelectMultiple(attrs={"size": 8}),
    )
    files = MultipleFileField(label=_("Attachments"))

    class Meta(TaskBaseForm.Meta):
        fields = ["title", "description", "category", "assignees", "complexity", "priority", "deadline"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assignees"].queryset = assignable_users()

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline < timezone.localdate():
            raise forms.ValidationError(_("The deadline cannot be in the past."))
        return deadline


class TaskEditForm(TaskBaseForm):
    assignee = UserChoiceField(label=_("Executor"), queryset=User.objects.none())

    class Meta(TaskBaseForm.Meta):
        fields = ["title", "description", "category", "assignee", "complexity", "priority", "deadline"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        users = assignable_users()
        if self.instance.assignee_id:
            users = users | User.objects.filter(pk=self.instance.assignee_id)
        self.fields["assignee"].queryset = users.distinct()


class ApproveForm(forms.Form):
    rating = forms.TypedChoiceField(
        label=_("Quality of the work"),
        coerce=int,
        choices=[
            (5, _("5 — excellent")),
            (4, _("4 — good")),
            (3, _("3 — acceptable")),
            (2, _("2 — weak")),
            (1, _("1 — poor")),
        ],
        widget=forms.RadioSelect,
        initial=5,
    )
    comment = forms.CharField(
        label=_("Comment (optional)"), required=False, widget=forms.Textarea(attrs={"rows": 2})
    )


class ReturnForm(forms.Form):
    comment = forms.CharField(
        label=_("What needs to be corrected"), widget=forms.Textarea(attrs={"rows": 3})
    )


class SimpleActionForm(forms.Form):
    comment = forms.CharField(
        label=_("Comment (optional)"), required=False, widget=forms.Textarea(attrs={"rows": 2})
    )


class ProgressForm(forms.Form):
    progress = forms.IntegerField(
        label=_("Progress, %"),
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"type": "range", "step": 5}),
    )


class CommentForm(forms.Form):
    text = forms.CharField(
        label=_("Comment"),
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": _("Write a comment…")}),
    )


class AttachmentForm(forms.Form):
    files = MultipleFileField(label=_("Files"), required=True)


class TaskFilterForm(forms.Form):
    STATE_CHOICES = [
        ("", _("All")),
        ("active", _("Not finished")),
        ("overdue", _("Overdue")),
    ] + list(Task.Status.choices)

    q = forms.CharField(label=_("Search"), required=False)
    state = forms.ChoiceField(label=_("Status"), choices=STATE_CHOICES, required=False)
    assignee = UserChoiceField(label=_("Executor"), queryset=User.objects.none(), required=False)
    department = forms.ModelChoiceField(
        label=_("Department"), queryset=Department.objects.all(), required=False
    )
    category = forms.ModelChoiceField(
        label=_("Task type"), queryset=Category.objects.all(), required=False
    )
    complexity = forms.TypedChoiceField(
        label=_("Complexity"),
        choices=[("", _("Any"))] + list(Task.Complexity.choices),
        coerce=int,
        required=False,
        empty_value=None,
    )
    priority = forms.TypedChoiceField(
        label=_("Priority"),
        choices=[("", _("Any"))] + list(Task.Priority.choices),
        coerce=int,
        required=False,
        empty_value=None,
    )
    deadline_from = forms.DateField(label=_("Deadline from"), required=False, widget=DateInput())
    deadline_to = forms.DateField(label=_("Deadline to"), required=False, widget=DateInput())

    def __init__(self, *args, manager=False, **kwargs):
        super().__init__(*args, **kwargs)
        if manager:
            self.fields["assignee"].queryset = User.objects.filter(
                assigned_tasks__isnull=False
            ).distinct().order_by("last_name", "first_name")
        else:
            del self.fields["assignee"]
            del self.fields["department"]

    def filter(self, qs):
        if not self.is_valid():
            return qs
        data = self.cleaned_data
        today = timezone.localdate()
        if data.get("q"):
            q = data["q"]
            filters = Q(title__icontains=q) | Q(description__icontains=q)
            if q.lstrip("#").isdigit():
                filters |= Q(pk=int(q.lstrip("#")))
            qs = qs.filter(filters)
        state = data.get("state")
        if state == "active":
            qs = qs.active()
        elif state == "overdue":
            qs = qs.overdue(today)
        elif state:
            qs = qs.filter(status=state)
        if data.get("assignee"):
            qs = qs.filter(assignee=data["assignee"])
        if data.get("department"):
            qs = qs.filter(assignee__profile__department=data["department"])
        if data.get("category"):
            qs = qs.filter(category=data["category"])
        if data.get("complexity"):
            qs = qs.filter(complexity=data["complexity"])
        if data.get("priority"):
            qs = qs.filter(priority=data["priority"])
        if data.get("deadline_from"):
            qs = qs.filter(deadline__gte=data["deadline_from"])
        if data.get("deadline_to"):
            qs = qs.filter(deadline__lte=data["deadline_to"])
        return qs
