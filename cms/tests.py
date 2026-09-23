from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import Profile


class MemberListTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staffer", password="staff-pass", is_staff=True)
        Profile.objects.filter(user=self.staff).update(name="관리자", phone="01000000000", role=Profile.ROLE_ADMIN)
        self.active = self._member("alive", "정상회원", Profile.STATUS_ACTIVE)
        self.suspended = self._member("paused", "정지회원", Profile.STATUS_SUSPENDED)
        self.withdrawn = self._member("gone", "탈퇴회원", Profile.STATUS_WITHDRAWN)
        self.client.force_login(self.staff)

    def _member(self, username, name, status):
        user = User.objects.create_user(username, password="member-pass")
        Profile.objects.filter(user=user).update(name=name, phone="01011112222", status=status)
        return user

    def test_default_hides_withdrawn(self):
        response = self.client.get("/staff/members/")
        self.assertContains(response, "정상회원")
        self.assertContains(response, "정지회원")
        self.assertNotContains(response, "탈퇴회원")

    def test_checkbox_shows_withdrawn(self):
        response = self.client.get("/staff/members/", {"withdrawn": "1"})
        self.assertContains(response, "탈퇴회원")

    def test_status_tabs_filter_without_a_status_sort(self):
        active = self.client.get("/staff/members/", {"status": "active"})
        withdrawn = self.client.get("/staff/members/", {"status": "withdrawn"})
        self.assertContains(active, "정상회원")
        self.assertNotContains(active, "탈퇴회원")
        self.assertContains(withdrawn, "탈퇴회원")
        self.assertNotContains(withdrawn, "상태순")
        self.assertContains(active, "이름순")

    def test_name_sort_is_alphabetical(self):
        response = self.client.get("/staff/members/", {"sort": "name", "withdrawn": "1"})
        body = response.content.decode()
        self.assertLess(body.index("정상회원"), body.index("정지회원"))
        self.assertLess(body.index("정지회원"), body.index("탈퇴회원"))
