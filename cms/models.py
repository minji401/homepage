from django.conf import settings
from django.db import models


class Board(models.Model):
    slug = models.SlugField("코드", unique=True, allow_unicode=True)
    name = models.CharField("게시판명", max_length=80)
    description = models.CharField("설명", max_length=200, blank=True)
    is_active = models.BooleanField("사용", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Post(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField("제목", max_length=200)
    body = models.TextField("내용")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    author_name = models.CharField("작성자", max_length=50, blank=True)
    image = models.CharField("이미지", max_length=300, blank=True)
    category = models.CharField("분류", max_length=30, blank=True)
    is_pinned = models.BooleanField("상단 고정", default=False)
    is_hidden = models.BooleanField("숨김", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField("작성자", max_length=50)
    body = models.TextField("내용")
    is_hidden = models.BooleanField("숨김", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Application(models.Model):
    KIND_CONSULT = "consult"
    KIND_TOUR = "tour"
    KIND_VOLUNTEER = "volunteer"
    KIND_DONATE = "donate"
    KIND_CHOICES = [
        (KIND_CONSULT, "입소 상담"),
        (KIND_TOUR, "견학 신청"),
        (KIND_VOLUNTEER, "자원봉사"),
        (KIND_DONATE, "후원"),
    ]
    STATUS_WAITING = "waiting"
    STATUS_DONE = "done"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_WAITING, "대기"),
        (STATUS_DONE, "상담 완료"),
        (STATUS_APPROVED, "승인"),
        (STATUS_REJECTED, "반려"),
    ]

    kind = models.CharField("구분", max_length=20, choices=KIND_CHOICES)
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING)
    name = models.CharField("이름", max_length=80)
    phone = models.CharField("연락처", max_length=30)
    title = models.CharField("제목", max_length=200, blank=True)
    body = models.TextField("내용", blank=True)
    extra = models.JSONField("부가정보", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SiteContent(models.Model):
    key = models.CharField("키", max_length=50, unique=True)
    label = models.CharField("항목명", max_length=80)
    body = models.TextField("내용", blank=True)

    def __str__(self):
        return self.label


class UsageStat(models.Model):
    slug = models.SlugField("코드", unique=True)
    name = models.CharField("구분명", max_length=80)
    capacity = models.PositiveIntegerField("정원", default=0)
    current = models.PositiveIntegerField("현원", default=0)
    waiting = models.PositiveIntegerField("대기 인원", default=0)
    general_capacity = models.PositiveIntegerField("일반실 정원", default=0)
    dementia_capacity = models.PositiveIntegerField("치매전담실 정원", default=0)
    sort_order = models.PositiveIntegerField("순서", default=1)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "이용 현황"
        verbose_name_plural = "이용 현황"

    def __str__(self):
        return self.name

    @property
    def available(self):
        return max(0, self.capacity - self.current)


class WaitlistEntry(models.Model):
    name = models.CharField("성명", max_length=40)
    service_type = models.CharField("구분", max_length=40)
    queue_no = models.PositiveIntegerField("대기 순번")

    class Meta:
        ordering = ["service_type", "queue_no", "id"]
        verbose_name = "대기자"
        verbose_name_plural = "대기자 명단"

    def __str__(self):
        return f"{self.name} ({self.service_type} {self.queue_no})"


USAGE_AS_OF_KEY = "usage_as_of"
USAGE_DEFAULTS = [
    {
        "slug": "nursing",
        "name": "입소시설",
        "capacity": 100,
        "current": 100,
        "waiting": 12,
        "general_capacity": 80,
        "dementia_capacity": 20,
        "sort_order": 1,
    },
    {
        "slug": "day_general",
        "name": "주·야간 일반",
        "capacity": 25,
        "current": 25,
        "waiting": 5,
        "general_capacity": 25,
        "dementia_capacity": 0,
        "sort_order": 2,
    },
    {
        "slug": "day_dementia",
        "name": "주·야간 치매전담",
        "capacity": 15,
        "current": 15,
        "waiting": 5,
        "general_capacity": 0,
        "dementia_capacity": 15,
        "sort_order": 3,
    },
]
WAITLIST_TYPES = ["입소시설", "주·야간보호 일반", "주·야간 치매전담"]
WAITLIST_DEFAULTS = [
    ("김순자", "입소시설", 3),
    ("박영수", "주·야간보호 일반", 1),
    ("이정숙", "입소시설", 7),
    ("최만호", "주·야간 치매전담", 2),
]


def ensure_usage_stats():
    for row in USAGE_DEFAULTS:
        UsageStat.objects.get_or_create(slug=row["slug"], defaults=row)
    SiteContent.objects.get_or_create(
        key=USAGE_AS_OF_KEY,
        defaults={"label": "이용 현황 기준일", "body": "2026년 9월 15일"},
    )
    if not WaitlistEntry.objects.exists():
        WaitlistEntry.objects.bulk_create(
            [WaitlistEntry(name=name, service_type=kind, queue_no=no) for name, kind, no in WAITLIST_DEFAULTS]
        )
    return {item.slug: item for item in UsageStat.objects.all()}


class Popup(models.Model):
    title = models.CharField("제목", max_length=120, blank=True)
    body = models.TextField("내용", blank=True)
    image = models.CharField("이미지", max_length=300, blank=True)
    is_active = models.BooleanField("표시", default=False)
    updated_at = models.DateTimeField(auto_now=True)


class Banner(models.Model):
    title = models.CharField("제목", max_length=80)
    image = models.CharField("이미지 경로", max_length=200)
    is_active = models.BooleanField("사용", default=True)
    sort_order = models.PositiveIntegerField("순서", default=1)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        if self.image and not self.image.startswith(("http://", "https://", "/")):
            self.image = "/" + self.image
        super().save(*args, **kwargs)


class SearchTerm(models.Model):
    keyword = models.CharField("검색어", max_length=80, unique=True)
    search_count = models.PositiveIntegerField("검색 횟수", default=0)
    is_recommended = models.BooleanField("추천검색어", default=False)
    recommend_order = models.PositiveIntegerField("추천 순서", default=0)

    class Meta:
        ordering = ["-search_count", "keyword"]


class VisitLog(models.Model):
    visited_at = models.DateTimeField(auto_now_add=True)
    path = models.CharField("경로", max_length=300)
    referer = models.CharField("유입 경로", max_length=400, blank=True)
    session_key = models.CharField("세션", max_length=40, blank=True)

    class Meta:
        ordering = ["-visited_at"]
