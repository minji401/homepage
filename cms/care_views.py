from __future__ import annotations

from datetime import datetime, timedelta

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
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
from .models import ensure_site_info
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


@csrf_exempt
@require_POST
def consult_create(request):
    if not shared_enabled():
        return JsonResponse({"ok": False, "message": "공유 DB가 연결되지 않았습니다."}, status=503)
    data = _json_body(request)
    name = (data.get("applicant_name") or data.get("name") or "").strip()
    phone = normalize_phone(data.get("applicant_phone") or data.get("phone") or "")
    relation = (data.get("relation_type") or "").strip()
    care_level = data.get("care_level") or ""
    mobility = data.get("mobility_status") or ""
    slot = data.get("preferred_time_slot") or "시간무관"
    date = (data.get("preferred_date") or "").strip() or None
    privacy = data.get("privacy_agreed") in (True, "true", "on", "1", 1)
    if not name or len(phone) < 10:
        return JsonResponse({"ok": False, "message": "신청자명과 연락처를 입력해 주세요."}, status=400)
    if not relation:
        return JsonResponse({"ok": False, "message": "어르신과의 관계를 선택해 주세요."}, status=400)
    if care_level not in CARE_LEVELS:
        return JsonResponse({"ok": False, "message": "장기요양등급을 선택해 주세요."}, status=400)
    if mobility not in MOBILITY:
        return JsonResponse({"ok": False, "message": "보행상태를 선택해 주세요."}, status=400)
    if slot not in SLOTS:
        return JsonResponse({"ok": False, "message": "희망 시간대를 선택해 주세요."}, status=400)
    if not privacy:
        return JsonResponse({"ok": False, "message": "개인정보 수집 및 이용에 동의해 주세요."}, status=400)
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
        }
    )
    return JsonResponse(
        {
            "ok": True,
            "id": item["id"],
            "message": "신청이 정상 접수되었습니다. 담당자 확인 후 일정 확정 안내 문자를 발송해 드립니다.",
        }
    )


@staff_required
def calendar_page(request):
    return render(request, "staff/calendar.html", {"sms_ready": sms_configured()})


@staff_required
@require_GET
def calendar_api(request):
    pending = list_consultations("PENDING")
    events = []
    for row in list_schedules():
        events.append(
            {
                "id": row["id"],
                "title": row["title"],
                "start": row["start_datetime"],
                "end": row["end_datetime"],
                "extendedProps": {
                    "category": row["category"],
                    "consultation_id": row.get("consultation_id") or "",
                    "memo": row.get("memo") or "",
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
