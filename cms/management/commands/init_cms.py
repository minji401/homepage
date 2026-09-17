from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Profile
from cms.models import Application, Banner, Board, Comment, Popup, Post, SearchTerm, SiteContent, VisitLog


class Command(BaseCommand):
    help = "관리자 계정과 예시 게시판·신청·통계 데이터를 준비합니다."

    def handle(self, *args, **options):
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "관리자", "email": "admin@example.com", "is_staff": True, "is_superuser": True},
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        if created or not admin_user.check_password("1234"):
            admin_user.set_password("1234")
        admin_user.save()
        Profile.objects.update_or_create(
            user=admin_user,
            defaults={"name": "관리자", "phone": "054-334-9986", "role": Profile.ROLE_ADMIN, "status": Profile.STATUS_ACTIVE},
        )

        hatsal, created = User.objects.get_or_create(
            username="hatsal",
            defaults={"first_name": "홍길동", "email": "hatsal@example.com"},
        )
        if created:
            hatsal.set_password("1234")
            hatsal.save()
        Profile.objects.update_or_create(
            user=hatsal,
            defaults={"name": "홍길동", "phone": "010-1234-5678", "role": Profile.ROLE_GUARDIAN, "status": Profile.STATUS_ACTIVE},
        )

        extras = [
            ("parkmin", "박민수", "010-2222-3333", Profile.ROLE_MEMBER),
            ("leeguard", "이보람", "010-4444-5555", Profile.ROLE_GUARDIAN),
        ]
        for username, name, phone, role in extras:
            user, made = User.objects.get_or_create(username=username, defaults={"first_name": name})
            if made:
                user.set_password("1234")
                user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={"name": name, "phone": phone, "role": role, "status": Profile.STATUS_ACTIVE},
            )

        boards = [
            ("notice", "공지사항", "운영 공지"),
            ("menu", "식단표", "주간 식단"),
            ("gallery", "갤러리", "활동 사진"),
            ("faq", "자주 묻는 질문", "FAQ"),
            ("review", "이용후기", "보호자 후기"),
            ("volunteer", "자원봉사 안내", "봉사 소식"),
            ("donate", "후원 안내", "후원 소식"),
        ]
        board_map = {}
        for slug, name, desc in boards:
            board, _ = Board.objects.get_or_create(slug=slug, defaults={"name": name, "description": desc})
            board_map[slug] = board

        if not Post.objects.exists():
            notice = board_map["notice"]
            posts = [
                ("2026년 9월 프로그램 안내", "원예치료, 음악치료, 인지프로그램 등 9월 월간 일정을 운영합니다.", True),
                ("시설 점검 안내 (소방·전기)", "소방설비 및 전기 안전 점검을 진행합니다.", False),
                ("신규 면회 수칙 안내", "면회 시간 예약제를 운영합니다.", False),
                ("추석 연휴 운영 안내", "연휴 기간 면회 시간을 조정합니다.", False),
                ("입소 상담 예약제 안내", "입소 상담은 사전 예약 후 진행됩니다.", False),
            ]
            for title, body, pinned in posts:
                Post.objects.create(board=notice, title=title, body=body, author_name="관리자", is_pinned=pinned)
            faqs = [
                ("입소하려면 장기요양등급이 꼭 필요한가요?", "시설급여·재가급여를 이용하려면 국민건강보험공단의 장기요양 인정이 필요합니다."),
                ("면회는 언제 가능한가요?", "매일 10:00~11:30, 14:00~16:30입니다. 방문 전 전화 예약을 권합니다."),
                ("이용 요금은 어떻게 계산되나요?", "장기요양 수가의 본인부담과 식재료비 등 비급여를 합산합니다."),
            ]
            for title, body in faqs:
                Post.objects.create(board=board_map["faq"], title=title, body=body, author_name="관리자")
            sample = Post.objects.filter(board=notice).first()
            if sample:
                Comment.objects.create(post=sample, author_name="홍길동", body="프로그램 일정 잘 보았습니다.")

        menu_board = board_map["menu"]
        if not Post.objects.filter(board=menu_board).exists():
            Post.objects.create(board=menu_board, title="9월 14일 ~ 9월 20일 주간 식단표", body="잡곡밥, 미역국, 고등어구이", author_name="영양팀", image="/img/1.jpg")
            Post.objects.create(board=menu_board, title="9월 7일 ~ 9월 13일 주간 식단표", body="현미밥, 된장찌개, 제육볶음", author_name="영양팀", image="/img/1.jpg")

        gallery_board = board_map["gallery"]
        if not Post.objects.filter(board=gallery_board).exists():
            samples = [
                ("원예 프로그램", "화분을 가꾸며 손 운동과 감각을 깨웁니다.", "night", "/img/gallery1.jpg"),
                ("음악 활동", "노래와 리듬 악기로 즐거운 오후의 시간.", "night", "/img/gallery2.jpg"),
                ("야외 산책", "날씨 좋은 날 정원과 주변 길을 걷습니다.", "nursing", "/img/gallery4.jpg"),
                ("방문요양 일상 지원", "자택에서 식사·이동·위생을 돕습니다.", "home", "/img/2.jpg"),
            ]
            for title, body, category, image in samples:
                Post.objects.create(
                    board=gallery_board, title=title, body=body, author_name="관리자",
                    category=category, image=image,
                )

        contents = [
            ("main_headline", "메인 환영 문구", "<span>따스한 손길</span>로 전하는 <span>사랑</span>, <br><span>헤리움 케어센터</span>가 함께합니다."),
            ("about_greeting", "인사말", "헤리움 케어센터를 방문해 주신 여러분께 감사드립니다.\n헤리움 케어센터는 어르신이 존중받는 일상 속에서 안전하게 지내실 수 있도록, 장기요양 시설급여와 재가급여를 함께 운영하고 있습니다.\n입소와 주야간보호, 방문요양을 고민 중이시라면 언제든 센터를 찾아 주십시오."),
            ("facility_intro", "시설 안내 소개", "생활실, 프로그램실, 식당, 재활치료실 등 어르신의 하루가 머무는 공간을 소개합니다."),
        ]
        for key, label, body in contents:
            SiteContent.objects.get_or_create(key=key, defaults={"label": label, "body": body})

        if not Popup.objects.exists():
            Popup.objects.create(title="면회 안내", body="면회는 하루 2회, 사전 전화 예약을 권합니다.", is_active=False)

        if not Banner.objects.exists():
            Banner.objects.bulk_create([
                Banner(title="메인 배너 1", image="/img/1.jpg", sort_order=1),
                Banner(title="메인 배너 2", image="/img/2.jpg", sort_order=2),
                Banner(title="메인 배너 3", image="/img/3.jpg", sort_order=3),
            ])
        for banner in Banner.objects.all():
            if banner.image and not banner.image.startswith("/") and not banner.image.startswith("http"):
                banner.image = "/" + banner.image
                banner.save(update_fields=["image"])

        keywords = ["입소안내", "이용요금", "주야간보호", "방문요양", "오시는 길", "자원봉사", "식단표"]
        for i, word in enumerate(keywords):
            SearchTerm.objects.get_or_create(
                keyword=word,
                defaults={"search_count": 20 - i, "is_recommended": True, "recommend_order": i},
            )

        if not Application.objects.exists():
            Application.objects.create(
                kind=Application.KIND_CONSULT, name="김순자", phone="010-1111-2222",
                title="입소 상담 요청", body="어머니 입소 상담을 희망합니다.", extra={"type": "입소 상담"},
            )
            Application.objects.create(
                kind=Application.KIND_VOLUNTEER, name="박민수", phone="010-2222-3333",
                title="말벗 봉사", body="주말 오후 봉사 가능합니다.", extra={"type": "말벗 봉사"},
            )
            Application.objects.create(
                kind=Application.KIND_DONATE, name="이보람", phone="010-4444-5555",
                title="물품 후원", body="계절 이불 후원 문의드립니다.", extra={"type": "물품 후원"},
            )

        if VisitLog.objects.count() < 10:
            now = timezone.now()
            for i in range(14):
                log = VisitLog.objects.create(
                    path="/main.html",
                    referer="https://www.google.com/" if i % 2 == 0 else "https://search.naver.com/",
                    session_key="seed",
                )
                VisitLog.objects.filter(pk=log.pk).update(visited_at=now - timedelta(days=i, hours=i))

        self.stdout.write(self.style.SUCCESS("관리자 admin / 1234, 일반 hatsal / 1234 준비 완료"))
