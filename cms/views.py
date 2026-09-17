from datetime import timedelta
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
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import Profile
from .models import Application, Banner, Board, Comment, Popup, Post, SearchTerm, SiteContent, VisitLog

CONTENT_BOARDS = {
    "notice": {"name": "공지사항", "has_image": False, "has_category": False},
    "menu": {"name": "식단표", "has_image": True, "has_category": False},
    "gallery": {"name": "갤러리", "has_image": True, "has_category": True},
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
    allowed = {"date_joined": "date_joined", "-date_joined": "-date_joined", "username": "username"}
    users = User.objects.select_related("profile").order_by(allowed.get(sort, "-date_joined"))
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(profile__name__icontains=q)
            | Q(email__icontains=q)
            | Q(profile__phone__icontains=q)
        )
    return render(request, "staff/members.html", {"users": users, "q": q, "sort": sort})


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
        return redirect("/staff/content/")
    return render(request, "staff/content.html", {
        "contents": SiteContent.objects.all(),
        "popup": Popup.objects.first(),
        "banners": Banner.objects.all(),
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
def search_keywords_api(request):
    recommended = list(
        SearchTerm.objects.filter(is_recommended=True).order_by("recommend_order", "keyword").values_list("keyword", flat=True)[:12]
    )
    popular = list(SearchTerm.objects.order_by("-search_count", "keyword").values_list("keyword", flat=True)[:10])
    return JsonResponse({"ok": True, "recommended": recommended, "popular": popular})
