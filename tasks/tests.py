import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import management
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from tasks import services
from tasks.models import Notification, Task, TaskAttachment, TaskEvent

User = get_user_model()
MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class TaskTestBase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.manager = User.objects.create_user("boss", password="x", first_name="Boss")
        self.manager.profile.role = Profile.Role.MANAGER
        self.manager.profile.save()
        self.emp = User.objects.create_user("emp", password="x", first_name="Emp")
        self.other = User.objects.create_user("other", password="x", first_name="Other")
        self.today = timezone.localdate()

    def make_task(self, **kwargs):
        defaults = dict(
            title="Prepare report",
            assignee=self.emp,
            created_by=self.manager,
            deadline=self.today + timedelta(days=3),
        )
        defaults.update(kwargs)
        return Task.objects.create(**defaults)


class WorkflowTests(TaskTestBase):
    def test_full_cycle_with_return(self):
        task = self.make_task()
        self.assertEqual(services.available_actions(task, self.emp), ["start", "submit"])
        self.assertEqual(services.available_actions(task, self.manager), ["approve", "cancel"])

        services.perform_action(task, self.emp, "start")
        services.perform_action(task, self.emp, "submit", comment="Done, see file")
        self.assertEqual(task.status, Task.Status.ON_REVIEW)
        self.assertIsNotNone(task.submitted_at)
        self.assertTrue(Notification.objects.filter(recipient=self.manager, verb="submitted").exists())

        with self.assertRaises(services.WorkflowError):
            services.perform_action(task, self.manager, "return", comment="  ")
        services.perform_action(task, self.manager, "return", comment="Add Q3 figures")
        self.assertEqual((task.status, task.revision_count), (Task.Status.RETURNED, 1))

        services.perform_action(task, self.emp, "submit")
        with self.assertRaises(services.WorkflowError):
            services.perform_action(task, self.manager, "approve")  # rating required
        services.perform_action(task, self.manager, "approve", rating=4)
        task.refresh_from_db()
        self.assertEqual((task.status, task.quality_rating), (Task.Status.DONE, 4))
        self.assertTrue(task.completed_on_time)
        self.assertEqual(task.comments.count(), 2)
        self.assertEqual(task.events.filter(kind=TaskEvent.Kind.STATUS).count(), 5)

    def test_employee_cannot_approve_and_manager_cannot_submit_for_executor(self):
        task = self.make_task(status=Task.Status.ON_REVIEW)
        with self.assertRaises(services.WorkflowError):
            services.perform_action(task, self.emp, "approve", rating=5)
        task = self.make_task()
        with self.assertRaises(services.WorkflowError):
            services.perform_action(task, self.manager, "submit")

    def test_direct_acceptance_counts_as_handed_in_now(self):
        task = self.make_task(deadline=self.today - timedelta(days=2), status=Task.Status.IN_PROGRESS)
        services.perform_action(task, self.manager, "approve", rating=5)
        self.assertEqual(timezone.localdate(task.submitted_at), self.today)
        self.assertFalse(task.completed_on_time)

    def test_reopen_clears_rating(self):
        task = self.make_task()
        services.perform_action(task, self.manager, "approve", rating=3)
        services.perform_action(task, self.manager, "reopen")
        self.assertIsNone(task.quality_rating)
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)

    def test_overdue_flag(self):
        self.assertTrue(self.make_task(deadline=self.today - timedelta(days=1)).is_overdue)
        self.assertFalse(
            self.make_task(deadline=self.today - timedelta(days=1), status=Task.Status.ON_REVIEW).is_overdue
        )
        self.assertFalse(self.make_task(deadline=self.today).is_overdue)


class ViewTests(TaskTestBase):
    def test_create_task_for_several_executors(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("tasks:create"),
            {
                "title": "Collect production data",
                "description": "Monthly figures",
                "assignees": [self.emp.pk, self.other.pk],
                "complexity": 3,
                "priority": 2,
                "deadline": (self.today + timedelta(days=5)).isoformat(),
                "files": [SimpleUploadedFile("brief.pdf", b"%PDF-1.4 test")],
            },
        )
        self.assertEqual(response.status_code, 302)
        tasks = Task.objects.filter(title="Collect production data")
        self.assertEqual(tasks.count(), 2)
        self.assertEqual(TaskAttachment.objects.count(), 2)
        self.assertEqual(Notification.objects.filter(verb="assigned").count(), 2)

    def test_deadline_in_past_is_rejected(self):
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("tasks:create"),
            {
                "title": "Late",
                "assignees": [self.emp.pk],
                "complexity": 1,
                "priority": 2,
                "deadline": (self.today - timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.exists())

    def test_employee_access_is_limited_to_own_tasks(self):
        mine = self.make_task()
        theirs = self.make_task(assignee=self.other)
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(mine.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(theirs.get_absolute_url()).status_code, 403)
        self.assertEqual(self.client.get(reverse("tasks:create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("tasks:edit", args=[mine.pk])).status_code, 403)
        listing = self.client.get(reverse("tasks:list"))
        self.assertEqual(list(listing.context["page"].object_list), [mine])

    def test_attachment_download_is_protected_and_types_are_checked(self):
        task = self.make_task()
        self.client.force_login(self.emp)
        self.client.post(
            reverse("tasks:attach", args=[task.pk]),
            {"files": [SimpleUploadedFile("virus.exe", b"MZ")]},
        )
        self.assertFalse(TaskAttachment.objects.exists())
        self.client.post(
            reverse("tasks:attach", args=[task.pk]),
            {"files": [SimpleUploadedFile("result.docx", b"data")]},
        )
        attachment = TaskAttachment.objects.get()
        self.assertEqual(self.client.get(reverse("tasks:attachment", args=[attachment.pk])).status_code, 200)

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("tasks:attachment", args=[attachment.pk])).status_code, 403)

        Task.objects.filter(pk=task.pk).update(status=Task.Status.DONE)
        self.client.force_login(self.emp)
        response = self.client.post(
            reverse("tasks:attach", args=[task.pk]), {"files": [SimpleUploadedFile("late.pdf", b"x")]}
        )
        self.assertEqual(response.status_code, 403)

    def test_actions_through_views(self):
        task = self.make_task()
        self.client.force_login(self.emp)
        self.client.post(reverse("tasks:action", args=[task.pk, "submit"]), {"comment": ""})
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ON_REVIEW)

        self.client.force_login(self.manager)
        self.client.post(reverse("tasks:action", args=[task.pk, "approve"]), {"rating": 5})
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

    def test_edit_logs_deadline_change_and_notifies(self):
        task = self.make_task()
        self.client.force_login(self.manager)
        new_deadline = self.today + timedelta(days=10)
        self.client.post(
            reverse("tasks:edit", args=[task.pk]),
            {
                "title": task.title,
                "assignee": self.emp.pk,
                "complexity": task.complexity,
                "priority": task.priority,
                "deadline": new_deadline.isoformat(),
            },
        )
        task.refresh_from_db()
        self.assertEqual(task.deadline, new_deadline)
        self.assertTrue(task.deadline_extended)
        self.assertTrue(task.events.filter(kind=TaskEvent.Kind.DEADLINE).exists())
        self.assertTrue(Notification.objects.filter(verb="deadline_changed", recipient=self.emp).exists())

    def test_pages_render_in_all_languages(self):
        task = self.make_task()
        for lang in ("uz", "ru", "en"):
            self.client.cookies["django_language"] = lang
            self.client.force_login(self.manager)
            for url in ("/", reverse("tasks:list"), task.get_absolute_url(), reverse("accounts:team"), reverse("kpi:methodology")):
                self.assertEqual(self.client.get(url).status_code, 200, (lang, url))
            self.client.force_login(self.emp)
            self.assertEqual(self.client.get("/").status_code, 200)


class CommandTests(TaskTestBase):
    def test_deadline_reminders_are_created_once(self):
        self.make_task(deadline=self.today + timedelta(days=1))
        self.make_task(deadline=self.today - timedelta(days=1))
        management.call_command("send_deadline_reminders", stdout=open("/dev/null", "w"))
        management.call_command("send_deadline_reminders", stdout=open("/dev/null", "w"))
        self.assertEqual(Notification.objects.filter(verb="due_soon").count(), 1)
        self.assertEqual(Notification.objects.filter(verb="overdue").count(), 2)

    def test_seed_demo(self):
        management.call_command("seed_demo", stdout=open("/dev/null", "w"))
        self.assertTrue(Task.objects.count() > 100)
