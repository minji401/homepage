from pathlib import Path

from django.conf import settings

from .models import Banner, Popup, Post, SearchTerm, SiteContent


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
        contents = {item.key: item.body for item in SiteContent.objects.all()}
        gallery = list(Post.objects.filter(board__slug="gallery", is_hidden=False).order_by("-created_at"))
        grouped = {"night": [], "nursing": [], "home": []}
        for item in gallery:
            key = item.category if item.category in grouped else "nursing"
            grouped[key].append(item)
        return {
            "cms": contents,
            "cms_popup": Popup.objects.filter(is_active=True).exclude(image="").first(),
            "cms_banners": Banner.objects.filter(is_active=True),
            "cms_notices": Post.objects.filter(board__slug="notice", is_hidden=False).order_by("-is_pinned", "-created_at")[:4],
            "cms_keywords": SearchTerm.objects.filter(is_recommended=True).order_by("recommend_order", "keyword"),
            "cms_notice_posts": Post.objects.filter(board__slug="notice", is_hidden=False),
            "cms_faq_posts": Post.objects.filter(board__slug="faq", is_hidden=False),
            "cms_menu_posts": Post.objects.filter(board__slug="menu", is_hidden=False).order_by("-is_pinned", "-created_at"),
            "cms_gallery": grouped,
            "cms_has_gallery": bool(gallery),
            "img_v": _img_version(),
        }
    except Exception:
        return {"cms": {}, "cms_has_gallery": False, "cms_gallery": {"night": [], "nursing": [], "home": []}, "cms_menu_posts": [], "img_v": "1"}
