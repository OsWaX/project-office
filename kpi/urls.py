from django.urls import path

from kpi import views

app_name = "kpi"

urlpatterns = [
    path("", views.kpi_month, name="month"),
    path("employee/<int:user_id>/", views.kpi_employee, name="employee"),
    path("employee/<int:user_id>/adjust/", views.kpi_adjust, name="adjust"),
    path("adjustments/<int:pk>/delete/", views.kpi_adjust_delete, name="adjust_delete"),
    path("finalize/", views.kpi_finalize, name="finalize"),
    path("reopen/", views.kpi_reopen, name="reopen"),
    path("export/", views.kpi_export, name="export"),
    path("print/", views.kpi_print, name="print"),
    path("settings/", views.kpi_settings, name="settings"),
    path("methodology/", views.methodology, name="methodology"),
]
