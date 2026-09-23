from django.conf import settings
from django.db import models


class Profile(models.Model):
    ROLE_MEMBER = "member"
    ROLE_GUARDIAN = "guardian"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_MEMBER, "일반 회원"),
        (ROLE_GUARDIAN, "보호자"),
        (ROLE_ADMIN, "관리자"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "정상"),
        (STATUS_SUSPENDED, "정지"),
        (STATUS_WITHDRAWN, "탈퇴"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    name = models.CharField("이름", max_length=50)
    phone = models.CharField("연락처", max_length=20)
    role = models.CharField("권한", max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        verbose_name = "회원 프로필"
        verbose_name_plural = "회원 프로필"

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.user.is_staff


class SharedUser(models.Model):
    """현대 의료기 Postgres users 테이블. managed=False — DROP/변경 금지."""

    id = models.CharField(primary_key=True, max_length=80)
    name = models.TextField()
    phone = models.TextField(unique=True)
    username = models.TextField(null=True, blank=True)
    password_hash = models.TextField()
    role = models.TextField(default="user")
    herium_linked = models.IntegerField(default=0)
    herium_relation = models.TextField(null=True, blank=True)
    herium_note = models.TextField(null=True, blank=True)
    created_at = models.TextField()

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "공유 회원"
        verbose_name_plural = "공유 회원"

    def __str__(self):
        return f"{self.name} ({self.phone})"

