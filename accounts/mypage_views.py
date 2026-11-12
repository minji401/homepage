from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from cms.care_store import STATUS_LABELS, list_consultations_for_user
from cms.models import Application
from .models import Profile, SeniorProfile
from .password_policy import PASSWORD_RULE, password_error
from .shared_users import (
    SharedAuthError,
    get_shared_by_email,
    normalize_phone,
    resolve_shared_login,
    set_guardian_name,
    shared_enabled,
    update_shared_password,
    update_shared_phone,
)
from .views import _get_profile, _json_body, _profile_payload, _valid_email, format_phone_or_digits


SHOP_URL = "https://hyundaimedi.com"
RELATIONS = [item[0] for item in SeniorProfile.RELATION_CHOICES]
GRADES = [item[0] for item in SeniorProfile.GRADE_CHOICES]


def _shared_id(user):
    if not shared_enabled():
        return ""
    shared = resolve_shared_login(user.username, user)
    return shared.id if shared is not None else ""


def _parse_date(value):
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return False


def _senior_payload(item):
    return item.as_card()


def _consult_rows(user):
    profile = _get_profile(user)
    phone = normalize_phone(getattr(profile, "phone", "") or "")
    rows = []
    apps = list(Application.objects.filter(user=user).order_by("-created_at"))
    linked_ids = {(item.extra_data.get("consultation_id") or "") for item in apps}
    try:
        for item in list_consultations_for_user(_shared_id(user), phone):
            cid = item.get("id") or ""
            if cid and cid in linked_ids:
                continue
            status = item.get("status") or "RECEIVED"
            status_key = Application.normalize_status(status)
            cancelled = status_key == "cancelled"
            locked = status_key == "done"
            linked_app = None
            if cid:
                try:
                    linked_app = Application.objects.filter(extra__consultation_id=cid).first()
                except Exception:
                    linked_app = next((row for row in apps if row.extra_data.get("consultation_id") == cid), None)
            rows.append(
                {
                    "id": cid,
                    "application_id": linked_app.id if linked_app else "",
                    "source": "care",
                    "created_at": (item.get("created_at") or "")[:16].replace("T", " "),
                    "senior_name": item.get("senior_name") or "-",
                    "kind": item.get("consult_kind") or "입소 상담",
                    "status": status,
                    "status_label": STATUS_LABELS.get(status) or {
                        "received": "접수완료",
                        "waiting": "상담대기",
                        "done": "상담완료",
                        "cancelled": "취소됨",
                    }.get(status_key, status),
                    "detail": item.get("admin_memo") or item.get("sms_content") or "",
                    "preferred": " ".join(
                        part for part in (item.get("preferred_date") or "", item.get("preferred_time_slot") or "") if part
                    ),
                    "can_cancel": bool(linked_app and linked_app.is_cancellable),
                    "show_center_hint": locked and not cancelled,
                }
            )
    except Exception:
        pass
    for item in apps:
        status = item.status
        label = item.status_admin_label if item.is_cancelled else dict(Application.STATUS_CHOICES).get(status, item.status_admin_label)
        locked = (not item.is_cancellable) and (not item.is_cancelled) and item.kind in (
            Application.KIND_CONSULT,
            Application.KIND_TOUR,
        )
        rows.append(
            {
                "id": f"app-{item.id}",
                "application_id": item.id,
                "source": "application",
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M"),
                "senior_name": item.senior_name or "-",
                "kind": item.get_kind_display(),
                "status": status,
                "status_label": label,
                "detail": item.body_plain or item.title,
                "preferred": item.preferred_display,
                "can_cancel": item.is_cancellable,
                "show_center_hint": locked,
            }
        )
    rows.sort(key=lambda row: row["created_at"], reverse=True)
    return rows


@ensure_csrf_cookie
@login_required
def mypage_page(request):
    profile = _get_profile(request.user)
    seniors = SeniorProfile.objects.filter(guardian=request.user)
    return render(
        request,
        "mypage.html",
        {
            "profile": profile,
            "seniors": seniors,
            "consults": _consult_rows(request.user),
            "relations": SeniorProfile.RELATION_CHOICES,
            "grades": SeniorProfile.GRADE_CHOICES,
            "shop_url": SHOP_URL,
            "password_rule": PASSWORD_RULE,
        },
    )


@login_required
@require_POST
def mypage_profile_api(request):
    from django.contrib.auth import authenticate

    data = _json_body(request)
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip()
    current = data.get("currentPassword") or data.get("current_password") or ""
    new_password = data.get("newPassword") or data.get("new_password") or ""
    from .password_policy import name_error, phone_error

    name_msg = name_error(name)
    if name_msg:
        return JsonResponse({"ok": False, "message": "신청인(보호자) 성명을 한글 또는 영문 2자 이상으로 입력해 주세요."}, status=400)
    digits = normalize_phone(phone)
    if phone_error(digits):
        return JsonResponse({"ok": False, "message": "연락처는 010-0000-0000 형식으로 입력해 주세요."}, status=400)
    if email and not _valid_email(email):
        return JsonResponse({"ok": False, "message": "이메일 형식을 확인해 주세요."}, status=400)
    user = request.user
    shared = resolve_shared_login(user.username, user) if shared_enabled() else None
    if new_password:
        if password_error(new_password):
            return JsonResponse({"ok": False, "message": PASSWORD_RULE}, status=400)
        from .passwords import verify_password

        ok = False
        if shared is not None:
            ok = verify_password(current, shared.password_hash)
        if not ok:
            ok = authenticate(request, username=user.username, password=current) is not None
        if not ok:
            return JsonResponse({"ok": False, "message": "현재 비밀번호가 일치하지 않습니다."}, status=400)
    if email:
        taken = user.__class__.objects.filter(email__iexact=email).exclude(pk=user.pk).exists()
        if taken:
            return JsonResponse({"ok": False, "message": "이미 사용 중인 이메일입니다."}, status=400)
    if shared is not None:
        try:
            update_shared_phone(shared, digits)
            set_guardian_name(shared, name)
            if new_password:
                update_shared_password(shared, new_password)
            if email:
                other = get_shared_by_email(email)
                if other is not None and other.id != shared.id:
                    return JsonResponse({"ok": False, "message": "이미 사용 중인 이메일입니다."}, status=400)
                shared.email = email
                shared.save(update_fields=["email"], using="shared")
        except SharedAuthError as exc:
            return JsonResponse({"ok": False, "message": exc.message}, status=exc.status)
    if new_password:
        user.set_password(new_password)
    user.email = email
    user.first_name = name
    user.save()
    profile = _get_profile(user)
    Profile.objects.update_or_create(
        user=user,
        defaults={
            "name": name,
            "phone": format_phone_or_digits(digits),
            "role": profile.role if profile else Profile.ROLE_MEMBER,
            "status": profile.status if profile else Profile.STATUS_ACTIVE,
        },
    )
    return JsonResponse({"ok": True, "message": "계정 정보를 저장했습니다.", "user": _profile_payload(user)})


def _save_senior(user, data, instance=None):
    name = (data.get("name") or "").strip()
    relationship = (data.get("relationship") or "기타").strip()
    if len(name) < 2:
        return None, JsonResponse({"ok": False, "message": "어르신 성함을 입력해 주세요."}, status=400)
    if relationship not in RELATIONS:
        relationship = "기타"
    grade = (data.get("care_grade") or data.get("careGrade") or "").strip()
    if grade and grade not in GRADES:
        return None, JsonResponse({"ok": False, "message": "장기요양등급을 확인해 주세요."}, status=400)
    birth = _parse_date(data.get("birth_date") or data.get("birthDate"))
    if birth is False:
        return None, JsonResponse({"ok": False, "message": "생년월일 형식을 확인해 주세요."}, status=400)
    fields = {
        "name": name,
        "relationship": relationship,
        "birth_date": birth,
        "care_grade": grade,
        "note": (data.get("note") or "").strip(),
        "shared_user_id": _shared_id(user),
    }
    if instance is None:
        instance = SeniorProfile(guardian=user)
    for key, value in fields.items():
        setattr(instance, key, value)
    instance.save()
    return instance, None


@require_http_methods(["GET", "POST"])
def seniors_api(request):
    if not request.user.is_authenticated:
        if request.method == "GET":
            return JsonResponse({"ok": True, "items": []})
        return JsonResponse({"ok": False, "message": "로그인이 필요합니다."}, status=401)
    if request.method == "GET":
        items = [_senior_payload(item) for item in SeniorProfile.objects.filter(guardian=request.user)]
        return JsonResponse({"ok": True, "items": items})
    item, error = _save_senior(request.user, _json_body(request))
    if error:
        return error
    return JsonResponse({"ok": True, "item": _senior_payload(item)})


@login_required
@require_http_methods(["POST", "PATCH", "DELETE"])
def senior_detail_api(request, pk):
    item = get_object_or_404(SeniorProfile, pk=pk, guardian=request.user)
    if request.method == "DELETE":
        item.delete()
        return JsonResponse({"ok": True})
    saved, error = _save_senior(request.user, _json_body(request), item)
    if error:
        return error
    return JsonResponse({"ok": True, "item": _senior_payload(saved)})


@login_required
@require_GET
def my_consults_api(request):
    return JsonResponse({"ok": True, "items": _consult_rows(request.user)})


def account_redirect(request):
    if not request.user.is_authenticated:
        return redirect("/login.html")
    return redirect("/mypage/")
