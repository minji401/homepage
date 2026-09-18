from django.urls import path

from . import views

urlpatterns = [
    path("staff/", views.dashboard, name="staff_dashboard"),
    path("staff/members/", views.members, name="staff_members"),
    path("staff/members/<int:user_id>/", views.member_detail, name="staff_member_detail"),
    path("staff/posts/<int:post_id>/edit/", views.post_edit, name="staff_post_edit"),
    path("staff/posts/<int:post_id>/", views.post_action, name="staff_post_action"),
    path("staff/posts/<slug:slug>/bulk/", views.posts_bulk, name="staff_posts_bulk"),
    path("staff/posts/<slug:slug>/new/", views.post_edit, name="staff_post_new"),
    path("staff/posts/<slug:slug>/", views.posts_list, name="staff_posts"),
    path("staff/boards/", views.boards, name="staff_boards"),
    path("staff/comments/<int:comment_id>/", views.comment_action, name="staff_comment_action"),
    path("staff/content/", views.content, name="staff_content"),
    path("staff/usage/", views.usage, name="staff_usage"),
    path("staff/applications/", views.applications, name="staff_applications"),
    path("staff/applications/<int:app_id>/", views.application_action, name="staff_application_action"),
    path("staff/insights/", views.insights, name="staff_insights"),
    path("api/apply/", views.apply_api, name="apply_api"),
    path("api/search/log/", views.search_log_api, name="search_log_api"),
    path("api/search/keywords/", views.search_keywords_api, name="search_keywords_api"),
    path("api/waitlist/", views.waitlist_api, name="waitlist_api"),
]
