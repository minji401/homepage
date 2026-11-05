import logging

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import m2m_changed, post_save

logger = logging.getLogger("herium.security")


def client_ip(request):
    if request is None:
        return "-"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "-"
    return request.META.get("REMOTE_ADDR") or "-"


def log_event(event, request=None, **extra):
    parts = [f"{key}={value}" for key, value in extra.items() if value not in (None, "")]
    logger.warning("%s ip=%s %s", event, client_ip(request), " ".join(parts))


def _on_login_failed(sender, credentials, request, **kwargs):
    login_id = ""
    if isinstance(credentials, dict):
        login_id = credentials.get("username") or credentials.get("id") or ""
    log_event("login_failed", request, user=str(login_id)[:80])


def _on_login_ok(sender, request, user, **kwargs):
    log_event("login_ok", request, user=getattr(user, "username", ""))


def _on_admin_log(sender, instance, created, **kwargs):
    if not isinstance(instance, LogEntry):
        return
    log_event(
        "admin_log",
        user=getattr(instance.user, "username", ""),
        action=instance.get_action_flag_display(),
        object=str(instance.object_repr)[:80],
    )


def _on_user_saved(sender, instance, created, **kwargs):
    if created:
        return
    if instance.is_staff or instance.is_superuser:
        log_event(
            "user_privilege",
            user=instance.username,
            staff=instance.is_staff,
            superuser=instance.is_superuser,
        )


def _on_groups_changed(sender, instance, action, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    log_event("user_groups", user=getattr(instance, "username", ""), action=action)


def connect():
    user_login_failed.connect(_on_login_failed, dispatch_uid="herium_login_failed")
    user_logged_in.connect(_on_login_ok, dispatch_uid="herium_login_ok")
    post_save.connect(_on_admin_log, sender=LogEntry, dispatch_uid="herium_admin_log")
    post_save.connect(_on_user_saved, sender=User, dispatch_uid="herium_user_priv")
    m2m_changed.connect(_on_groups_changed, sender=User.groups.through, dispatch_uid="herium_user_groups")
