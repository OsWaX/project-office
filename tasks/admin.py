from django.contrib import admin

from tasks.models import Category, Notification, Task, TaskAttachment, TaskComment, TaskEvent


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_editable = ["is_active"]
    search_fields = ["name"]


class CommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    readonly_fields = ["original_name", "size", "uploaded_by", "created_at"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "assignee", "status", "complexity", "priority", "deadline"]
    list_filter = ["status", "complexity", "priority", "category"]
    search_fields = ["title", "description"]
    date_hierarchy = "deadline"
    raw_id_fields = ["assignee", "created_by"]
    inlines = [CommentInline, AttachmentInline]


@admin.register(TaskEvent)
class TaskEventAdmin(admin.ModelAdmin):
    list_display = ["task", "kind", "actor", "created_at"]
    list_filter = ["kind"]
    raw_id_fields = ["task"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "verb", "task", "is_read", "created_at"]
    list_filter = ["verb", "is_read"]
    raw_id_fields = ["task"]
