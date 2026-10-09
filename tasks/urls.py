from django.urls import path

from tasks import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("new/", views.task_create, name="create"),
    path("<int:pk>/", views.task_detail, name="detail"),
    path("<int:pk>/edit/", views.task_edit, name="edit"),
    path("<int:pk>/action/<str:action>/", views.task_action, name="action"),
    path("<int:pk>/progress/", views.task_progress, name="progress"),
    path("<int:pk>/comment/", views.task_comment, name="comment"),
    path("<int:pk>/attach/", views.task_attach, name="attach"),
    path("files/<int:pk>/", views.attachment_download, name="attachment"),
    path("files/<int:pk>/delete/", views.attachment_delete, name="attachment_delete"),
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/", views.notification_open, name="notification_open"),
    path("notifications/read-all/", views.notification_read_all, name="notifications_read_all"),
]
