from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SitePageView(TemplateView):
    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, max_age=0)
        return response


def robots_txt(_request):
    from django.conf import settings

    admin_path = (getattr(settings, "ADMIN_URL_PATH", None) or "herium-control-99").strip("/")
    extra_admin = ""
    if admin_path and admin_path != "herium-control-99":
        extra_admin = f"Disallow: /{admin_path}/\n"
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /herium-control-99/\n"
        f"{extra_admin}"
        "Disallow: /accounts/\n"
        "Disallow: /mypage/\n"
        "Disallow: /api/\n"
        "\n"
        "Sitemap: https://heriumcare.com/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")
