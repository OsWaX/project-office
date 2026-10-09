from django.conf import settings

from accounts.permissions import is_manager


def portal(request):
    user = request.user
    context = {"ORGANIZATION_NAME": settings.ORGANIZATION_NAME}
    if user.is_authenticated:
        context["is_manager"] = is_manager(user)
        context["unread_notifications"] = user.notifications.filter(is_read=False).count()
    return context
