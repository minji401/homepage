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

    def banner_items(self):
        meals = []
        if self.breakfast:
            meals.append(("아침", self.breakfast))
        if self.lunch:
            meals.append(("점심", self.lunch))
        if self.dinner:
            meals.append(("저녁", self.dinner))
        if self.snack:
            meals.append(("간식", self.snack))
        if not meals:
            return ["식단 준비 중"]
        if len(meals) == 1:
            return [part.strip() for part in re.split(r"[,/·\n]+", meals[0][1]) if part.strip()] or [meals[0][1]]
        return [f"{label} {text}" for label, text in meals]

    def as_banner(self):
        return {
            "date": self.date.isoformat(),
            "label": f"{self.date.month}월 {self.date.day}일",
            "items": self.banner_items(),
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
        ("biz_no", "사업자등록번호", "123-45-67890"),
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
