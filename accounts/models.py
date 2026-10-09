from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    name = models.CharField(_("name"), max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("department")
        verbose_name_plural = _("departments")

    def __str__(self):
        return self.name


class Profile(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", _("Manager")
        EMPLOYEE = "employee", _("Employee")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
        help_text=_("Managers assign and review tasks and see everyone's KPI."),
    )
    department = models.ForeignKey(
        Department,
        verbose_name=_("department"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )
    position = models.CharField(_("position"), max_length=200, blank=True)
    phone = models.CharField(_("phone"), max_length=50, blank=True)
    monthly_norm = models.PositiveIntegerField(
        _("monthly workload norm"),
        null=True,
        blank=True,
        help_text=_(
            "Complexity points this person is expected to complete per month. "
            "Leave empty to use the default from KPI settings."
        ),
    )

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    def __str__(self):
        return str(self.user)

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER or self.user.is_superuser


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "role": Profile.Role.MANAGER if instance.is_superuser else Profile.Role.EMPLOYEE
            },
        )
