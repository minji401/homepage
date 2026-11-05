from pathlib import Path

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
BLOCKED_UPLOAD_EXTS = {
    ".exe", ".sh", ".bat", ".cmd", ".com", ".msi", ".php", ".py", ".js",
    ".html", ".htm", ".svg", ".jsp", ".asp", ".aspx", ".cgi", ".dll", ".so", ".ps1",
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
FILE_EXTS = IMAGE_EXTS | {".pdf"}
STAFF_SHEET_EXTS = {".xlsx", ".xlsm", ".csv"}


def upload_error(upload, allowed=None):
    if upload is None:
        return "파일을 선택해 주세요."
    suffix = Path(getattr(upload, "name", "") or "").suffix.lower()
    if suffix in BLOCKED_UPLOAD_EXTS or suffix.startswith(".php"):
        return "실행 가능한 파일은 올릴 수 없습니다."
    allowed = allowed or IMAGE_EXTS
    if suffix not in allowed:
        return "허용되지 않은 파일 형식입니다."
    size = int(getattr(upload, "size", 0) or 0)
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        return "파일은 10MB 이하만 올릴 수 있습니다."
    return ""
