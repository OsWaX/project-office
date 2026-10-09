from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Department, Profile

User = get_user_model()


class TeamTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user("boss", password="x")
        self.manager.profile.role = Profile.Role.MANAGER
        self.manager.profile.save()
        self.emp = User.objects.create_user("emp", password="x")

    def test_profile_created_automatically(self):
        self.assertEqual(self.emp.profile.role, Profile.Role.EMPLOYEE)
        admin = User.objects.create_superuser("root", password="x")
        self.assertEqual(admin.profile.role, Profile.Role.MANAGER)

    def test_manager_adds_member(self):
        dept = Department.objects.create(name="Textile")
        self.client.force_login(self.manager)
        response = self.client.post(
            reverse("accounts:member_create"),
            {
                "last_name": "Karimov",
                "first_name": "Aziz",
                "username": "akarimov",
                "role": "employee",
                "department": dept.pk,
                "position": "Specialist",
                "monthly_norm": 15,
                "password": "Str0ng-pass-2026",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="akarimov")
        self.assertTrue(user.check_password("Str0ng-pass-2026"))
        self.assertEqual((user.profile.department, user.profile.monthly_norm), (dept, 15))

    def test_employee_cannot_manage_team(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("accounts:team")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:member_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:member", args=[self.manager.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:member", args=[self.emp.pk])).status_code, 200)

    def test_manager_adds_department_and_task_type(self):
        from tasks.models import Category

        self.client.force_login(self.manager)
        self.client.post(reverse("accounts:department_create"), {"name": "Silk"})
        self.client.post(reverse("accounts:category_create"), {"name": "Field inspection"})
        self.assertTrue(Department.objects.filter(name="Silk").exists())
        self.assertTrue(Category.objects.filter(name="Field inspection").exists())

        self.client.force_login(self.emp)
        response = self.client.post(reverse("accounts:category_create"), {"name": "Other"})
        self.assertEqual(response.status_code, 403)
