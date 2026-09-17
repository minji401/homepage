from django.urls import path
from django.views.generic import RedirectView

from accounts.views import find_page, login_page, signup_page
from .views import SitePageView

PAGE_TEMPLATES = [
    ("main.html", "main.html"),
    ("search.html", "search.html"),
    ("sitemap.html", "sitemap.html"),
    ("about/about.html", "about/about.html"),
    ("about/facility.html", "about/facility.html"),
    ("about/location.html", "about/location.html"),
    ("about/organization.html", "about/organization.html"),
    ("about/disclosure.html", "about/disclosure.html"),
    ("about/system.html", "about/system.html"),
    ("about/partners.html", "about/partners.html"),
    ("service/nighttime.html", "service/nighttime.html"),
    ("service/nursing.html", "service/nursing.html"),
    ("service/home_visit.html", "service/home_visit.html"),
    ("service/home_bath.html", "service/home_bath.html"),
    ("service/dementia.html", "service/dementia.html"),
    ("service/monthly.html", "service/monthly.html"),
    ("admission/procedure.html", "admission/procedure.html"),
    ("admission/fees.html", "admission/fees.html"),
    ("admission/status.html", "admission/status.html"),
    ("admission/waitlist.html", "admission/waitlist.html"),
    ("admission/period.html", "admission/period.html"),
    ("admission/tour.html", "admission/tour.html"),
    ("admission/requirements.html", "admission/requirements.html"),
    ("volunteer/intro.html", "volunteer/intro.html"),
    ("volunteer/application.html", "volunteer/application.html"),
    ("community/notice.html", "community/notice.html"),
    ("community/gallery.html", "community/gallery.html"),
    ("community/menu.html", "community/menu.html"),
    ("community/faq.html", "community/faq.html"),
    ("community/inquiry.html", "community/inquiry.html"),
]

urlpatterns = [
    path("", RedirectView.as_view(url="/main.html", permanent=False)),
    path("login.html", login_page, name="login_page"),
    path("signup.html", signup_page, name="signup_page"),
    path("find-account.html", find_page, name="find_page"),
]

urlpatterns += [
    path(route, SitePageView.as_view(template_name=template), name=route.replace("/", "_").replace(".html", ""))
    for route, template in PAGE_TEMPLATES
]
