from django.http import HttpResponse
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

PUBLIC_SITEMAP_PATHS = [
    "main.html",
    "sitemap.html",
    "search.html",
    "login.html",
    "signup.html",
    "find-account.html",
    "about/about.html",
    "about/facility.html",
    "about/location.html",
    "about/organization.html",
    "about/disclosure.html",
    "about/system.html",
    "about/partners.html",
    "service/nighttime.html",
    "service/nursing.html",
    "service/home_visit.html",
    "service/home_bath.html",
    "service/dementia.html",
    "service/monthly.html",
    "service/medical.html",
    "admission/procedure.html",
    "admission/fees.html",
    "admission/status.html",
    "admission/waitlist.html",
    "admission/period.html",
    "admission/tour.html",
    "admission/requirements.html",
    "volunteer/intro.html",
    "volunteer/application.html",
    "community/notice.html",
    "community/gallery.html",
    "community/menu.html",
    "community/faq.html",
    "community/inquiry.html",
]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SitePageView(TemplateView):
    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_cache_control(response, no_cache=True, no_store=True, must_revalidate=True, max_age=0)
        return response


def sitemap_xml(request):
    scheme = "https" if request.is_secure() else request.scheme
    host = request.get_host()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path in PUBLIC_SITEMAP_PATHS:
        lines.append(f"  <url><loc>{scheme}://{host}/{path}</loc></url>")
    lines.append("</urlset>")
    return HttpResponse("\n".join(lines) + "\n", content_type="application/xml")


def robots_txt(request):
    scheme = "https" if request.is_secure() else request.scheme
    host = request.get_host()
    body = (
        "User-agent: Yeti\n"
        "Allow: /\n"
        "\n"
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /staff/\n"
        "Disallow: /admin/\n"
        "Disallow: /account.html\n"
        "Disallow: /guardian.html\n"
        "Disallow: /accounts/\n"
        f"Sitemap: {scheme}://{host}/sitemap.xml\n"
    )
    return HttpResponse(body, content_type="text/plain")
