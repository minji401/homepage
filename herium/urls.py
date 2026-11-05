from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.utils.cache import patch_cache_control
from django.views.static import serve as static_serve

from herium.axes_lockout import lockout_response
from pages.sitemaps import SITEMAPS
from pages.views import robots_txt


def serve(request, path, document_root=None, show_indexes=False):
    response = static_serve(request, path, document_root=document_root, show_indexes=show_indexes)
    patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
    return response

_admin_path = (getattr(settings, "ADMIN_URL_PATH", None) or "herium-control-99").strip("/")

urlpatterns = [
    path("healthz", lambda request: HttpResponse("ok", content_type="text/plain")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap_xml"),
    path(f"{_admin_path}/", admin.site.urls),
    path("locked/", lambda request: lockout_response(request, {}), name="axes_locked"),
    path("accounts/", include("accounts.urls")),
    path("", include("cms.urls")),
    path("", include("pages.urls")),
    path("main.css", serve, {"document_root": settings.BASE_DIR, "path": "main.css"}),
    path("sub.css", serve, {"document_root": settings.BASE_DIR, "path": "sub.css"}),
    path("auth.js", serve, {"document_root": settings.BASE_DIR, "path": "auth.js"}),
    path("mypage.js", serve, {"document_root": settings.BASE_DIR, "path": "mypage.js"}),
    path("search.js", serve, {"document_root": settings.BASE_DIR, "path": "search.js"}),
    path("page.js", serve, {"document_root": settings.BASE_DIR, "path": "page.js"}),
    path("main.js", serve, {"document_root": settings.BASE_DIR, "path": "main.js"}),
    path("staff.css", serve, {"document_root": settings.BASE_DIR, "path": "staff.css"}),
    path("staff.js", serve, {"document_root": settings.BASE_DIR, "path": "staff.js"}),
    re_path(r"^img/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "img"}),
    re_path(r"^uploads/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

handler404 = "herium.error_views.page_not_found"
handler500 = "herium.error_views.server_error"
