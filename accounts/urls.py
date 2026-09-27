from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_api, name="login_api"),
    path("signup/", views.signup_api, name="signup_api"),
    path("logout/", views.logout_api, name="logout_api"),
    path("me/", views.me_api, name="me_api"),
    path("find/", views.find_api, name="find_api"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-help/", views.password_help_request, name="password_help_request"),
    path("guardian/", views.guardian_api, name="guardian_api"),
    path("profile/", views.profile_api, name="profile_api"),
    path("public-config/", views.public_config, name="public_config"),
]
