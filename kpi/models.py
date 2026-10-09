from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class KPISettings(models.Model):
    """Single row holding the KPI formula parameters (editable by managers)."""

    weight_completion = models.PositiveSmallIntegerField(
        _("weight: execution"), default=35, validators=[MaxValueValidator(100)]
    )
    weight_timeliness = models.PositiveSmallIntegerField(
        _("weight: timeliness"), default=25, validators=[MaxValueValidator(100)]
    )
    weight_quality = models.PositiveSmallIntegerField(
        _("weight: quality"), default=25, validators=[MaxValueValidator(100)]
    )
    weight_workload = models.PositiveSmallIntegerField(
        _("weight: workload"), default=15, validators=[MaxValueValidator(100)]
    )

    points_simple = models.PositiveSmallIntegerField(
        _("points: simple task"), default=1, validators=[MinValueValidator(1)]
    )
    points_medium = models.PositiveSmallIntegerField(
        _("points: medium task"), default=2, validators=[MinValueValidator(1)]
    )
    points_complex = models.PositiveSmallIntegerField(
        _("points: complex task"), default=3, validators=[MinValueValidator(1)]
    )
    points_very_complex = models.PositiveSmallIntegerField(
        _("points: very complex task"), default=5, validators=[MinValueValidator(1)]
    )

    default_monthly_norm = models.PositiveSmallIntegerField(
        _("default monthly workload norm, points"),
        default=20,
        help_text=_("Used for people without their own norm. 0 switches the workload component off."),
    )

    grade_excellent = models.PositiveSmallIntegerField(
        _("“Excellent” from"), default=90, validators=[MaxValueValidator(100)]
    )
    grade_good = models.PositiveSmallIntegerField(
        _("“Good” from"), default=75, validators=[MaxValueValidator(100)]
    )
    grade_satisfactory = models.PositiveSmallIntegerField(
        _("“Satisfactory” from"), default=60, validators=[MaxValueValidator(100)]
    )

    max_adjustment = models.PositiveSmallIntegerField(
        _("maximum manual adjustment, ± points"), default=10, validators=[MaxValueValidator(50)]
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("KPI settings")
        verbose_name_plural = _("KPI settings")

    def __str__(self):
        return str(_("KPI settings"))

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def clean(self):
        total = (
            self.weight_completion + self.weight_timeliness + self.weight_quality + self.weight_workload
        )
        if total != 100:
            raise ValidationError(
                _("Component weights must add up to 100 (now %(total)s)."), params={"total": total}
            )
        if not self.grade_excellent > self.grade_good > self.grade_satisfactory:
            raise ValidationError(_("Grade thresholds must decrease: Excellent > Good > Satisfactory."))

    def complexity_points(self):
        return {
            1: self.points_simple,
            2: self.points_medium,
            3: self.points_complex,
            4: self.points_very_complex,
        }

    def as_dict(self):
        return {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name not in ("id", "updated_at")
        }


class KPIAdjustment(models.Model):
    """A manager's bonus or penalty for things the task list does not capture."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kpi_adjustments"
    )
    month = models.DateField(_("month"), help_text=_("First day of the month."))
    points = models.SmallIntegerField(_("points"))
    reason = models.CharField(_("reason"), max_length=500)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("KPI adjustment")
        verbose_name_plural = _("KPI adjustments")

    def __str__(self):
        return f"{self.employee} {self.month:%Y-%m} {self.points:+d}"


class KPIPeriod(models.Model):
    """A finalised month: results are frozen so later edits do not change history."""

    month = models.DateField(_("month"), unique=True)
    finalized_at = models.DateTimeField(auto_now_add=True)
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    settings_snapshot = models.JSONField(default=dict)
    rows = models.JSONField(default=list)

    class Meta:
        ordering = ["-month"]
        verbose_name = _("finalised KPI month")
        verbose_name_plural = _("finalised KPI months")

    def __str__(self):
        return f"{self.month:%Y-%m}"
