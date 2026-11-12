from __future__ import annotations

from datetime import datetime, timedelta
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.jwt_auth import bearer_user_id
from accounts.shared_users import get_shared_by_id, normalize_phone, shared_enabled
from .care_store import (
    CARE_LEVELS,
    CATEGORIES,
    MOBILITY,
    SLOTS,
    confirm_on_calendar,
    create_consultation,
    delete_schedule,
    get_consultation,
    get_schedule,
    list_consultations,
    list_schedules,
    update_consultation,
    upsert_schedule,
)
from .forms import ConsultCreateForm, first_form_error
from .models import Application, ensure_site_info
from .pii import encrypt_text
from .sms import send_sms, sms_configured
from .views import _json_body, staff_required


def _user_id(request):
    if request.user.is_authenticated:
        shared = getattr(request.user, "profile", None)
        if shared:
            found = None
            from accounts.shared_users import get_shared_by_phone, get_shared_by_username

            found = get_shared_by_username(request.user.username) or get_shared_by_phone(shared.phone)
            if found:
                return found.id
    return bearer_user_id(request)


@require_POST
def consult_create(request):
    if not shared_enabled():
        return JsonResponse({"ok": False, "message": "공유 DB가 연결되지 않았습니다."}, status=503)
    data = _json_body(request)
    form = ConsultCreateForm(data)
    if not form.is_valid():
        return JsonResponse({"ok": False, "message": first_form_error(form)}, status=400)
    cleaned = form.cleaned_data
    name = cleaned["applicant_name"]
    phone = cleaned["applicant_phone"]
    relation = (cleaned.get("relation_type") or "").strip()
    care_level = cleaned.get("care_level") or ""
    mobility = cleaned.get("mobility_status") or ""
    slot = cleaned.get("preferred_time_slot") or "시간무관"
    date = (cleaned.get("preferred_date") or "").strip() or None
    senior_name = cleaned.get("senior_name") or ""
    patient_id = cleaned.get("patient_id") or ""
    if patient_id and request.user.is_authenticated:
        from accounts.models import SeniorProfile

        senior = SeniorProfile.objects.filter(pk=patient_id, guardian=request.user).first()
        if senior:
            senior_name = senior_name or senior.name
            if care_level not in CARE_LEVELS and senior.care_grade:
                mapped = {
                    "1등급": "1_2등급",
                    "2등급": "1_2등급",
                    "3등급": "3_5등급",
                    "4등급": "3_5등급",
                    "5등급": "3_5등급",
                    "등급외/신청중": "신청중_미인정",
                }.get(senior.care_grade)
                if mapped:
                    care_level = mapped
    consult_kind = cleaned.get("consult_kind") or "입소 상담"
    item = create_consultation(
        {
            "user_id": _user_id(request),
            "applicant_name": name,
            "applicant_phone": phone,
            "relation_type": relation,
            "care_level": care_level,
            "mobility_status": mobility,
            "preferred_date": date,
            "preferred_time_slot": slot,
            "privacy_agreed": True,
            "patient_id": patient_id,
            "senior_name": senior_name,
            "consult_kind": consult_kind,
            "status": "RECEIVED",
        }
    )
    extra = {
        "consultation_id": item["id"],
        "relationship": relation,
        "relation_type": relation,
        "preferred_date": date or "",
        "preferred_time_slot": slot,
        "consult_kind": consult_kind,
        "care_level": care_level,
        "mobility_status": mobility,
    }
    Application.objects.create(
        kind=Application.kind_from_label(consult_kind),
        status=Application.STATUS_RECEIVED,
        user=request.user if request.user.is_authenticated else None,
        patient_id=str(patient_id or ""),
        senior_name=senior_name,
        name=encrypt_text(name),
        phone=encrypt_text(phone),
        title=consult_kind,
        body=encrypt_text(cleaned.get("memo") or ""),
        extra=extra,
    )
    return JsonResponse(
        {
            "ok": True,
            "id": item["id"],
            "applicant_name": name,
            "senior_name": senior_name,
            "preferred_date": date or "",
            "preferred_time_slot": slot,
            "redirect": "/mypage.html",
            "message": "신청이 정상 접수되었습니다. 담당자 확인 후 일정 확정 안내 문자를 발송해 드립니다.",
        }
    )


@staff_required
def calendar_page(request):
    return render(request, "staff/calendar.html", {"sms_ready": sms_configured()})


_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
_ISO_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}T")
_CANCELLED_KEYS = {"cancelled", "취소됨", "취소", "CANCELLED"}
_DONE_KEYS = {"done", "상담완료", "상담 완료", "확정", "CONFIRMED", "COMPLETED", "completed", "confirmed"}
_PENDING_KEYS = {
    "received",
    "RECEIVED",
    "접수완료",
    "waiting",
    "PENDING",
    "pending",
    "상담대기",
    "대기중",
    "대기",
}


def _iso_date(*values):
    for value in values:
        found = _DATE_RE.search(str(value or ""))
        if found:
            return found.group(1)
    return ""


def _time_label(*values):
    date = _iso_date(*values)
    text = " ".join(str(value).strip() for value in values if value)
    if date:
        text = text.replace(date, " ")
    return re.sub(r"\s+", " ", text).strip(" /-")


def _status_key(value):
    return Application.normalize_status(value)


def _is_cancelled_status(value):
    return _status_key(value) == "cancelled" or (value or "").strip() in _CANCELLED_KEYS


def _is_pending_status(value):
    raw = (value or "").strip()
    return _status_key(value) in Application.CANCELLABLE_STATUSES or raw in _PENDING_KEYS


def _event_start(*values):
    for value in values:
        text = str(value or "").strip()
        if _ISO_RE.match(text):
            return text
    return _iso_date(*values) or None


def _consult_event_start(row):
    return _event_start(row.get("preferred_date"), row.get("created_at"))


def _pending_from_care(row):
    date = _iso_date(row.get("preferred_date"), row.get("created_at"))
    slot = (row.get("preferred_time_slot") or "").strip() or _time_label(row.get("preferred_date"))
    return {
        "id": row.get("id"),
        "applicant_name": row.get("applicant_name") or "",
        "senior_name": row.get("senior_name") or "",
        "relation_type": row.get("relation_type") or "",
        "care_level": row.get("care_level") or "",
        "mobility_status": row.get("mobility_status") or "",
        "preferred_date": date,
        "preferred_time_slot": slot,
        "preferred_label": " ".join(part for part in (date, slot) if part) or "날짜 미정",
        "status": row.get("status") or "",
    }


def _pending_from_application(item):
    extra = item.extra_data
    date = _iso_date(item.preferred_date_value, extra.get("preferred_date"), extra.get("date"), item.created_at.date().isoformat())
    slot = (extra.get("preferred_time_slot") or extra.get("time") or "").strip() or _time_label(item.preferred_display)
    return {
        "id": extra.get("consultation_id") or f"app-{item.id}",
        "application_id": item.id,
        "applicant_name": item.name_plain,
        "senior_name": item.senior_name or "",
        "relation_type": item.relationship,
        "care_level": extra.get("care_level") or "",
        "mobility_status": extra.get("mobility_status") or "",
        "preferred_date": date,
        "preferred_time_slot": slot,
        "preferred_label": " ".join(part for part in (date, slot) if part) or "날짜 미정",
        "status": item.status,
    }


@staff_required
@require_GET
def calendar_api(request):
    pending = []
    seen_pending = set()
    cancelled_ids = set()
    for row in list_consultations():
        cid = str(row.get("id") or "")
        if _is_cancelled_status(row.get("status")):
            if cid:
                cancelled_ids.add(cid)
            continue
        if cid and _is_pending_status(row.get("status")):
            payload = _pending_from_care(row)
            pending.append(payload)
            seen_pending.add(cid)
    for item in Application.objects.filter(kind__in=[Application.KIND_CONSULT, Application.KIND_TOUR]):
        if item.is_cancelled:
            linked = str(item.extra_data.get("consultation_id") or "")
            if linked:
                cancelled_ids.add(linked)
            continue
        if not item.is_cancellable:
            continue
        linked = str(item.extra_data.get("consultation_id") or "")
        if linked and linked in seen_pending:
            continue
        payload = _pending_from_application(item)
        pending.append(payload)
        seen_pending.add(str(payload.get("id") or f"app-{item.id}"))
    events = []
    scheduled_ids = set()
    for row in list_schedules():
        cid = str(row.get("consultation_id") or "")
        if cid and cid in cancelled_ids:
            continue
        start = _event_start(row.get("start_datetime"), row.get("end_datetime"))
        if not start:
            continue
        if cid:
            scheduled_ids.add(cid)
        events.append(
            {
                "id": row["id"],
                "title": row["title"],
                "start": start,
                "end": _event_start(row.get("end_datetime")) or start,
                "extendedProps": {
                    "category": row["category"],
                    "consultation_id": cid,
                    "memo": row.get("memo") or "",
                    "time_slot": _time_label(row.get("start_datetime")),
                },
            }
        )
    for row in list_consultations():
        cid = str(row.get("id") or "")
        if not cid or cid in scheduled_ids or _is_cancelled_status(row.get("status")):
            continue
        start = _consult_event_start(row)
        if not start:
            continue
        kind = row.get("consult_kind") or "상담"
        senior = row.get("senior_name") or ""
        title = f"{kind} · {row.get('applicant_name') or ''}"
        if senior:
            title += f" / {senior}"
        events.append(
            {
                "id": "consult-" + cid,
                "title": title.strip(" ·"),
                "start": start,
                "allDay": True,
                "backgroundColor": "#c4a574",
                "borderColor": "#b38b4d",
                "extendedProps": {
                    "category": "상담",
                    "consultation_id": cid,
                    "memo": (row.get("preferred_time_slot") or "") + " " + (row.get("relation_type") or ""),
                    "time_slot": row.get("preferred_time_slot") or "",
                },
            }
        )
        scheduled_ids.add(cid)
    for item in Application.objects.filter(kind__in=[Application.KIND_CONSULT, Application.KIND_TOUR]):
        if item.is_cancelled:
            continue
        extra = item.extra_data
        linked = str(extra.get("consultation_id") or "")
        if linked and linked in scheduled_ids:
            continue
        start = _event_start(item.preferred_date_value, extra.get("date"), item.created_at.date().isoformat())
        if not start:
            continue
        title = f"{item.get_kind_display()} · {item.name_plain}"
        if item.senior_name:
            title += f" / {item.senior_name}"
        events.append(
            {
                "id": f"app-{item.id}",
                "title": title,
                "start": start,
                "allDay": True,
                "backgroundColor": "#c4a574",
                "borderColor": "#b38b4d",
                "extendedProps": {
                    "category": "상담",
                    "consultation_id": linked,
                    "memo": item.preferred_display or item.relationship,
                    "time_slot": extra.get("preferred_time_slot") or extra.get("time") or "",
                },
            }
        )
    return JsonResponse({"ok": True, "pending": pending, "events": events})


@staff_required
@require_http_methods(["POST", "PATCH", "DELETE"])
def schedule_api(request, item_id=None):
    data = _json_body(request) if request.body else {}
    if request.method == "DELETE":
        delete_schedule(item_id)
        return JsonResponse({"ok": True})
    title = (data.get("title") or "").strip()
    start = data.get("start") or data.get("start_datetime")
    end = data.get("end") or data.get("end_datetime") or start
    category = data.get("category") or "기타"
    if category not in CATEGORIES:
        category = "기타"
    if not title or not start:
        return JsonResponse({"ok": False, "message": "제목과 시작 시각이 필요합니다."}, status=400)
    saved = upsert_schedule(
        {
            "consultation_id": data.get("consultation_id"),
            "title": title,
            "start_datetime": start,
            "end_datetime": end,
            "category": category,
            "memo": data.get("memo") or "",
        },
        item_id=item_id,
    )
    consult_id = data.get("consultation_id")
    if consult_id:
        update_consultation(consult_id, {"status": "CONFIRMED", "confirmed_datetime": start})
    return JsonResponse({"ok": True, "item": saved})


@staff_required
@require_POST
def confirm_consult(request, item_id):
    data = _json_body(request)
    start = data.get("start") or data.get("confirmed_datetime")
    if not start:
        return JsonResponse({"ok": False, "message": "확정 일시를 선택해 주세요."}, status=400)
    end = data.get("end") or (datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(hours=1)).isoformat()
    saved = confirm_on_calendar(item_id, start, end)
    if not saved:
        return JsonResponse({"ok": False, "message": "상담 건을 찾지 못했습니다."}, status=404)
    return JsonResponse({"ok": True, "item": saved})


@staff_required
@require_POST
def sms_send(request, item_id):
    item = get_consultation(item_id)
    if not item:
        return JsonResponse({"ok": False, "message": "상담 건을 찾지 못했습니다."}, status=404)
    data = _json_body(request)
    to_phone = normalize_phone(data.get("to") or item.get("applicant_phone"))
    text = (data.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "message": "문자 내용을 입력해 주세요."}, status=400)
    try:
        send_sms(to_phone, text)
        ok = 1
        message = "문자를 발송했습니다."
    except Exception as exc:
        ok = 0
        message = str(exc)
        if not sms_configured():
            return JsonResponse({"ok": False, "message": message}, status=503)
        return JsonResponse({"ok": False, "message": message}, status=502)
    from datetime import timezone

    update_consultation(
        item_id,
        {
            "sms_sent_at": datetime.now(timezone.utc).isoformat(),
            "sms_content": text,
            "sms_ok": ok,
        },
    )
    return JsonResponse({"ok": True, "message": message})


def default_sms_text(item):
    info = ensure_site_info()
    when = item.get("confirmed_datetime") or ""
    date_part = when[:10] if when else "미정"
    time_part = when[11:16] if len(when) >= 16 else ""
    address = info.get("address_full") or info.get("address") or "영천시 역전로 16"
    return (
        f"[헤리움] 안녕하세요 {item.get('applicant_name')} 님, 어르신 입소 상담이 "
        f"{date_part} {time_part}에 예약되었습니다. (오시는 길: {address})"
    )


@staff_required
@require_GET
def sms_preview(request, item_id):
    item = get_consultation(item_id)
    if not item:
        return JsonResponse({"ok": False, "message": "상담 건을 찾지 못했습니다."}, status=404)
    return JsonResponse(
        {
            "ok": True,
            "to": item.get("applicant_phone"),
            "text": default_sms_text(item),
            "configured": sms_configured(),
        }
    )
