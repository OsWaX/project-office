from django.contrib import admin

from kpi.models import KPIAdjustment, KPIPeriod, KPISettings


@admin.register(KPISettings)
class KPISettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not KPISettings.objects.exists()


@admin.register(KPIAdjustment)
class KPIAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["employee", "month", "points", "reason", "created_by"]
    list_filter = ["month"]


@admin.register(KPIPeriod)
class KPIPeriodAdmin(admin.ModelAdmin):
    list_display = ["month", "finalized_by", "finalized_at"]
    readonly_fields = ["month", "finalized_by", "finalized_at", "settings_snapshot", "rows"]
