from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_api, name="login_api"),
    path("signup/", views.signup_api, name="signup_api"),
    path("logout/", views.logout_api, name="logout_api"),
    path("me/", views.me_api, name="me_api"),
    path("find/", views.find_api, name="find_api"),
    path("guardian/", views.guardian_api, name="guardian_api"),
    path("profile/", views.profile_api, name="profile_api"),
]
