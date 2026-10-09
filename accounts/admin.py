from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import Department, Profile


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]

    def get_inline_instances(self, request, obj=None):
        # The profile is created by a signal when the user is first saved, so
        # it can only be edited inline on the change page.
        if obj is None:
            return []
        return super().get_inline_instances(request, obj)
    list_display = ["username", "first_name", "last_name", "role", "department", "is_active"]
    list_select_related = ["profile", "profile__department"]

    @admin.display(description="role")
    def role(self, obj):
        return obj.profile.get_role_display()

    @admin.display(description="department")
    def department(self, obj):
        return obj.profile.department


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
