from django.conf import settings
from django.db import models


class Profile(models.Model):
    ROLE_MEMBER = "member"
    ROLE_GUARDIAN = "guardian"
    ROLE_STAFF = "staff"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_MEMBER, "MEMBER"),
        (ROLE_GUARDIAN, "보호자"),
        (ROLE_STAFF, "STAFF"),
        (ROLE_ADMIN, "ADMIN"),
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
    login_failures = models.IntegerField(default=0)
    login_locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "회원 프로필"
        verbose_name_plural = "회원 프로필"

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.user.is_staff

    @property
    def is_staff_role(self):
        return self.role == self.ROLE_STAFF or self.user.is_staff


class SeniorProfile(models.Model):
    RELATION_CHOICES = [
        ("부", "부"),
        ("모", "모"),
        ("조부모", "조부모"),
        ("배우자", "배우자"),
        ("자녀", "자녀"),
        ("기타", "기타"),
    ]
    GRADE_CHOICES = [
        ("1등급", "1등급"),
        ("2등급", "2등급"),
        ("3등급", "3등급"),
        ("4등급", "4등급"),
        ("5등급", "5등급"),
        ("인지지원등급", "인지지원등급"),
        ("등급외/신청중", "등급외/신청중"),
        ("해당없음", "해당없음"),
    ]

    guardian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patients",
        verbose_name="보호자",
    )
    shared_user_id = models.CharField("공유 회원 ID", max_length=80, blank=True)
    name = models.CharField("어르신 성함", max_length=50)
    relationship = models.CharField("보호자와의 관계", max_length=30, choices=RELATION_CHOICES, default="기타")
    birth_date = models.DateField("생년월일", null=True, blank=True)
    care_grade = models.CharField("장기요양등급", max_length=20, blank=True, choices=GRADE_CHOICES)
    note = models.TextField("특이사항", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "senior_profiles"
        ordering = ["-updated_at", "-id"]
        verbose_name = "어르신 프로필"
        verbose_name_plural = "어르신 프로필"

    def __str__(self):
        return f"{self.name} ({self.relationship})"

    def as_card(self):
        return {
            "id": self.id,
            "name": self.name,
            "relationship": self.relationship,
            "birth_date": self.birth_date.isoformat() if self.birth_date else "",
            "care_grade": self.care_grade,
            "note": self.note,
        }


class SharedUser(models.Model):
    """공유 PostgreSQL users 테이블. managed=False — DROP/컬럼 파괴 금지."""

    ROLE_USER = "user"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [
        (ROLE_USER, "USER"),
        (ROLE_ADMIN, "ADMIN"),
    ]

    id = models.CharField(primary_key=True, max_length=80)
    name = models.TextField("이름")
    guardian_name = models.TextField(null=True, blank=True)
    phone = models.TextField("연락처", unique=True)
    username = models.TextField("로그인 아이디", null=True, blank=True)
    email = models.TextField("이메일", null=True, blank=True)
    password_hash = models.TextField("비밀번호 해시")
    login_failures = models.IntegerField(default=0)
    login_locked_until = models.TextField(null=True, blank=True)
    role = models.TextField("역할", default=ROLE_USER, choices=ROLE_CHOICES)
    herium_linked = models.IntegerField(default=0)
    herium_relation = models.TextField(null=True, blank=True)
    herium_note = models.TextField(null=True, blank=True)
    marketing_agreed = models.IntegerField(default=0)
    age_14_agreed = models.IntegerField("만 14세 이상 확인", default=0)
    withdrawn_at = models.TextField(null=True, blank=True)
    created_at = models.TextField("가입일시")

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "공유 회원"
        verbose_name_plural = "공유 회원"

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def is_over_14(self):
        return int(self.age_14_agreed or 0) == 1

    @is_over_14.setter
    def is_over_14(self, value):
        self.age_14_agreed = 1 if value else 0


class SharedSiteContent(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    content_key = models.TextField("키", unique=True)
    title = models.TextField("제목", null=True, blank=True)
    content = models.TextField("내용", null=True, blank=True)
    image_url = models.TextField("이미지 URL", null=True, blank=True)
    updated_at = models.TextField("수정일시")

    class Meta:
        managed = False
        db_table = "site_contents"
        verbose_name = "공유 CMS"
        verbose_name_plural = "공유 CMS"

    def __str__(self):
        return self.content_key


class CareConsultation(models.Model):
    STATUS_RECEIVED = "RECEIVED"
    STATUS_PENDING = "PENDING"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_RECEIVED, "접수완료"),
        (STATUS_PENDING, "상담대기"),
        (STATUS_CONFIRMED, "상담완료"),
        (STATUS_CANCELLED, "취소"),
    ]
    STATUS_BADGE = {
        STATUS_RECEIVED: "접수완료",
        STATUS_PENDING: "상담대기",
        STATUS_CONFIRMED: "상담완료",
        STATUS_CANCELLED: "취소",
    }
    CARE_LEVELS = [
        ("1_2등급", "1~2등급"),
        ("3_5등급", "3~5등급"),
        ("신청중_미인정", "신청중 또는 미인정"),
    ]
    MOBILITY = [
        ("자립보행", "자립보행"),
        ("부축필요", "부축필요"),
        ("와상", "와상"),
    ]
    SLOTS = [
        ("오전(10-12)", "오전 10~12"),
        ("오후(14-16)", "오후 14~16"),
        ("오후(16-18)", "오후 16~18"),
        ("시간무관", "시간무관"),
    ]

    id = models.CharField(primary_key=True, max_length=80)
    user_id = models.CharField("회원 ID", max_length=80, null=True, blank=True)
    applicant_name = models.TextField("신청자명")
    applicant_phone = models.TextField("연락처")
    relation_type = models.TextField("어르신과의 관계", default="")
    care_level = models.TextField("장기요양등급", default="", choices=CARE_LEVELS)
    mobility_status = models.TextField("보행상태", default="", choices=MOBILITY)
    preferred_date = models.TextField("희망일자", null=True, blank=True)
    preferred_time_slot = models.TextField("희망시간대", null=True, blank=True, choices=SLOTS)
    privacy_agreed = models.IntegerField("개인정보수집동의", default=0)
    confirmed_datetime = models.TextField("확정일시", null=True, blank=True)
    status = models.TextField("상담상태", default=STATUS_PENDING, choices=STATUS_CHOICES)
    sms_sent_at = models.TextField("확정문자발송일시", null=True, blank=True)
    sms_content = models.TextField("확정문자내용", null=True, blank=True)
    sms_ok = models.IntegerField(null=True, blank=True)
    admin_memo = models.TextField(null=True, blank=True)
    created_at = models.TextField("신청일시")
    patient_id = models.CharField("어르신 프로필 ID", max_length=80, null=True, blank=True)
    senior_name = models.TextField("대상 어르신", null=True, blank=True)
    consult_kind = models.TextField("상담 유형", default="입소 상담")

    class Meta:
        managed = False
        db_table = "care_consultations"
        verbose_name = "입소 상담"
        verbose_name_plural = "입소 상담"

    def __str__(self):
        return f"{self.applicant_name} ({self.status})"


class CareSchedule(models.Model):
    CATEGORIES = [
        ("상담", "상담"),
        ("봉사", "봉사"),
        ("시설행사", "시설행사"),
        ("기타", "기타"),
    ]

    id = models.CharField(primary_key=True, max_length=80)
    consultation_id = models.CharField("상담 ID", max_length=80, null=True, blank=True)
    title = models.TextField("일정 제목")
    start_datetime = models.TextField("시작일시")
    end_datetime = models.TextField("종료일시")
    category = models.TextField("분류", default="기타", choices=CATEGORIES)
    memo = models.TextField("메모", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "care_schedules"
        verbose_name = "요양원 일정"
        verbose_name_plural = "요양원 일정"

    def __str__(self):
        return self.title


class Product(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    name = models.TextField("상품명")
    price = models.IntegerField("판매가")
    sale_price = models.IntegerField("할인가", null=True, blank=True)
    stock = models.IntegerField("재고", default=0)
    category = models.TextField("카테고리", default="")
    thumbnail_url = models.TextField("대표이미지 URL", default="")
    description = models.TextField("설명", default="")
    is_hygiene_product = models.IntegerField("위생/피부접촉용품", default=0)
    is_active = models.IntegerField("노출", default=1)
    created_at = models.TextField("등록일시")

    class Meta:
        managed = False
        db_table = "products"
        verbose_name = "의료기 상품"
        verbose_name_plural = "의료기 상품"

    def __str__(self):
        return self.name

    @property
    def sale_status(self):
        if not int(self.is_active or 0):
            return "숨김"
        if int(self.stock or 0) <= 0:
            return "품절"
        return "판매중"


class ShopProfile(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    user_id = models.CharField("회원 ID", max_length=80, unique=True)
    recipient_name = models.TextField("수령인명", default="")
    recipient_phone = models.TextField("연락처", default="")
    zipcode = models.TextField("우편번호", default="")
    address_basic = models.TextField("기본주소", default="")
    address_detail = models.TextField("상세주소", default="")

    class Meta:
        managed = False
        db_table = "shop_profiles"
        verbose_name = "배송 프로필"
        verbose_name_plural = "배송 프로필"

    def __str__(self):
        return self.recipient_name or self.user_id


class Order(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    number = models.TextField("주문번호", unique=True)
    user_id = models.CharField("회원 ID", max_length=80, null=True, blank=True)
    type = models.TextField(default="order")
    name = models.TextField("주문자명")
    phone = models.TextField("연락처")
    address = models.TextField("주소", default="")
    memo = models.TextField(default="")
    topics = models.TextField(default="[]")
    items = models.TextField(default="[]")
    total = models.IntegerField("총결제금액", default=0)
    status = models.TextField("주문상태", default="PENDING")
    created_at = models.TextField("주문일시")
    payment_key = models.TextField("토스 결제키", null=True, blank=True)
    zipcode = models.TextField("우편번호", null=True, blank=True)
    address_basic = models.TextField("기본주소", null=True, blank=True)
    address_detail = models.TextField("상세주소", null=True, blank=True)
    tracking_number = models.TextField("운송장번호", null=True, blank=True)
    recipient_name = models.TextField("수령인명", null=True, blank=True)
    recipient_phone = models.TextField("수령인 연락처", null=True, blank=True)

    class Meta:
        managed = False
        db_table = "orders"
        verbose_name = "주문"
        verbose_name_plural = "주문"

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    order_id = models.CharField("주문 ID", max_length=80)
    product_id = models.CharField("상품 ID", max_length=80, null=True, blank=True)
    product_name = models.TextField("상품명")
    unit_price = models.IntegerField("단가")
    quantity = models.IntegerField("수량")

    class Meta:
        managed = False
        db_table = "order_items"
        verbose_name = "주문 품목"
        verbose_name_plural = "주문 품목"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
