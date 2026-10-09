from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from tasks.views import dashboard

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password/",
        auth_views.PasswordChangeView.as_view(success_url="/password/done/"),
        name="password_change",
    ),
    path("password/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("tasks/", include("tasks.urls")),
    path("team/", include("accounts.urls")),
    path("kpi/", include("kpi.urls")),
    path("admin/", admin.site.urls),
]
