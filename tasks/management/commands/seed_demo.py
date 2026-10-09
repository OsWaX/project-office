"""Fill an empty portal with a realistic demo team and four months of tasks.

    python manage.py seed_demo            # creates users "director" and employees, password demo12345

Only for trying the portal out — do not run it on the production database.
"""

import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Department, Profile
from kpi import services as kpi
from kpi.models import KPIAdjustment
from tasks.models import Category, Notification, Task, TaskComment, TaskEvent

User = get_user_model()
PASSWORD = "demo12345"

DEPARTMENTS = [
    "Textile industry department",
    "Silk and wool department",
    "Leather and footwear department",
    "Investment and export department",
    "Analytics and monitoring department",
]

# username, first, last, position, department index, reliability profile
EMPLOYEES = [
    ("akarimov", "Aziz", "Karimov", "Head of textile department", 0, (0.97, 0.92, 4.6)),
    ("drahimova", "Dilnoza", "Rahimova", "Chief specialist, textile", 0, (0.93, 0.85, 4.3)),
    ("stursunov", "Sardor", "Tursunov", "Leading specialist, silk", 1, (0.85, 0.70, 3.9)),
    ("myusupova", "Malika", "Yusupova", "Chief specialist, leather", 2, (0.95, 0.90, 4.5)),
    ("jabdullaev", "Jasur", "Abdullaev", "Investment projects specialist", 3, (0.78, 0.60, 3.6)),
    ("nismoilova", "Nodira", "Ismoilova", "Export promotion specialist", 3, (0.90, 0.80, 4.1)),
    ("bnazarov", "Bekzod", "Nazarov", "Analyst", 4, (0.70, 0.55, 3.4)),
]

CATEGORIES = [
    "Analytical report",
    "Official letter / response",
    "Draft regulation",
    "Meeting preparation",
    "Field inspection",
    "Investment project",
    "Statistics and monitoring",
]

# title, category index, complexity
TASKS = [
    ("Prepare analytical note on cotton yarn exports for the quarter", 0, 3),
    ("Draft response to the Ministry of Economy letter on textile clusters", 1, 1),
    ("Collect monthly production data from leather enterprises", 6, 2),
    ("Prepare presentation for the meeting with Turkish investors", 3, 2),
    ("Draft resolution on support measures for silk producers", 2, 4),
    ("Inspection visit to the textile cluster in Fergana region", 4, 3),
    ("Update the register of light industry enterprises", 6, 2),
    ("Prepare proposals for the 2027 sector development programme", 2, 4),
    ("Answer a citizen's appeal about employment at a garment factory", 1, 1),
    ("Analyse import duties on synthetic fibres", 0, 3),
    ("Prepare minutes of the working group meeting", 3, 1),
    ("Coordinate participation in the Tashkent international textile fair", 3, 3),
    ("Monitor implementation of the decree on the leather industry", 6, 3),
    ("Prepare a reference on silk cocoon procurement prices", 0, 2),
    ("Review the investment project of a denim factory in Namangan", 5, 3),
    ("Prepare the weekly report on export contracts", 6, 1),
    ("Compile a list of enterprises for certification to EU standards", 0, 2),
    ("Draft the agenda for the board meeting", 3, 1),
    ("Analyse capacity utilisation of knitting factories", 0, 2),
    ("Prepare information on sector results for the Prime Minister's office", 0, 4),
    ("Respond to the regional administration's request on cluster land plots", 1, 1),
    ("Evaluate a footwear plant modernisation project", 5, 3),
]

COMMENTS = [
    "Data from two regions is still missing, I have requested it again.",
    "Please also add a comparison with last year.",
    "Draft attached, waiting for comments from the legal department.",
    "Agreed. Please submit by the deadline.",
    "The figures were checked with the Statistics Agency.",
]


def aware(day, hour=10):
    return timezone.make_aware(datetime.combine(day, time(hour, 0)))


class Command(BaseCommand):
    help = "Create a demo team and four months of sample tasks (for evaluation only)."

    @transaction.atomic
    def handle(self, *args, **options):
        if User.objects.filter(username="director").exists():
            raise CommandError("Demo data already exists (user 'director').")
        rng = random.Random(42)
        today = timezone.localdate()

        departments = [Department.objects.get_or_create(name=name)[0] for name in DEPARTMENTS]
        categories = [Category.objects.get_or_create(name=name)[0] for name in CATEGORIES]

        director = User.objects.create_user(
            "director", password=PASSWORD, first_name="Deputy Director", is_staff=True
        )
        director.profile.role = Profile.Role.MANAGER
        director.profile.position = "Deputy Director"
        director.profile.save()

        people = []
        for username, first, last, position, dept, reliability in EMPLOYEES:
            user = User.objects.create_user(username, password=PASSWORD, first_name=first, last_name=last)
            user.profile.position = position
            user.profile.department = departments[dept]
            user.profile.save()
            people.append((user, reliability))

        current = kpi.first_of_month(today)
        for offset in (3, 2, 1, 0):
            month = kpi.shift_month(current, -offset)
            last_day = kpi.month_end(month)
            for user, reliability in people:
                for _ in range(rng.randint(5, 8)):
                    deadline = month + timedelta(days=rng.randint(2, last_day.day - 1))
                    self._make_task(rng, director, user, reliability, deadline, categories, today)

        # A few unread items for the director to look at.
        for task in Task.objects.filter(status=Task.Status.ON_REVIEW)[:4]:
            Notification.objects.create(
                recipient=director, actor=task.assignee, task=task, verb=Notification.Verb.SUBMITTED
            )

        last_month = kpi.shift_month(current, -1)
        KPIAdjustment.objects.create(
            employee=people[3][0],
            month=last_month,
            points=5,
            reason="Prepared extra materials for the Prime Minister's visit at short notice",
            created_by=director,
        )
        KPIAdjustment.objects.create(
            employee=people[6][0],
            month=last_month,
            points=-3,
            reason="Weekly export report submitted late twice",
            created_by=director,
        )

        for offset in (3, 2):
            kpi.finalize(kpi.shift_month(current, -offset), director, today)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data created: {Task.objects.count()} tasks. "
                f"Log in as 'director' (manager) or e.g. 'akarimov' (employee), password '{PASSWORD}'."
            )
        )

    def _make_task(self, rng, director, user, reliability, deadline, categories, today):
        p_done, p_on_time, quality = reliability
        title, category, complexity = rng.choice(TASKS)
        created = max(deadline - timedelta(days=rng.randint(3, 15)), deadline - timedelta(days=30))
        created = min(created, today)
        task = Task.objects.create(
            title=title,
            description="Please see the attached instructions and coordinate with the relevant departments.",
            category=categories[category],
            assignee=user,
            created_by=director,
            complexity=complexity,
            priority=rng.choices([1, 2, 3, 4], weights=[1, 6, 3, 1])[0],
            deadline=deadline,
        )
        events = [(TaskEvent.Kind.CREATED, {}, aware(created, 9), director)]

        if deadline < today:
            roll = rng.random()
            if roll < 0.03:
                task.status = Task.Status.CANCELLED
            elif roll < p_done or (today - deadline).days > 30 and rng.random() < 0.8:
                # Old unfinished work is usually handed in late eventually.
                on_time = roll < p_done and rng.random() < p_on_time
                late_by = rng.randint(1, 6) if roll < p_done else rng.randint(7, 20)
                submitted = (
                    deadline - timedelta(days=rng.randint(0, 3))
                    if on_time
                    else deadline + timedelta(days=late_by)
                )
                submitted = max(submitted, created)
                if submitted >= today:
                    task.status = Task.Status.ON_REVIEW
                    task.submitted_at = aware(today, 9)
                    task.progress = 100
                    events.append(
                        (TaskEvent.Kind.STATUS, {"old": "in_progress", "new": "on_review"}, task.submitted_at, user)
                    )
                else:
                    accepted = min(submitted + timedelta(days=rng.randint(0, 2)), today)
                    task.status = Task.Status.DONE
                    task.started_at = aware(created, 11)
                    task.submitted_at = aware(submitted, 16)
                    task.completed_at = aware(accepted, 17)
                    task.progress = 100
                    task.quality_rating = max(1, min(5, round(rng.gauss(quality, 0.6))))
                    events.append(
                        (TaskEvent.Kind.STATUS, {"old": "in_progress", "new": "on_review"}, task.submitted_at, user)
                    )
                    events.append(
                        (
                            TaskEvent.Kind.STATUS,
                            {"old": "on_review", "new": "done", "rating": task.quality_rating},
                            task.completed_at,
                            director,
                        )
                    )
            else:
                task.status = rng.choice([Task.Status.IN_PROGRESS, Task.Status.RETURNED])
                task.started_at = aware(created, 11)
                task.progress = rng.choice([30, 50, 70, 80])
                if task.status == Task.Status.RETURNED:
                    task.revision_count = 1
                    task.review_comment = "Figures for the last quarter are missing, please add them."
        else:
            task.status = rng.choices(
                [Task.Status.NEW, Task.Status.IN_PROGRESS, Task.Status.ON_REVIEW], weights=[3, 5, 2]
            )[0]
            if task.status != Task.Status.NEW:
                task.started_at = aware(created, 11)
                task.progress = rng.choice([20, 40, 60, 80])
            if task.status == Task.Status.ON_REVIEW:
                task.submitted_at = aware(min(today, deadline), 9)
                task.progress = 100
                events.append(
                    (TaskEvent.Kind.STATUS, {"old": "in_progress", "new": "on_review"}, task.submitted_at, user)
                )

        task.save()
        Task.objects.filter(pk=task.pk).update(created_at=aware(created, 9))
        for kind, data, when, actor in events:
            event = TaskEvent.objects.create(task=task, actor=actor, kind=kind, data=data)
            TaskEvent.objects.filter(pk=event.pk).update(created_at=when)
        if rng.random() < 0.3:
            comment = TaskComment.objects.create(task=task, author=user, text=rng.choice(COMMENTS))
            when = min(aware(created + timedelta(days=1), 12), timezone.now())
            TaskComment.objects.filter(pk=comment.pk).update(created_at=when)
