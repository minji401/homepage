from django.db import migrations, models


def apply_shared_tables(apps, schema_editor):
    from accounts.shared_schema import ensure_integration_schema

    ensure_integration_schema()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_login_lock_and_reset"),
    ]

    operations = [
        migrations.CreateModel(
            name="SharedSiteContent",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("content_key", models.TextField(unique=True, verbose_name="키")),
                ("title", models.TextField(blank=True, null=True, verbose_name="제목")),
                ("content", models.TextField(blank=True, null=True, verbose_name="내용")),
                ("image_url", models.TextField(blank=True, null=True, verbose_name="이미지 URL")),
                ("updated_at", models.TextField(verbose_name="수정일시")),
            ],
            options={
                "verbose_name": "공유 CMS",
                "verbose_name_plural": "공유 CMS",
                "db_table": "site_contents",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="CareConsultation",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("user_id", models.CharField(blank=True, max_length=80, null=True, verbose_name="회원 ID")),
                ("applicant_name", models.TextField(verbose_name="신청자명")),
                ("applicant_phone", models.TextField(verbose_name="연락처")),
                ("relation_type", models.TextField(default="", verbose_name="어르신과의 관계")),
                ("care_level", models.TextField(default="", verbose_name="장기요양등급")),
                ("mobility_status", models.TextField(default="", verbose_name="보행상태")),
                ("preferred_date", models.TextField(blank=True, null=True, verbose_name="희망일자")),
                ("preferred_time_slot", models.TextField(blank=True, null=True, verbose_name="희망시간대")),
                ("privacy_agreed", models.IntegerField(default=0, verbose_name="개인정보수집동의")),
                ("confirmed_datetime", models.TextField(blank=True, null=True, verbose_name="확정일시")),
                ("status", models.TextField(default="PENDING", verbose_name="상담상태")),
                ("sms_sent_at", models.TextField(blank=True, null=True, verbose_name="확정문자발송일시")),
                ("sms_content", models.TextField(blank=True, null=True, verbose_name="확정문자내용")),
                ("sms_ok", models.IntegerField(blank=True, null=True)),
                ("admin_memo", models.TextField(blank=True, null=True)),
                ("created_at", models.TextField(verbose_name="신청일시")),
            ],
            options={
                "verbose_name": "입소 상담",
                "verbose_name_plural": "입소 상담",
                "db_table": "care_consultations",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="CareSchedule",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("consultation_id", models.CharField(blank=True, max_length=80, null=True, verbose_name="상담 ID")),
                ("title", models.TextField(verbose_name="일정 제목")),
                ("start_datetime", models.TextField(verbose_name="시작일시")),
                ("end_datetime", models.TextField(verbose_name="종료일시")),
                ("category", models.TextField(default="기타", verbose_name="분류")),
                ("memo", models.TextField(blank=True, null=True, verbose_name="메모")),
            ],
            options={
                "verbose_name": "요양원 일정",
                "verbose_name_plural": "요양원 일정",
                "db_table": "care_schedules",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("name", models.TextField(verbose_name="상품명")),
                ("price", models.IntegerField(verbose_name="판매가")),
                ("sale_price", models.IntegerField(blank=True, null=True, verbose_name="할인가")),
                ("stock", models.IntegerField(default=0, verbose_name="재고")),
                ("category", models.TextField(default="", verbose_name="카테고리")),
                ("thumbnail_url", models.TextField(default="", verbose_name="대표이미지 URL")),
                ("description", models.TextField(default="", verbose_name="설명")),
                ("is_hygiene_product", models.IntegerField(default=0, verbose_name="위생/피부접촉용품")),
                ("is_active", models.IntegerField(default=1, verbose_name="노출")),
                ("created_at", models.TextField(verbose_name="등록일시")),
            ],
            options={
                "verbose_name": "의료기 상품",
                "verbose_name_plural": "의료기 상품",
                "db_table": "products",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="ShopProfile",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("user_id", models.CharField(max_length=80, unique=True, verbose_name="회원 ID")),
                ("recipient_name", models.TextField(default="", verbose_name="수령인명")),
                ("recipient_phone", models.TextField(default="", verbose_name="연락처")),
                ("zipcode", models.TextField(default="", verbose_name="우편번호")),
                ("address_basic", models.TextField(default="", verbose_name="기본주소")),
                ("address_detail", models.TextField(default="", verbose_name="상세주소")),
            ],
            options={
                "verbose_name": "배송 프로필",
                "verbose_name_plural": "배송 프로필",
                "db_table": "shop_profiles",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("number", models.TextField(unique=True, verbose_name="주문번호")),
                ("user_id", models.CharField(blank=True, max_length=80, null=True, verbose_name="회원 ID")),
                ("type", models.TextField(default="order")),
                ("name", models.TextField(verbose_name="주문자명")),
                ("phone", models.TextField(verbose_name="연락처")),
                ("address", models.TextField(default="", verbose_name="주소")),
                ("memo", models.TextField(default="")),
                ("topics", models.TextField(default="[]")),
                ("items", models.TextField(default="[]")),
                ("total", models.IntegerField(default=0, verbose_name="총결제금액")),
                ("status", models.TextField(default="PENDING", verbose_name="주문상태")),
                ("created_at", models.TextField(verbose_name="주문일시")),
                ("payment_key", models.TextField(blank=True, null=True, verbose_name="토스 결제키")),
                ("zipcode", models.TextField(blank=True, null=True, verbose_name="우편번호")),
                ("address_basic", models.TextField(blank=True, null=True, verbose_name="기본주소")),
                ("address_detail", models.TextField(blank=True, null=True, verbose_name="상세주소")),
                ("tracking_number", models.TextField(blank=True, null=True, verbose_name="운송장번호")),
                ("recipient_name", models.TextField(blank=True, null=True, verbose_name="수령인명")),
                ("recipient_phone", models.TextField(blank=True, null=True, verbose_name="수령인 연락처")),
            ],
            options={
                "verbose_name": "주문",
                "verbose_name_plural": "주문",
                "db_table": "orders",
                "managed": False,
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.CharField(max_length=80, primary_key=True, serialize=False)),
                ("order_id", models.CharField(max_length=80, verbose_name="주문 ID")),
                ("product_id", models.CharField(blank=True, max_length=80, null=True, verbose_name="상품 ID")),
                ("product_name", models.TextField(verbose_name="상품명")),
                ("unit_price", models.IntegerField(verbose_name="단가")),
                ("quantity", models.IntegerField(verbose_name="수량")),
            ],
            options={
                "verbose_name": "주문 품목",
                "verbose_name_plural": "주문 품목",
                "db_table": "order_items",
                "managed": False,
            },
        ),
        migrations.RunPython(apply_shared_tables, migrations.RunPython.noop),
    ]
