from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import (
    USAGE_AS_OF_KEY,
    Banner,
    DailyMenu,
    Popup,
    Post,
    SearchTerm,
    SiteContent,
    ensure_site_info,
    ensure_usage_stats,
)


def _img_version():
    folder = Path(settings.BASE_DIR) / "img"
    newest = 0
    if folder.exists():
        for item in folder.iterdir():
            if item.is_file():
                newest = max(newest, int(item.stat().st_mtime))
    return str(newest)


def public_cms(request):
    try:
        usage = ensure_usage_stats()
        info = ensure_site_info()
        contents = {item.key: item.body for item in SiteContent.objects.all()}
        gallery = list(Post.objects.filter(board__slug="gallery", is_hidden=False).order_by("-created_at"))
        grouped = {"night": [], "nursing": [], "home": []}
        for item in gallery:
            key = item.category if item.category in grouped else "nursing"
            grouped[key].append(item)
        day_total = 0
        if usage.get("day_general"):
            day_total += usage["day_general"].capacity
        if usage.get("day_dementia"):
            day_total += usage["day_dementia"].capacity
        today = timezone.localdate()
        diet = list(
            DailyMenu.objects.filter(date__gte=today - timedelta(days=3), date__lte=today + timedelta(days=14))
        )
        if not diet:
            diet = list(reversed(list(DailyMenu.objects.order_by("-date")[:10])))
        return {
            "cms": contents,
            "info": info,
            "cms_popup": Popup.objects.filter(is_active=True).exclude(image="").first(),
            "cms_banners": Banner.objects.filter(is_active=True),
            "cms_notices": Post.objects.filter(board__slug="notice", is_hidden=False).order_by("-is_pinned", "-created_at")[:4],
            "cms_keywords": SearchTerm.objects.filter(is_recommended=True).order_by("recommend_order", "keyword"),
            "cms_notice_posts": Post.objects.filter(board__slug="notice", is_hidden=False),
            "cms_faq_posts": Post.objects.filter(board__slug="faq", is_hidden=False),
            "cms_menu_posts": Post.objects.filter(board__slug="menu", is_hidden=False).order_by("-is_pinned", "-created_at"),
            "cms_gallery": grouped,
            "cms_has_gallery": bool(gallery),
            "usage": usage,
            "usage_day_total": day_total,
            "usage_as_of": contents.get(USAGE_AS_OF_KEY) or "2026년 9월 15일",
            "diet_days": [item.as_banner() for item in diet],
            "img_v": _img_version(),
        }
    except Exception:
        return {"cms": {}, "info": {}, "cms_has_gallery": False, "cms_gallery": {"night": [], "nursing": [], "home": []}, "cms_menu_posts": [], "usage": {}, "usage_day_total": 0, "usage_as_of": "", "diet_days": [], "img_v": "1"}
