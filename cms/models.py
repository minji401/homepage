from django.conf import settings
from django.db import models
import re


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
    extra_images = models.JSONField("추가 사진", default=list, blank=True)
    attachment = models.CharField("첨부파일", max_length=400, blank=True)
    attachment_name = models.CharField("첨부파일명", max_length=200, blank=True)
    category = models.CharField("분류", max_length=30, blank=True)
    is_pinned = models.BooleanField("상단 고정", default=False)
    is_hidden = models.BooleanField("숨김", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title

    def image_list(self):
        urls = []
        if self.image:
            urls.append(self.image)
        extra = self.extra_images or []
        if isinstance(extra, str):
            extra = [part.strip() for part in extra.split(",") if part.strip()]
        for url in extra:
            if url and url not in urls:
                urls.append(url)
        return urls

    def list_url(self):
        slug = self.board.slug if self.board_id else "notice"
        mapping = {
            "notice": "/community/notice.html",
            "gallery": "/community/gallery.html",
            "menu": "/community/menu.html",
            "faq": "/community/faq.html",
        }
        return mapping.get(slug, "/community/notice.html")


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
    STATUS_RECEIVED = "received"
    STATUS_WAITING = "waiting"
    STATUS_DONE = "done"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_RECEIVED, "접수완료"),
        (STATUS_WAITING, "상담대기"),
        (STATUS_DONE, "상담완료"),
        (STATUS_APPROVED, "승인"),
        (STATUS_REJECTED, "반려"),
        (STATUS_CANCELLED, "취소됨"),
    ]
    STATUS_NORMALIZE = {
        "received": "received",
        "RECEIVED": "received",
        "접수완료": "received",
        "waiting": "waiting",
        "PENDING": "waiting",
        "pending": "waiting",
        "상담대기": "waiting",
        "대기중": "waiting",
        "대기": "waiting",
        "done": "done",
        "상담완료": "done",
        "상담 완료": "done",
        "확정": "done",
        "CONFIRMED": "done",
        "confirmed": "done",
        "COMPLETED": "done",
        "completed": "done",
        "approved": "approved",
        "승인": "approved",
        "rejected": "rejected",
        "반려": "rejected",
        "CANCELLED": "cancelled",
        "cancelled": "cancelled",
        "취소됨": "cancelled",
        "취소": "cancelled",
        "회원 취소": "cancelled",
    }
    CANCELLABLE_STATUSES = {"received", "waiting", "pending"}
    LOCKED_STATUSES = {"done", "approved", "rejected", "cancelled"}

    kind = models.CharField("구분", max_length=20, choices=KIND_CHOICES)
    status = models.CharField("상태", max_length=20, choices=STATUS_CHOICES, default=STATUS_RECEIVED)
    user = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="care_applications",
        verbose_name="신청 회원",
    )
    patient_id = models.CharField("어르신 프로필 ID", max_length=80, blank=True)
    senior_name = models.CharField("대상 어르신", max_length=50, blank=True)
    name = models.TextField("이름")
    phone = models.TextField("연락처")
    title = models.CharField("제목", max_length=200, blank=True)
    body = models.TextField("내용", blank=True)
    extra = models.JSONField("부가정보", default=dict, blank=True)
    cancel_reason = models.TextField("취소 사유", blank=True, null=True)
    cancelled_at = models.DateTimeField("취소 일시", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def name_plain(self):
        from .pii import decrypt_text
        return decrypt_text(self.name)

    @property
    def phone_plain(self):
        from .pii import decrypt_text
        return decrypt_text(self.phone)

    @property
    def body_plain(self):
        from .pii import decrypt_text
        return decrypt_text(self.body)

    @property
    def extra_data(self):
        return self.extra if isinstance(self.extra, dict) else {}

    @property
    def relationship(self):
        extra = self.extra_data
        return extra.get("relationship") or extra.get("relation_type") or extra.get("relation") or ""

    @property
    def preferred_display(self):
        extra = self.extra_data
        date = extra.get("preferred_date") or extra.get("date") or extra.get("day") or ""
        slot = extra.get("preferred_time_slot") or extra.get("time") or ""
        return " ".join(part for part in (date, slot) if part)

    @property
    def preferred_date_value(self):
        extra = self.extra_data
        return extra.get("preferred_date") or extra.get("date") or extra.get("day") or ""

    @classmethod
    def kind_from_label(cls, label):
        text = label or ""
        if "견학" in text:
            return cls.KIND_TOUR
        return cls.KIND_CONSULT

    @classmethod
    def normalize_status(cls, value):
        raw = (value or "").strip()
        if raw in cls.STATUS_NORMALIZE:
            return cls.STATUS_NORMALIZE[raw]
        return cls.STATUS_NORMALIZE.get(raw.upper(), raw.lower())

    @property
    def status_key(self):
        return self.normalize_status(self.status)

    @property
    def is_cancelled(self):
        return self.status_key == "cancelled"

    @property
    def is_cancellable(self):
        if self.kind not in (self.KIND_CONSULT, self.KIND_TOUR):
            return False
        if self.status_key in self.LOCKED_STATUSES:
            return False
        return True

    @property
    def status_admin_label(self):
        if self.is_cancelled:
            return "취소됨(회원 취소)"
        mapped = {
            "received": "접수완료",
            "waiting": "상담대기",
            "done": "상담완료",
            "approved": "승인",
            "rejected": "반려",
            "cancelled": "취소됨",
        }
        return mapped.get(self.status_key) or self.get_status_display()


class AuditLog(models.Model):
    actor = models.CharField(max_length=80)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=120, blank=True)
    ip = models.CharField(max_length=64, blank=True)
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


class DailyMenu(models.Model):
    date = models.DateField("날짜", unique=True)
    breakfast = models.CharField("아침", max_length=400, blank=True)
    lunch = models.CharField("점심", max_length=400, blank=True)
    dinner = models.CharField("저녁", max_length=400, blank=True)
    snack = models.CharField("간식", max_length=400, blank=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "일일 식단"
        verbose_name_plural = "메인 식단"

    def __str__(self):
        return self.date.isoformat()

    def meal_rows(self):
        return [
            {"label": "아침", "text": (self.breakfast or "").strip(), "tone": ""},
            {"label": "점심", "text": (self.lunch or "").strip(), "tone": "highlight"},
            {"label": "저녁", "text": (self.dinner or "").strip(), "tone": ""},
            {"label": "간식", "text": (self.snack or "").strip(), "tone": "snack"},
        ]

    def banner_items(self):
        meals = [(row["label"], row["text"]) for row in self.meal_rows() if row["text"]]
        if not meals:
            return ["식단 준비 중"]
        if len(meals) == 1:
            return [part.strip() for part in re.split(r"[,/·\n]+", meals[0][1]) if part.strip()] or [meals[0][1]]
        return [f"{label} {text}" for label, text in meals]

    def as_banner(self):
        weekdays = "월화수목금토일"
        return {
            "date": self.date.isoformat(),
            "label": f"{self.date.month}월 {self.date.day}일 ({weekdays[self.date.weekday()]})",
            "items": self.banner_items(),
            "meals": self.meal_rows(),
        }


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


SITE_FIELD_GROUPS = [
    ("기관 정보", [
        ("center_name", "시설명", "헤리움 케어센터"),
        ("owner", "대표자 / 원장", "강시중"),
        ("address", "주소 (푸터)", "영천시 역전로 16(완산동 1081-5)"),
        ("address_full", "주소 (상세)", "경상북도 영천시 역전로 16 (완산동 1081-5)"),
        ("biz_no", "고유번호(사업자번호)", "123-45-67890"),
        ("phone", "대표전화", "054-334-9986"),
        ("fax", "팩스", "054-334-9985"),
        ("email", "이메일", "info@example.com"),
        ("hours", "상담시간", "평일 09:00 ~ 18:00 (주말·공휴일은 사전 예약)"),
        ("scale", "시설 규모", "지상 3층 · 지하 1층 / 연면적 2,450㎡"),
    ]),
    ("SNS", [
        ("blog_url", "블로그 주소", ""),
        ("instagram_url", "인스타그램 주소", ""),
    ]),
    ("면회·견학", [
        ("visit_hours", "면회 시간", "매일 10:00~11:30, 14:00~16:30 (식사 시간 제외)"),
        ("visit_rule", "면회 예약 안내", "방문 전 전화 예약 (감염 상황 시 조정될 수 있음)"),
        ("tour_hours", "견학 운영 시간", "평일 10:00~16:00"),
        ("tour_slots", "견학 회차", "평일 10:00 / 14:00"),
        ("tour_duration", "견학 소요 시간", "약 40~50분"),
        ("tour_max", "견학 1회 최대 인원", "4"),
    ]),
    ("오시는 길", [
        ("map_query", "지도 검색어", "경상북도 영천시 역전로 16"),
        ("location_lead", "오시는 길 안내 문구", "헤리움 케어센터는 영천시 완산동에 있습니다. 방문 전 전화로 예약해 주시면 안내가 더 수월합니다."),
        ("transit_bus", "버스 안내", "영천역 인근 하차 후 도보 약 5~10분"),
        ("transit_train", "기차 안내", "영천역에서 나와 역전로 방면으로 이동"),
        ("transit_parking", "주차 안내", "센터 앞 방문객 주차장 이용 (한정 대수)"),
    ]),
    ("이용 요금", [
        ("fees_note", "요금 안내 문구", "아래 금액은 안내용 예시입니다. 실제 수가는 공단 고시와 감경 여부에 따라 달라집니다."),
        ("fees_room", "상급 침실 이용료", "특실 30,000원 / 1인실 22,500원 / 2인실 15,000원 (1일당)"),
    ]),
    ("층별 안내", [
        ("floor_3", "3층", "생활실, 간호스테이션, 프로그램실, 휴게실"),
        ("floor_2", "2층", "생활실, 물리치료실, 작업치료실, 면회실"),
        ("floor_1", "1층", "로비, 사무실, 식당, 주야간보호, 상담실"),
        ("floor_b1", "지하 1층", "주방, 세탁실, 기계실, 창고"),
    ]),
    ("소개 문구", [
        ("main_headline", "메인 환영 문구", "<span>따스한 손길</span>로 전하는 <span>사랑</span>, <br><span>헤리움 케어센터</span>가 함께합니다."),
        ("about_greeting", "인사말", "헤리움 케어센터를 방문해 주신 여러분께 감사드립니다.\n헤리움 케어센터는 어르신이 존중받는 일상 속에서 안전하게 지내실 수 있도록, 장기요양 시설급여와 재가급여를 함께 운영하고 있습니다.\n입소와 주야간보호, 방문요양을 고민 중이시라면 언제든 센터를 찾아 주십시오."),
        ("facility_intro", "시설 안내 소개", "생활실, 프로그램실, 식당, 재활치료실 등 어르신의 하루가 머무는 공간을 소개합니다."),
        ("org_lead", "조직 안내 문구", "원장을 중심으로 간호·요양·사회복지·영양·재활팀이 함께 어르신을 돌봅니다."),
    ]),
]
SITE_FIELD_KEYS = [key for _, fields in SITE_FIELD_GROUPS for key, _, _ in fields]
SITE_DEFAULTS = {key: default for _, fields in SITE_FIELD_GROUPS for key, _, default in fields}


def ensure_site_info():
    info = {}
    for group_name, fields in SITE_FIELD_GROUPS:
        for key, label, default in fields:
            item, created = SiteContent.objects.get_or_create(
                key=key,
                defaults={"label": label, "body": default},
            )
            if not created and item.label != label:
                item.label = label
                item.save(update_fields=["label"])
            info[key] = item.body
    return info


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


class StoredUpload(models.Model):
    """Render 디스크가 비워져도 남도록 Neon(Postgres)에 파일을 둡니다."""

    folder = models.CharField(max_length=40, default="posts")
    filename = models.CharField(max_length=200)
    content_type = models.CharField(max_length=120, default="application/octet-stream")
    data = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def public_url(self):
        return f"/uploads/db/{self.pk}/{self.filename}"
