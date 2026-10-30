from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request


def sms_configured():
    return bool((os.environ.get("SMS_WEBHOOK_URL") or os.environ.get("ALIGO_KEY") or "").strip())


def send_sms(to_phone, text):
    to_phone = "".join(ch for ch in (to_phone or "") if ch.isdigit())
    text = (text or "").strip()
    if not to_phone or not text:
        raise ValueError("수신 번호와 문구가 필요합니다.")
    webhook = (os.environ.get("SMS_WEBHOOK_URL") or "").strip()
    if webhook:
        payload = json.dumps({"to": to_phone, "text": text, "from": os.environ.get("SMS_FROM") or ""}).encode("utf-8")
        req = urllib.request.Request(webhook, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=12) as res:
            if res.status >= 300:
                raise RuntimeError("문자 서버가 거절했습니다.")
        return True
    key = (os.environ.get("ALIGO_KEY") or "").strip()
    user = (os.environ.get("ALIGO_USER") or "").strip()
    sender = (os.environ.get("ALIGO_SENDER") or os.environ.get("SMS_FROM") or "").strip()
    if key and user and sender:
        body = (
            f"key={key}&user_id={user}&sender={sender}&receiver={to_phone}&msg={urllib.parse.quote(text)}&msg_type={'LMS' if len(text) > 90 else 'SMS'}"
        ).encode("utf-8")
        req = urllib.request.Request("https://apis.aligo.in/send/", data=body, method="POST")
        with urllib.request.urlopen(req, timeout=12) as res:
            raw = res.read().decode("utf-8", "ignore")
        data = json.loads(raw) if raw.startswith("{") else {}
        if str(data.get("result_code")) not in ("1", "0"):
            raise RuntimeError(data.get("message") or "문자 발송에 실패했습니다.")
        return True
    raise RuntimeError("문자 발송 설정(SMS_WEBHOOK_URL 또는 ALIGO_KEY)이 없습니다.")
