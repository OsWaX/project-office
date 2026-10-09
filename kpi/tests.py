from datetime import date, datetime, time

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile
from kpi import services
from kpi.models import KPIAdjustment, KPISettings
from tasks.models import Task

User = get_user_model()

SEPT = date(2026, 9, 1)
AFTER_SEPT = date(2026, 10, 9)  # "today" for a month that is already over


def at(day, hour=12):
    return timezone.make_aware(datetime.combine(day, time(hour)))


class KPIBase(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("boss", password="x", first_name="Boss")
        self.manager.profile.role = Profile.Role.MANAGER
        self.manager.profile.save()
        self.emp = User.objects.create_user("emp", password="x", first_name="Emp", last_name="One")
        self.settings = KPISettings.load()

    def task(self, deadline, complexity=Task.Complexity.MEDIUM, status=Task.Status.NEW, submitted=None, rating=None, assignee=None):
        return Task.objects.create(
            title="t",
            assignee=assignee or self.emp,
            created_by=self.manager,
            complexity=complexity,
            status=status,
            deadline=deadline,
            submitted_at=at(submitted) if submitted else None,
            completed_at=at(submitted) if status == Task.Status.DONE and submitted else None,
            quality_rating=rating,
        )

    def result(self, month=SEPT, today=AFTER_SEPT, user=None):
        return services.employee_result(user or self.emp, month, today)


class CalculationTests(KPIBase):
    def test_methodology_example(self):
        """The worked example on the Methodology page must match the code."""
        self.task(date(2026, 9, 10), Task.Complexity.MEDIUM, Task.Status.DONE, date(2026, 9, 9), 5)
        self.task(date(2026, 9, 15), Task.Complexity.MEDIUM, Task.Status.DONE, date(2026, 9, 15), 4)
        self.task(date(2026, 9, 20), Task.Complexity.COMPLEX, Task.Status.DONE, date(2026, 9, 21), 4)
        self.task(date(2026, 9, 25), Task.Complexity.SIMPLE, Task.Status.IN_PROGRESS)

        r = self.result()
        self.assertEqual((r["assessed"], r["done"], r["on_time"], r["late"], r["failed"]), (4, 3, 2, 1, 1))
        self.assertEqual((r["points_assessed"], r["points_done"], r["points_on_time"]), (8, 7, 4))
        self.assertEqual(r["completion"], 87.5)
        self.assertEqual(r["timeliness"], 50.0)
        self.assertEqual(r["quality"], 85.7)
        self.assertEqual(r["workload"], 35.0)
        self.assertEqual(r["base_score"], 69.8)
        self.assertEqual(r["score"], 69.8)
        self.assertEqual(r["grade"], "satisfactory")

    def test_no_tasks_means_no_score(self):
        r = self.result()
        self.assertIsNone(r["score"])
        self.assertIsNone(r["grade"])

    def test_cancelled_pending_and_upcoming_tasks_are_not_assessed(self):
        today = date(2026, 9, 15)
        self.task(date(2026, 9, 5), status=Task.Status.CANCELLED)
        self.task(date(2026, 9, 6), status=Task.Status.ON_REVIEW, submitted=date(2026, 9, 7))
        self.task(date(2026, 9, 20), status=Task.Status.IN_PROGRESS)  # deadline not reached yet
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)

        r = self.result(today=today)
        self.assertEqual(r["tasks_total"], 3)  # cancelled task is ignored entirely
        self.assertEqual((r["assessed"], r["pending"], r["upcoming"]), (1, 1, 1))
        self.assertEqual(r["completion"], 100.0)
        self.assertEqual(r["timeliness"], 100.0)

    def test_timeliness_uses_submission_not_approval_date(self):
        t = self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)
        Task.objects.filter(pk=t.pk).update(completed_at=at(date(2026, 9, 20)))
        self.assertEqual(self.result()["on_time"], 1)

    def test_complex_tasks_weigh_more(self):
        self.task(date(2026, 9, 10), Task.Complexity.VERY_COMPLEX, Task.Status.DONE, date(2026, 9, 9), 5)
        self.task(date(2026, 9, 11), Task.Complexity.SIMPLE, Task.Status.NEW)
        r = self.result()
        self.assertAlmostEqual(r["completion"], round(100 * 5 / 6, 1))

    def test_missing_component_weight_is_redistributed(self):
        # Nothing completed: quality cannot be measured, the rest are zero.
        self.task(date(2026, 9, 10), status=Task.Status.IN_PROGRESS)
        r = self.result()
        self.assertIsNone(r["quality"])
        self.assertEqual(r["base_score"], 0.0)

        # Workload switched off: score comes from the other three components only.
        self.settings.default_monthly_norm = 0
        self.settings.save()
        Task.objects.all().delete()
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)
        r = self.result()
        self.assertIsNone(r["workload"])
        self.assertEqual(r["score"], 100.0)

    def test_personal_norm_overrides_default(self):
        self.emp.profile.monthly_norm = 4
        self.emp.profile.save()
        self.task(date(2026, 9, 10), Task.Complexity.MEDIUM, Task.Status.DONE, date(2026, 9, 10), 5)
        self.assertEqual(self.result()["workload"], 50.0)

    def test_norm_is_prorated_in_current_month(self):
        today = date(2026, 9, 15)  # half of September
        self.task(date(2026, 9, 10), Task.Complexity.VERY_COMPLEX, Task.Status.DONE, date(2026, 9, 10), 5)
        r = self.result(today=today)
        self.assertEqual(r["norm"], 10.0)
        self.assertEqual(r["workload"], 50.0)

    def test_adjustments_are_added_and_clamped(self):
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)
        KPIAdjustment.objects.create(employee=self.emp, month=SEPT, points=10, reason="r", created_by=self.manager)
        r = self.result()
        self.assertEqual(r["adjustment"], 10)
        self.assertEqual(r["score"], min(100.0, r["base_score"] + 10))
        self.assertLessEqual(r["score"], 100)

    def test_month_results_include_idle_employees_and_rank_by_score(self):
        other = User.objects.create_user("other", password="x")
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 12), rating=3, assignee=other)
        idle = User.objects.create_user("idle", password="x")
        rows, period = services.month_results(SEPT, AFTER_SEPT)
        self.assertIsNone(period)
        ids = [row["user_id"] for row in rows]
        self.assertEqual(ids[:2], [self.emp.pk, other.pk])
        self.assertIn(idle.pk, ids)
        self.assertNotIn(self.manager.pk, ids)

    def test_finalised_month_is_frozen(self):
        t = self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=5)
        services.finalize(SEPT, self.manager, AFTER_SEPT)
        Task.objects.filter(pk=t.pk).update(quality_rating=1)
        self.assertEqual(self.result()["quality"], 100.0)
        services.reopen(SEPT)
        self.assertEqual(self.result()["quality"], 20.0)

    def test_parse_month_never_goes_into_future(self):
        today = date(2026, 10, 9)
        self.assertEqual(services.parse_month("2026-08", today), date(2026, 8, 1))
        self.assertEqual(services.parse_month("2027-01", today), date(2026, 10, 1))
        self.assertEqual(services.parse_month("garbage", today), date(2026, 10, 1))
        self.assertEqual(services.shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))


class SettingsTests(KPIBase):
    def test_weights_must_sum_to_100(self):
        self.settings.weight_quality = 30
        with self.assertRaises(ValidationError):
            self.settings.full_clean()

    def test_grades_must_decrease(self):
        self.settings.grade_good = 95
        with self.assertRaises(ValidationError):
            self.settings.full_clean()


class KPIViewTests(KPIBase):
    def test_manager_pages_and_export(self):
        self.task(date(2026, 9, 10), status=Task.Status.DONE, submitted=date(2026, 9, 10), rating=4)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("kpi:month")).status_code, 200)
        response = self.client.get(reverse("kpi:export") + "?month=2026-09")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))  # xlsx is a zip file
        self.assertEqual(self.client.get(reverse("kpi:print") + "?month=2026-09").status_code, 200)

    def test_employee_sees_only_own_kpi(self):
        other = User.objects.create_user("other", password="x")
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("kpi:employee", args=[self.emp.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("kpi:employee", args=[other.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("kpi:month")).status_code, 403)

    def test_adjustment_limits_and_finalised_months(self):
        self.client.force_login(self.manager)
        url = reverse("kpi:adjust", args=[self.emp.pk])
        self.client.post(url, {"month": "2026-09", "points": 50, "reason": "too much"})
        self.assertFalse(KPIAdjustment.objects.exists())
        self.client.post(url, {"month": "2026-09", "points": 5, "reason": "initiative"})
        self.assertEqual(KPIAdjustment.objects.get().points, 5)

        self.client.post(reverse("kpi:finalize"), {"month": "2026-09"})
        self.client.post(url, {"month": "2026-09", "points": 3, "reason": "late"})
        self.assertEqual(KPIAdjustment.objects.count(), 1)

    def test_current_month_cannot_be_finalised(self):
        self.client.force_login(self.manager)
        self.client.post(reverse("kpi:finalize"), {"month": timezone.localdate().strftime("%Y-%m")})
        self.assertFalse(services.get_period(services.first_of_month(timezone.localdate())))
