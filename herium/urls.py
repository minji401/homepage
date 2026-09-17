from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.utils.cache import patch_cache_control
from django.views.static import serve as static_serve


def serve(request, path, document_root=None, show_indexes=False):
    response = static_serve(request, path, document_root=document_root, show_indexes=show_indexes)
    patch_cache_control(response, no_cache=True, must_revalidate=True, max_age=0)
    return response

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("cms.urls")),
    path("", include("pages.urls")),
    path("main.css", serve, {"document_root": settings.BASE_DIR, "path": "main.css"}),
    path("sub.css", serve, {"document_root": settings.BASE_DIR, "path": "sub.css"}),
    path("auth.js", serve, {"document_root": settings.BASE_DIR, "path": "auth.js"}),
    path("search.js", serve, {"document_root": settings.BASE_DIR, "path": "search.js"}),
    path("page.js", serve, {"document_root": settings.BASE_DIR, "path": "page.js"}),
    path("main.js", serve, {"document_root": settings.BASE_DIR, "path": "main.js"}),
    path("staff.css", serve, {"document_root": settings.BASE_DIR, "path": "staff.css"}),
    path("staff.js", serve, {"document_root": settings.BASE_DIR, "path": "staff.js"}),
    re_path(r"^img/(?P<path>.*)$", serve, {"document_root": settings.BASE_DIR / "img"}),
    re_path(r"^uploads/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
