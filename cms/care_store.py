from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from django.db import connections

from accounts.shared_schema import ensure_integration_schema
from accounts.shared_users import shared_enabled

CARE_LEVELS = ("1_2등급", "3_5등급", "신청중_미인정")
MOBILITY = ("자립보행", "부축필요", "와상")
SLOTS = ("오전(10-12)", "오후(14-16)", "오후(16-18)", "시간무관")
STATUSES = ("RECEIVED", "PENDING", "CONFIRMED", "CANCELLED")
STATUS_LABELS = {
    "RECEIVED": "접수완료",
    "PENDING": "상담대기",
    "CONFIRMED": "상담완료",
    "CANCELLED": "취소됨",
    "cancelled": "취소됨",
}
CATEGORIES = ("상담", "봉사", "시설행사", "기타")


def _db():
    if not shared_enabled():
        return None
    ensure_integration_schema()
    return connections["shared"]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _row(cursor):
    cols = [col[0] for col in cursor.description]
    data = cursor.fetchone()
    return dict(zip(cols, data)) if data else None


def _rows(cursor):
    cols = [col[0] for col in cursor.description]
    return [dict(zip(cols, item)) for item in cursor.fetchall()]


def create_consultation(data):
    db = _db()
    if db is None:
        raise RuntimeError("공유 DB가 없습니다.")
    item_id = "c_" + uuid4().hex
    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO care_consultations (
              id, user_id, applicant_name, applicant_phone, relation_type, care_level,
              mobility_status, preferred_date, preferred_time_slot, privacy_agreed,
              status, created_at, patient_id, senior_name, consult_kind
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            [
                item_id,
                data.get("user_id"),
                data["applicant_name"],
                data["applicant_phone"],
                data.get("relation_type") or data.get("relationship") or "",
                data.get("care_level") or "",
                data.get("mobility_status") or "",
                data.get("preferred_date"),
                data.get("preferred_time_slot"),
                1 if data.get("privacy_agreed") else 0,
                data.get("status") or "RECEIVED",
                _now(),
                str(data.get("patient_id") or "") or None,
                data.get("senior_name") or "",
                data.get("consult_kind") or "입소 상담",
            ],
        )
    return get_consultation(item_id)


def get_consultation(item_id):
    db = _db()
    if db is None:
        return None
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM care_consultations WHERE id = %s", [item_id])
        return _row(cursor)


def list_consultations(status=""):
    db = _db()
    if db is None:
        return []
    with db.cursor() as cursor:
        if status:
            cursor.execute(
                "SELECT * FROM care_consultations WHERE status = %s ORDER BY created_at DESC",
                [status],
            )
        else:
            cursor.execute("SELECT * FROM care_consultations ORDER BY created_at DESC")
        return _rows(cursor)


def list_consultations_for_user(user_id="", phone=""):
    db = _db()
    if db is None:
        return []
    clauses = []
    values = []
    if user_id:
        clauses.append("user_id = %s")
        values.append(user_id)
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits:
        clauses.append("applicant_phone = %s")
        values.append(digits)
    if not clauses:
        return []
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM care_consultations WHERE "
            + " OR ".join(clauses)
            + " ORDER BY created_at DESC",
            values,
        )
        return _rows(cursor)


def update_consultation(item_id, fields):
    allowed = {
        "confirmed_datetime",
        "status",
        "admin_memo",
        "sms_sent_at",
        "sms_content",
        "sms_ok",
        "preferred_date",
        "preferred_time_slot",
        "cancel_reason",
        "cancelled_at",
    }
    sets = []
    values = []
    for key, value in fields.items():
        if key not in allowed:
            continue
        sets.append(f"{key} = %s")
        values.append(value)
    if not sets:
        return get_consultation(item_id)
    values.append(item_id)
    db = _db()
    with db.cursor() as cursor:
        cursor.execute(f"UPDATE care_consultations SET {', '.join(sets)} WHERE id = %s", values)
    return get_consultation(item_id)


def list_schedules():
    db = _db()
    if db is None:
        return []
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM care_schedules ORDER BY start_datetime")
        return _rows(cursor)


def get_schedule(item_id):
    db = _db()
    with db.cursor() as cursor:
        cursor.execute("SELECT * FROM care_schedules WHERE id = %s", [item_id])
        return _row(cursor)


def upsert_schedule(data, item_id=None):
    db = _db()
    item_id = item_id or "s_" + uuid4().hex
    existing = get_schedule(item_id)
    with db.cursor() as cursor:
        if existing:
            cursor.execute(
                """
                UPDATE care_schedules
                SET consultation_id=%s, title=%s, start_datetime=%s, end_datetime=%s, category=%s, memo=%s
                WHERE id=%s
                """,
                [
                    data.get("consultation_id"),
                    data["title"],
                    data["start_datetime"],
                    data["end_datetime"],
                    data.get("category") or "기타",
                    data.get("memo"),
                    item_id,
                ],
            )
        else:
            cursor.execute(
                """
                INSERT INTO care_schedules
                  (id, consultation_id, title, start_datetime, end_datetime, category, memo)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    item_id,
                    data.get("consultation_id"),
                    data["title"],
                    data["start_datetime"],
                    data["end_datetime"],
                    data.get("category") or "기타",
                    data.get("memo"),
                ],
            )
    return get_schedule(item_id)


def delete_schedule(item_id):
    db = _db()
    with db.cursor() as cursor:
        cursor.execute("DELETE FROM care_schedules WHERE id = %s", [item_id])
    return True


def confirm_on_calendar(consultation_id, start, end):
    item = get_consultation(consultation_id)
    if not item:
        return None
    title = f"상담 · {item['applicant_name']}"
    schedule = upsert_schedule(
        {
            "consultation_id": consultation_id,
            "title": title,
            "start_datetime": start,
            "end_datetime": end,
            "category": "상담",
            "memo": item.get("admin_memo") or "",
        }
    )
    update_consultation(
        consultation_id,
        {"status": "CONFIRMED", "confirmed_datetime": start},
    )
    return schedule
