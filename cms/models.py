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
