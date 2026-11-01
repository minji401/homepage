from django.contrib.sitemaps import Sitemap

from cms.models import Post

PUBLIC_PATHS = [
    "/",
    "/main.html",
    "/about/about.html",
    "/community/inquiry.html",
    "/about/facility.html",
    "/about/location.html",
    "/about/organization.html",
    "/about/disclosure.html",
    "/about/system.html",
    "/about/partners.html",
    "/service/nighttime.html",
    "/service/nursing.html",
    "/service/home_visit.html",
    "/service/home_bath.html",
    "/service/dementia.html",
    "/service/monthly.html",
    "/service/medical.html",
    "/admission/procedure.html",
    "/admission/fees.html",
    "/admission/status.html",
    "/admission/waitlist.html",
    "/admission/period.html",
    "/admission/tour.html",
    "/admission/requirements.html",
    "/volunteer/intro.html",
    "/volunteer/application.html",
    "/community/notice.html",
    "/community/gallery.html",
    "/community/menu.html",
    "/community/faq.html",
    "/privacy.html",
    "/terms.html",
]


class PublicPageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
    protocol = "https"

    def items(self):
        return PUBLIC_PATHS

    def location(self, item):
        return item


class NoticeSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
    protocol = "https"

    def items(self):
        try:
            return list(
                Post.objects.filter(board__slug="notice", is_hidden=False).order_by("-created_at")[:50]
            )
        except Exception:
            return []

    def location(self, item):
        return f"/community/post/{item.id}/"

    def lastmod(self, item):
        return getattr(item, "created_at", None)


SITEMAPS = {
    "pages": PublicPageSitemap,
    "notices": NoticeSitemap,
}
