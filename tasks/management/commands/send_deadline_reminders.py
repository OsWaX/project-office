"""Create in-portal reminders for tasks due tomorrow and tasks that just became overdue.

Run once a day, e.g. from cron at 08:00:
    0 8 * * *  cd /srv/project-office && .venv/bin/python manage.py send_deadline_reminders
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Notification, Task


class Command(BaseCommand):
    help = "Notify executors about tomorrow's deadlines and newly overdue tasks."

    def handle(self, *args, **options):
        today = timezone.localdate()
        created = 0
        open_tasks = Task.objects.filter(status__in=Task.OPEN_STATUSES).select_related(
            "assignee", "created_by"
        )

        for task in open_tasks.filter(deadline=today + timedelta(days=1)):
            created += self._notify(task.assignee, task, Notification.Verb.DUE_SOON, today)

        for task in open_tasks.filter(deadline=today - timedelta(days=1)):
            created += self._notify(task.assignee, task, Notification.Verb.OVERDUE, today)
            created += self._notify(task.created_by, task, Notification.Verb.OVERDUE, today)

        self.stdout.write(self.style.SUCCESS(f"{created} reminder(s) created."))

    def _notify(self, user, task, verb, today):
        if not user.is_active:
            return 0
        already = Notification.objects.filter(
            recipient=user, task=task, verb=verb, created_at__date=today
        ).exists()
        if already:
            return 0
        Notification.objects.create(recipient=user, task=task, verb=verb)
        return 1
