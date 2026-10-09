from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _

from accounts.models import Department, Profile
from tasks.models import Category

User = get_user_model()


class MemberForm(forms.ModelForm):
    """Create or edit a team member: the login account and the work profile together."""

    role = forms.ChoiceField(label=_("Role"), choices=Profile.Role.choices)
    department = forms.ModelChoiceField(
        label=_("Department"), queryset=Department.objects.all(), required=False
    )
    position = forms.CharField(label=_("Position"), max_length=200, required=False)
    phone = forms.CharField(label=_("Phone"), max_length=50, required=False)
    monthly_norm = forms.IntegerField(
        label=_("Monthly workload norm, points"),
        min_value=0,
        required=False,
        help_text=_("Leave empty to use the default from KPI settings."),
    )
    password = forms.CharField(
        label=_("Password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["last_name", "first_name", "username", "email", "is_active"]
        labels = {"username": _("Login")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        if self.instance.pk:
            profile = self.instance.profile
            self.initial.update(
                role=profile.role,
                department=profile.department_id,
                position=profile.position,
                phone=profile.phone,
                monthly_norm=profile.monthly_norm,
            )
            self.fields["password"].help_text = _("Leave empty to keep the current password.")
        else:
            self.fields["password"].required = True
            del self.fields["is_active"]

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            password_validation.validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        user.save()
        profile, _created = Profile.objects.get_or_create(user=user)
        profile.role = self.cleaned_data["role"]
        profile.department = self.cleaned_data["department"]
        profile.position = self.cleaned_data["position"]
        profile.phone = self.cleaned_data["phone"]
        profile.monthly_norm = self.cleaned_data["monthly_norm"]
        profile.save()
        return user


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
