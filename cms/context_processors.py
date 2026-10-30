import logging
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

logger = logging.getLogger("herium")


def _img_version():
    newest = 0
    try:
        folders = [Path(settings.BASE_DIR) / "img", Path(settings.MEDIA_ROOT) / "brand"]
        for folder in folders:
            if not folder.exists():
                continue
            for item in folder.iterdir():
                if item.is_file():
                    newest = max(newest, int(item.stat().st_mtime))
    except OSError:
        pass
    return str(newest or 1)


def _active_popup():
    try:
        popup = (
            Popup.objects.filter(is_active=True)
            .exclude(image="")
            .order_by("-updated_at", "-id")
            .first()
        )
        if popup is None:
            popup = Popup.objects.filter(is_active=True).order_by("-updated_at", "-id").first()
        if popup and popup.image and not popup.image.startswith(("http://", "https://", "/")):
            popup.image = "/" + popup.image
        return popup
    except Exception:
        logger.exception("cms popup load failed")
        return None


def public_cms(request):
    context = {
        "cms": {},
        "info": {},
        "site_logo": "/img/logo.png",
        "site_logo_footer": "/img/logo2.png",
        "hero_photo": "",
        "cms_popup": None,
        "cms_banners": [],
        "cms_notices": [],
        "cms_keywords": [],
        "cms_notice_posts": [],
        "cms_faq_posts": [],
        "cms_menu_posts": [],
        "cms_has_gallery": False,
        "cms_gallery": {"night": [], "nursing": [], "home": []},
        "cms_gallery_slides": [],
        "usage": {},
        "usage_day_total": 0,
        "usage_as_of": "",
        "diet_days": [],
        "img_v": "1",
    }
    context["cms_popup"] = _active_popup()
    try:
        usage = ensure_usage_stats()
        info = ensure_site_info()
        contents = {item.key: item.body for item in SiteContent.objects.all()}
        gallery = list(Post.objects.filter(board__slug="gallery", is_hidden=False).order_by("-created_at"))
        grouped = {"night": [], "nursing": [], "home": []}
        for item in gallery:
            key = item.category if item.category in grouped else "nursing"
            grouped[key].append(item)
        gallery_slides = [item for item in gallery if (item.image or "").strip()]
        hero_photo = (contents.get("hero_photo") or "").strip()
        hero_path = hero_photo.split("?")[0]
        banners = []
        for banner in Banner.objects.filter(is_active=True).order_by("sort_order", "id"):
            image = (banner.image or "").split("?")[0]
            if hero_path and image and image == hero_path:
                continue
            if image:
                banners.append(banner)
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
        context.update(
            {
                "cms": contents,
                "info": info,
                "site_logo": contents.get("logo") or "/img/logo.png",
                "site_logo_footer": contents.get("logo_footer") or "/img/logo2.png",
                "hero_photo": hero_photo,
                "cms_banners": banners,
                "cms_notices": Post.objects.filter(board__slug="notice", is_hidden=False).order_by(
                    "-is_pinned", "-created_at"
                )[:4],
                "cms_keywords": SearchTerm.objects.filter(is_recommended=True).order_by("recommend_order", "keyword"),
                "cms_notice_posts": Post.objects.filter(board__slug="notice", is_hidden=False),
                "cms_faq_posts": Post.objects.filter(board__slug="faq", is_hidden=False),
                "cms_menu_posts": Post.objects.filter(board__slug="menu", is_hidden=False).order_by(
                    "-is_pinned", "-created_at"
                ),
                "cms_gallery": grouped,
                "cms_gallery_slides": gallery_slides,
                "cms_has_gallery": bool(gallery),
                "usage": usage,
                "usage_day_total": day_total,
                "usage_as_of": contents.get(USAGE_AS_OF_KEY) or "2026년 9월 15일",
                "diet_days": [item.as_banner() for item in diet],
                "img_v": _img_version(),
            }
        )
        context["cms_popup"] = _active_popup()
    except Exception:
        logger.exception("public_cms failed")
        context["cms_popup"] = context.get("cms_popup") or _active_popup()
        context["img_v"] = _img_version()
    return context
