from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("", views.team_list, name="team"),
    path("new/", views.member_create, name="member_create"),
    path("departments/new/", views.department_create, name="department_create"),
    path("task-types/new/", views.category_create, name="category_create"),
    path("<int:pk>/", views.member_detail, name="member"),
    path("<int:pk>/edit/", views.member_edit, name="member_edit"),
]
