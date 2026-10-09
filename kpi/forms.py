from django import forms
from django.utils.translation import gettext_lazy as _

from kpi.models import KPISettings


class KPISettingsForm(forms.ModelForm):
    class Meta:
        model = KPISettings
        exclude = ["updated_at"]


class AdjustmentForm(forms.Form):
    points = forms.IntegerField(label=_("Points (+ bonus / − penalty)"))
    reason = forms.CharField(label=_("Reason"), max_length=500)

    def __init__(self, *args, max_points=10, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_points = max_points
        self.fields["points"].min_value = -max_points
        self.fields["points"].max_value = max_points
        self.fields["points"].widget.attrs.update(min=-max_points, max=max_points)

    def clean_points(self):
        points = self.cleaned_data["points"]
        if points == 0:
            raise forms.ValidationError(_("Enter a non-zero number of points."))
        if abs(points) > self.max_points:
            raise forms.ValidationError(
                _("Adjustment must be between −%(max)s and +%(max)s."), params={"max": self.max_points}
            )
        return points
