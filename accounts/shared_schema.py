"""공유 DB에 상담·일정·상품·주문 확장 테이블을 만듭니다. Django 마이그레이션은 돌리지 않습니다."""

from __future__ import annotations

from django.db import connections
from django.db.utils import OperationalError, ProgrammingError

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      phone TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'user',
      herium_linked INTEGER NOT NULL DEFAULT 0,
      herium_relation TEXT,
      herium_note TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
      id TEXT PRIMARY KEY,
      number TEXT NOT NULL UNIQUE,
      user_id TEXT,
      type TEXT NOT NULL,
      name TEXT NOT NULL,
      phone TEXT NOT NULL,
      address TEXT NOT NULL DEFAULT '',
      memo TEXT NOT NULL DEFAULT '',
      topics TEXT NOT NULL DEFAULT '[]',
      items TEXT NOT NULL DEFAULT '[]',
      total INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'received',
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS care_consultations (
      id TEXT PRIMARY KEY,
      user_id TEXT,
      applicant_name TEXT NOT NULL,
      applicant_phone TEXT NOT NULL,
      relation_type TEXT NOT NULL DEFAULT '',
      care_level TEXT NOT NULL DEFAULT '',
      mobility_status TEXT NOT NULL DEFAULT '',
      preferred_date TEXT,
      preferred_time_slot TEXT,
      privacy_agreed INTEGER NOT NULL DEFAULT 0,
      confirmed_datetime TEXT,
      status TEXT NOT NULL DEFAULT 'PENDING',
      sms_sent_at TEXT,
      sms_content TEXT,
      sms_ok INTEGER,
      admin_memo TEXT,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS care_schedules (
      id TEXT PRIMARY KEY,
      consultation_id TEXT,
      title TEXT NOT NULL,
      start_datetime TEXT NOT NULL,
      end_datetime TEXT NOT NULL,
      category TEXT NOT NULL DEFAULT '기타',
      memo TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS site_contents (
      id TEXT PRIMARY KEY,
      content_key TEXT NOT NULL UNIQUE,
      title TEXT,
      content TEXT,
      image_url TEXT,
      updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shop_profiles (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL UNIQUE,
      recipient_name TEXT NOT NULL DEFAULT '',
      recipient_phone TEXT NOT NULL DEFAULT '',
      zipcode TEXT NOT NULL DEFAULT '',
      address_basic TEXT NOT NULL DEFAULT '',
      address_detail TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      price INTEGER NOT NULL,
      sale_price INTEGER,
      stock INTEGER NOT NULL DEFAULT 0,
      category TEXT NOT NULL DEFAULT '',
      thumbnail_url TEXT NOT NULL DEFAULT '',
      description TEXT NOT NULL DEFAULT '',
      is_hygiene_product INTEGER NOT NULL DEFAULT 0,
      is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS order_items (
      id TEXT PRIMARY KEY,
      order_id TEXT NOT NULL,
      product_id TEXT,
      product_name TEXT NOT NULL,
      unit_price INTEGER NOT NULL,
      quantity INTEGER NOT NULL
    )
    """,
]

USER_COLUMNS = [
    ("marketing_agreed", "INTEGER NOT NULL DEFAULT 0"),
    ("age_14_agreed", "INTEGER NOT NULL DEFAULT 0"),
    ("withdrawn_at", "TEXT"),
]

ORDER_COLUMNS = [
    ("payment_key", "TEXT"),
    ("zipcode", "TEXT"),
    ("address_basic", "TEXT"),
    ("address_detail", "TEXT"),
    ("tracking_number", "TEXT"),
    ("recipient_name", "TEXT"),
    ("recipient_phone", "TEXT"),
]

CONSULT_COLUMNS = [
    ("sms_ok", "INTEGER"),
    ("sms_sent_at", "TEXT"),
    ("sms_content", "TEXT"),
    ("admin_memo", "TEXT"),
    ("patient_id", "TEXT"),
    ("senior_name", "TEXT"),
    ("consult_kind", "TEXT NOT NULL DEFAULT '입소 상담'"),
    ("cancel_reason", "TEXT"),
    ("cancelled_at", "TEXT"),
]


def _existing_columns(cursor, vendor, table):
    if vendor == "sqlite":
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}
    cursor.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        [table],
    )
    return {row[0] for row in cursor.fetchall()}


def ensure_integration_schema():
    from django.conf import settings

    if "shared" not in getattr(settings, "DATABASES", {}):
        return
    try:
        apply_shared_schema(connections["shared"])
    except (OperationalError, ProgrammingError):
        return


def apply_shared_schema(connection):
    vendor = connection.vendor
    try:
        with connection.cursor() as cursor:
            for sql in TABLES:
                cursor.execute(sql)
            for table, cols in (("users", USER_COLUMNS), ("orders", ORDER_COLUMNS), ("care_consultations", CONSULT_COLUMNS)):
                try:
                    existing = _existing_columns(cursor, vendor, table)
                except (OperationalError, ProgrammingError):
                    continue
                if not existing:
                    continue
                for name, coltype in cols:
                    if name in existing:
                        continue
                    try:
                        if vendor == "postgresql":
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {coltype}")
                        else:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
                    except (OperationalError, ProgrammingError):
                        continue
    except (OperationalError, ProgrammingError):
        return
