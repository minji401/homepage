from datetime import date, timedelta
from functools import wraps
from pathlib import Path
import re
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import Profile
from .menu_import import parse_menu_table, rows_from_csv, rows_from_xlsx
from .models import (
    SITE_FIELD_GROUPS,
    SITE_FIELD_KEYS,
    USAGE_AS_OF_KEY,
    WAITLIST_TYPES,
    Application,
    Banner,
    Board,
    Comment,
    DailyMenu,
    Popup,
    Post,
    SearchTerm,
    SiteContent,
    UsageStat,
    VisitLog,
    WaitlistEntry,
    ensure_site_info,
    ensure_usage_stats,
)

CONTENT_BOARDS = {
    "notice": {"name": "공지사항", "has_image": False, "has_category": False},
    "menu": {"name": "식단표", "has_image": True, "has_category": False},
    "gallery": {"name": "갤러리", "has_image": True, "has_category": True},
    "faq": {"name": "자주 묻는 질문", "has_image": False, "has_category": False},
}
GALLERY_CATEGORIES = [
    ("night", "주야간보호"),
    ("nursing", "요양원"),
    ("home", "가정방문급여"),
]


def staff_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/login.html")
        profile = getattr(request.user, "profile", None)
        if not (request.user.is_staff or (profile and profile.role == Profile.ROLE_ADMIN)):
            return HttpResponseForbidden("관리자만 접근할 수 있습니다.")
        if profile and profile.status != Profile.STATUS_ACTIVE:
            return redirect("/login.html")
        return view(request, *args, **kwargs)

    return wrapper


def _json_body(request):
    import json

    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def _ensure_board(slug):
    meta = CONTENT_BOARDS[slug]
    board, _ = Board.objects.get_or_create(slug=slug, defaults={"name": meta["name"]})
    return board


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


def _save_upload(upload, folder="posts"):
    suffix = Path(upload.name).suffix.lower()
    if suffix not in IMAGE_EXTS:
        return ""
    dest_dir = Path(settings.MEDIA_ROOT) / folder
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", upload.name)
    name = f"{int(time.time())}_{safe}"
    dest = dest_dir / name
    with dest.open("wb") as out:
        for chunk in upload.chunks():
            out.write(chunk)
    return f"/uploads/{folder}/{name}"


def _author_name(user):
    profile = getattr(user, "profile", None)
    return (profile.name if profile and profile.name else user.first_name) or user.username


@staff_required
def dashboard(request):
    today = timezone.localdate()
    week_ago = today - timedelta(days=6)
    return render(request, "staff/dashboard.html", {
        "member_count": User.objects.filter(profile__status=Profile.STATUS_ACTIVE).count(),
        "member_total": User.objects.count(),
        "new_week": User.objects.filter(date_joined__date__gte=week_ago).count(),
        "waiting_count": Application.objects.filter(status=Application.STATUS_WAITING).count(),
        "today_visits": VisitLog.objects.filter(visited_at__date=today).count(),
        "notice_count": Post.objects.filter(board__slug="notice").count(),
        "menu_count": Post.objects.filter(board__slug="menu").count(),
        "gallery_count": Post.objects.filter(board__slug="gallery").count(),
        "latest_notices": Post.objects.filter(board__slug="notice").order_by("-created_at")[:5],
        "latest_menus": Post.objects.filter(board__slug="menu").order_by("-created_at")[:5],
        "latest_gallery": Post.objects.filter(board__slug="gallery").order_by("-created_at")[:5],
        "recent_members": User.objects.select_related("profile").order_by("-date_joined")[:6],
    })


@staff_required
def members(request):
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort") or "-date_joined"
    status = (request.GET.get("status") or "").strip()
    show_withdrawn = request.GET.get("withdrawn") == "1"
    allowed = {
        "date_joined": "date_joined",
        "-date_joined": "-date_joined",
        "username": "username",
        "name": "profile__name",
    }
    if sort not in allowed:
        sort = "-date_joined"
    allowed_status = {
        Profile.STATUS_ACTIVE,
        Profile.STATUS_SUSPENDED,
        Profile.STATUS_WITHDRAWN,
    }
    users = User.objects.select_related("profile").order_by(allowed[sort])
    if status in allowed_status:
        users = users.filter(profile__status=status)
    elif not show_withdrawn:
        users = users.exclude(profile__status=Profile.STATUS_WITHDRAWN)
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(profile__name__icontains=q)
            | Q(email__icontains=q)
            | Q(profile__phone__icontains=q)
        )
    return render(
        request,
        "staff/members.html",
        {"users": users, "q": q, "sort": sort, "status": status, "show_withdrawn": show_withdrawn},
    )


@staff_required
def member_detail(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    if request.method == "POST":
        return member_action(request, user_id)
    return render(request, "staff/member_detail.html", {"u": target})


@staff_required
@require_POST
def member_action(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    profile, _ = Profile.objects.get_or_create(
        user=target, defaults={"name": target.first_name or target.username, "phone": ""}
    )
    action = request.POST.get("action")
    admin_count = User.objects.filter(Q(is_staff=True) | Q(profile__role=Profile.ROLE_ADMIN)).exclude(
        profile__status=Profile.STATUS_WITHDRAWN
    ).count()
    next_url = request.POST.get("next") or "/staff/members/"

    if action == "suspend":
        if target == request.user:
            messages.error(request, "본인 계정은 정지할 수 없습니다.")
        else:
            profile.status = Profile.STATUS_SUSPENDED
            target.is_active = False
            profile.save(update_fields=["status"])
            target.save(update_fields=["is_active"])
            messages.success(request, f"{profile.name} 회원을 정지했습니다.")
    elif action == "restore":
        profile.status = Profile.STATUS_ACTIVE
        target.is_active = True
        profile.save(update_fields=["status"])
        target.save(update_fields=["is_active"])
        messages.success(request, f"{profile.name} 회원을 복구했습니다.")
    elif action == "withdraw":
        if target == request.user:
            messages.error(request, "본인 계정은 탈퇴 처리할 수 없습니다.")
        else:
            profile.status = Profile.STATUS_WITHDRAWN
            target.is_active = False
            profile.save(update_fields=["status"])
            target.save(update_fields=["is_active"])
            messages.success(request, f"{profile.name} 회원을 강제 탈퇴 처리했습니다.")
    elif action == "make_admin":
        profile.role = Profile.ROLE_ADMIN
        target.is_staff = True
        profile.save(update_fields=["role"])
        target.save(update_fields=["is_staff"])
        messages.success(request, f"{profile.name} 님에게 관리자 권한을 부여했습니다.")
    elif action == "remove_admin":
        if target == request.user:
            messages.error(request, "본인 관리자 권한은 회수할 수 없습니다.")
        elif admin_count <= 1:
            messages.error(request, "마지막 관리자 권한은 회수할 수 없습니다.")
        else:
            profile.role = Profile.ROLE_MEMBER
            target.is_staff = False
            profile.save(update_fields=["role"])
            target.save(update_fields=["is_staff"])
            messages.success(request, f"{profile.name} 님의 관리자 권한을 회수했습니다.")
    elif action == "set_role":
        role = request.POST.get("role")
        if role in dict(Profile.ROLE_CHOICES) and role != Profile.ROLE_ADMIN:
            if profile.role == Profile.ROLE_ADMIN and admin_count <= 1:
                messages.error(request, "마지막 관리자 권한은 회수할 수 없습니다.")
            else:
                profile.role = role
                if role != Profile.ROLE_ADMIN:
                    target.is_staff = False
                    target.save(update_fields=["is_staff"])
                profile.save(update_fields=["role"])
                messages.success(request, "회원 권한을 변경했습니다.")
    return redirect(next_url)


@staff_required
def posts_list(request, slug):
    if slug not in CONTENT_BOARDS:
        return redirect("/staff/posts/notice/")
    board = _ensure_board(slug)
    meta = CONTENT_BOARDS[slug]
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort") or "-created_at"
    allowed = {"created_at": "created_at", "-created_at": "-created_at", "title": "title"}
    posts = Post.objects.filter(board=board).order_by(allowed.get(sort, "-created_at"))
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(body__icontains=q) | Q(category__icontains=q))
    return render(request, "staff/posts.html", {
        "board": board,
        "slug": slug,
        "meta": meta,
        "posts": posts,
        "q": q,
        "sort": sort,
        "categories": GALLERY_CATEGORIES,
    })


@staff_required
@require_POST
def posts_bulk(request, slug):
    if slug not in CONTENT_BOARDS:
        return redirect("/staff/posts/notice/")
    board = _ensure_board(slug)
    ids = request.POST.getlist("ids")
    action = request.POST.get("bulk")
    qs = Post.objects.filter(board=board, id__in=ids)
    count = qs.count()
    if not count:
        messages.error(request, "선택된 항목이 없습니다.")
    elif action == "delete":
        qs.delete()
        messages.success(request, f"{count}건을 삭제했습니다.")
    elif action == "hide":
        qs.update(is_hidden=True)
        messages.success(request, f"{count}건을 숨김 처리했습니다.")
    elif action == "show":
        qs.update(is_hidden=False)
        messages.success(request, f"{count}건을 공개했습니다.")
    elif action == "pin":
        qs.update(is_pinned=True)
        messages.success(request, f"{count}건을 상단 고정했습니다.")
    elif action == "unpin":
        qs.update(is_pinned=False)
        messages.success(request, f"{count}건의 고정을 해제했습니다.")
    return redirect(f"/staff/posts/{slug}/")


@staff_required
def boards(request):
    return redirect("/staff/posts/notice/")


@staff_required
@require_http_methods(["GET", "POST"])
def post_edit(request, post_id=None, slug=None):
    post = get_object_or_404(Post, pk=post_id) if post_id else None
    if slug is None:
        slug = post.board.slug if post else (request.GET.get("slug") or "notice")
    if slug not in CONTENT_BOARDS:
        slug = "notice"
    board = _ensure_board(slug)
    meta = CONTENT_BOARDS[slug]
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        body = (request.POST.get("body") or "").strip()
        if not title:
            messages.error(request, "제목을 입력해 주세요.")
        elif slug == "notice" and not body:
            messages.error(request, "내용을 입력해 주세요.")
        else:
            if post is None:
                post = Post(author=request.user, board=board)
            post.board = board
            post.title = title
            post.body = body
            post.author_name = _author_name(request.user)
            post.category = request.POST.get("category") or ""
            post.is_pinned = request.POST.get("is_pinned") == "on"
            post.is_hidden = request.POST.get("is_hidden") == "on"
            upload = request.FILES.get("image")
            if upload:
                saved = _save_upload(upload)
                if not saved:
                    messages.error(request, "jpg, png, gif, webp 이미지만 올릴 수 있습니다.")
                    return render(request, "staff/post_form.html", {
                        "post": post,
                        "slug": slug,
                        "board": board,
                        "meta": meta,
                        "categories": GALLERY_CATEGORIES,
                    })
                post.image = saved
            post.save()
            messages.success(request, "저장되었습니다.")
            return redirect(f"/staff/posts/{slug}/")
    return render(request, "staff/post_form.html", {
        "post": post,
        "slug": slug,
        "board": board,
        "meta": meta,
        "categories": GALLERY_CATEGORIES,
    })


@staff_required
@require_POST
def post_action(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    slug = post.board.slug
    action = request.POST.get("action")
    if action == "delete":
        post.delete()
        messages.success(request, "삭제되었습니다.")
    elif action == "pin":
        post.is_pinned = not post.is_pinned
        post.save(update_fields=["is_pinned"])
        messages.success(request, "고정 상태를 변경했습니다.")
    elif action == "hide":
        post.is_hidden = not post.is_hidden
        post.save(update_fields=["is_hidden"])
        messages.success(request, "공개 상태를 변경했습니다.")
    return redirect(f"/staff/posts/{slug}/")


@staff_required
@require_POST
def comment_action(request, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    action = request.POST.get("action")
    if action == "delete":
        comment.delete()
        messages.success(request, "댓글을 삭제했습니다.")
    elif action == "hide":
        comment.is_hidden = not comment.is_hidden
        comment.save(update_fields=["is_hidden"])
    elif action == "edit":
        body = (request.POST.get("body") or "").strip()
        if body:
            comment.body = body
            comment.save(update_fields=["body"])
            messages.success(request, "댓글을 수정했습니다.")
    return redirect("/staff/boards/")


@staff_required
def content(request):
    if request.method == "POST":
        section = request.POST.get("section")
        if section == "text":
            item = get_object_or_404(SiteContent, pk=request.POST.get("id"))
            item.body = request.POST.get("body") or ""
            item.save(update_fields=["body"])
            messages.success(request, f"{item.label}을(를) 저장했습니다.")
        elif section == "popup":
            popup = Popup.objects.first() or Popup(title="안내")
            popup.title = request.POST.get("title") or "안내"
            popup.is_active = request.POST.get("is_active") == "on"
            upload = request.FILES.get("image")
            if upload:
                saved = _save_upload(upload, "popups")
                if not saved:
                    messages.error(request, "jpg, png, gif, webp 이미지만 올릴 수 있습니다.")
                    return redirect("/staff/content/")
                popup.image = saved
            popup.save()
            if popup.is_active and not popup.image:
                popup.is_active = False
                popup.save(update_fields=["is_active"])
                messages.error(request, "팝업 사진을 올린 뒤에 메인에 표시할 수 있습니다.")
            else:
                messages.success(request, "팝업을 저장했습니다.")
        elif section == "banner":
            banner = get_object_or_404(Banner, pk=request.POST.get("id"))
            banner.title = request.POST.get("title") or banner.title
            banner.is_active = request.POST.get("is_active") == "on"
            banner.sort_order = int(request.POST.get("sort_order") or banner.sort_order)
            upload = request.FILES.get("image_file")
            if upload:
                saved = _save_upload(upload, "banners")
                if not saved:
                    messages.error(request, "jpg, png, gif, webp 이미지만 올릴 수 있습니다.")
                    return redirect("/staff/content/")
                banner.image = saved
            banner.save()
            messages.success(request, "배너를 저장했습니다.")
        elif section == "banner_add":
            upload = request.FILES.get("image_file")
            saved = _save_upload(upload, "banners") if upload else ""
            if not saved:
                messages.error(request, "배너 이미지를 선택해 주세요.")
            else:
                Banner.objects.create(
                    title=(request.POST.get("title") or "메인 배너").strip(),
                    image=saved,
                    sort_order=int(request.POST.get("sort_order") or 1),
                    is_active=True,
                )
                messages.success(request, "배너를 추가했습니다.")
        elif section == "banner_delete":
            Banner.objects.filter(pk=request.POST.get("id")).delete()
            messages.success(request, "배너를 삭제했습니다.")
        elif section == "site_info":
            ensure_site_info()
            for key in SITE_FIELD_KEYS:
                item = SiteContent.objects.filter(key=key).first()
                if item:
                    item.body = request.POST.get(key, item.body)
                    item.save(update_fields=["body"])
            messages.success(request, "사이트 정보를 저장했습니다.")
        return redirect("/staff/content/")
    ensure_site_info()
    site_groups = []
    contents_by_key = {item.key: item for item in SiteContent.objects.all()}
    for title, fields in SITE_FIELD_GROUPS:
        rows = []
        for key, label, default in fields:
            item = contents_by_key.get(key)
            rows.append({
                "key": key,
                "label": label,
                "body": item.body if item else default,
                "multiline": key in ("about_greeting", "facility_intro", "main_headline", "org_lead", "fees_note", "location_lead"),
            })
        site_groups.append({"title": title, "fields": rows})
    return render(request, "staff/content.html", {
        "site_groups": site_groups,
        "popup": Popup.objects.first(),
        "banners": Banner.objects.all(),
    })


def _int(value, default=0):
    try:
        return max(0, int(str(value).strip()))
    except (TypeError, ValueError):
        return default


@staff_required
def usage(request):
    stats = ensure_usage_stats()
    as_of, _ = SiteContent.objects.get_or_create(
        key=USAGE_AS_OF_KEY,
        defaults={"label": "이용 현황 기준일", "body": "2026년 9월 15일"},
    )
    if request.method == "POST":
        action = request.POST.get("action") or "save_stats"
        if action == "save_stats":
            as_of.body = (request.POST.get("as_of") or "").strip()
            as_of.save(update_fields=["body"])
            for slug, item in stats.items():
                item.capacity = _int(request.POST.get(f"{slug}_capacity"), item.capacity)
                item.current = _int(request.POST.get(f"{slug}_current"), item.current)
                item.waiting = _int(request.POST.get(f"{slug}_waiting"), item.waiting)
                item.general_capacity = _int(request.POST.get(f"{slug}_general"), item.general_capacity)
                item.dementia_capacity = _int(request.POST.get(f"{slug}_dementia"), item.dementia_capacity)
                item.save()
            messages.success(request, "이용 현황 수치를 저장했습니다.")
        elif action == "wait_add":
            name = (request.POST.get("name") or "").strip()
            service_type = (request.POST.get("service_type") or "").strip()
            if not name:
                messages.error(request, "대기자 성명을 입력해 주세요.")
            else:
                WaitlistEntry.objects.create(
                    name=name,
                    service_type=service_type or WAITLIST_TYPES[0],
                    queue_no=_int(request.POST.get("queue_no"), 1),
                )
                messages.success(request, "대기자를 등록했습니다.")
        elif action == "wait_save":
            entry = get_object_or_404(WaitlistEntry, pk=request.POST.get("id"))
            name = (request.POST.get("name") or "").strip()
            if name:
                entry.name = name
                entry.service_type = (request.POST.get("service_type") or entry.service_type).strip()
                entry.queue_no = _int(request.POST.get("queue_no"), entry.queue_no)
                entry.save()
                messages.success(request, "대기자 정보를 저장했습니다.")
        elif action == "wait_delete":
            WaitlistEntry.objects.filter(pk=request.POST.get("id")).delete()
            messages.success(request, "대기자를 삭제했습니다.")
        return redirect("/staff/usage/")
    return render(request, "staff/usage.html", {
        "stats": UsageStat.objects.all(),
        "as_of": as_of.body,
        "waitlist": WaitlistEntry.objects.all(),
        "wait_types": WAITLIST_TYPES,
    })


@staff_required
def applications(request):
    kind = request.GET.get("kind") or ""
    items = Application.objects.all()
    if kind:
        items = items.filter(kind=kind)
    return render(request, "staff/applications.html", {"items": items, "kind": kind})


@staff_required
@require_POST
def application_action(request, app_id):
    item = get_object_or_404(Application, pk=app_id)
    status = request.POST.get("status")
    if status in dict(Application.STATUS_CHOICES):
        item.status = status
        item.save(update_fields=["status"])
        messages.success(request, "신청 상태를 변경했습니다.")
    return redirect(request.POST.get("next") or "/staff/applications/")


def _save_menu_rows(rows):
    count = 0
    for row in rows:
        day = row.get("date")
        if not day:
            continue
        item, _ = DailyMenu.objects.get_or_create(date=day)
        changed = False
        for field in ("breakfast", "lunch", "dinner", "snack"):
            if row.get(field):
                setattr(item, field, row[field])
                changed = True
        if changed:
            item.save()
            count += 1
    return count


@staff_required
def meals(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_day":
            raw = (request.POST.get("date") or "").strip()
            try:
                day = date.fromisoformat(raw)
            except ValueError:
                messages.error(request, "날짜를 확인해 주세요.")
                return redirect("/staff/meals/")
            DailyMenu.objects.update_or_create(
                date=day,
                defaults={
                    "breakfast": (request.POST.get("breakfast") or "").strip(),
                    "lunch": (request.POST.get("lunch") or "").strip(),
                    "dinner": (request.POST.get("dinner") or "").strip(),
                    "snack": (request.POST.get("snack") or "").strip(),
                },
            )
            messages.success(request, f"{day.month}월 {day.day}일 식단을 저장했습니다.")
        elif action == "delete":
            DailyMenu.objects.filter(pk=request.POST.get("id")).delete()
            messages.success(request, "식단을 삭제했습니다.")
        elif action == "paste":
            rows = parse_menu_table(request.POST.get("paste") or "")
            saved = _save_menu_rows(rows)
            if saved:
                messages.success(request, f"{saved}일치 식단을 반영했습니다.")
            else:
                messages.error(request, "표에서 날짜와 메뉴를 찾지 못했습니다. 엑셀에서 복사한 뒤 붙여 넣어 주세요.")
        elif action == "upload":
            upload = request.FILES.get("file")
            if not upload:
                messages.error(request, "엑셀 또는 CSV 파일을 선택해 주세요.")
            else:
                name = (upload.name or "").lower()
                try:
                    if name.endswith(".xlsx") or name.endswith(".xlsm"):
                        rows = rows_from_xlsx(upload)
                    else:
                        rows = rows_from_csv(upload)
                    saved = _save_menu_rows(rows)
                    if saved:
                        messages.success(request, f"{saved}일치 식단을 파일에서 가져왔습니다.")
                    else:
                        messages.error(request, "파일에서 식단을 읽지 못했습니다. 날짜와 아침/점심/저녁 행이 있는지 확인해 주세요.")
                except Exception:
                    messages.error(request, "파일을 읽지 못했습니다. CSV 또는 엑셀(.xlsx)로 올려 주세요.")
        return redirect("/staff/meals/")
    today = timezone.localdate()
    return render(request, "staff/meals.html", {
        "items": DailyMenu.objects.filter(date__gte=today - timedelta(days=7)).order_by("date"),
        "today": today.isoformat(),
    })


@staff_required
def insights(request):
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            keyword = (request.POST.get("keyword") or "").strip()
            if keyword:
                term, _ = SearchTerm.objects.get_or_create(keyword=keyword)
                term.is_recommended = True
                term.recommend_order = int(request.POST.get("recommend_order") or 0)
                term.save()
                messages.success(request, "추천 검색어를 등록했습니다.")
        elif action == "delete":
            SearchTerm.objects.filter(pk=request.POST.get("id")).delete()
            messages.success(request, "검색어를 삭제했습니다.")
        elif action == "toggle":
            term = get_object_or_404(SearchTerm, pk=request.POST.get("id"))
            term.is_recommended = not term.is_recommended
            term.save(update_fields=["is_recommended"])
        return redirect("/staff/insights/")

    today = timezone.localdate()
    daily = list(
        VisitLog.objects.filter(visited_at__date__gte=today - timedelta(days=13))
        .annotate(day=TruncDate("visited_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    monthly = list(
        VisitLog.objects.annotate(month=TruncMonth("visited_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("-month")[:6]
    )
    signups = list(
        User.objects.filter(date_joined__date__gte=today - timedelta(days=30))
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    referers = list(
        VisitLog.objects.exclude(referer="")
        .values("referer")
        .annotate(count=Count("id"))
        .order_by("-count")[:8]
    )
    return render(request, "staff/insights.html", {
        "terms": SearchTerm.objects.all(),
        "daily": daily,
        "monthly": monthly,
        "signups": signups,
        "referers": referers,
        "signup_total": User.objects.count(),
        "visit_total": VisitLog.objects.count(),
    })


@csrf_exempt
@require_POST
def apply_api(request):
    data = _json_body(request)
    kind = data.get("kind")
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if kind not in dict(Application.KIND_CHOICES):
        return JsonResponse({"ok": False, "message": "올바른 신청 구분이 아닙니다."}, status=400)
    if not name or not phone:
        return JsonResponse({"ok": False, "message": "이름과 연락처를 입력해 주세요."}, status=400)
    extra = {key: data.get(key) for key in ("type", "time", "date", "day", "item") if data.get(key)}
    Application.objects.create(
        kind=kind,
        name=name,
        phone=phone,
        title=(data.get("title") or "")[:200],
        body=data.get("body") or data.get("memo") or "",
        extra=extra,
    )
    return JsonResponse({"ok": True, "message": "접수되었습니다. 담당자가 확인 후 연락드리겠습니다."})


@csrf_exempt
@require_POST
def search_log_api(request):
    data = _json_body(request)
    keyword = (data.get("q") or "").strip()
    if keyword:
        term, _ = SearchTerm.objects.get_or_create(keyword=keyword)
        term.search_count += 1
        term.save(update_fields=["search_count"])
    return JsonResponse({"ok": True})


@require_GET
def waitlist_api(request):
    name = (request.GET.get("name") or "").strip()
    if not name:
        return JsonResponse({"ok": True, "items": []})
    items = [
        {"name": row.name, "type": row.service_type, "no": row.queue_no}
        for row in WaitlistEntry.objects.filter(name=name)
    ]
    return JsonResponse({"ok": True, "items": items})


@require_GET
def search_keywords_api(request):
    recommended = list(
        SearchTerm.objects.filter(is_recommended=True).order_by("recommend_order", "keyword").values_list("keyword", flat=True)[:12]
    )
    popular = list(SearchTerm.objects.order_by("-search_count", "keyword").values_list("keyword", flat=True)[:10])
    return JsonResponse({"ok": True, "recommended": recommended, "popular": popular})
