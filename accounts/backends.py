from django.contrib.auth.backends import ModelBackend

from .shared_users import find_local_by_login


class EmailOrUsernameBackend(ModelBackend):
    """구버전 username과 신규 email 로그인 ID를 모두 허용한다."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        login_id = (username or kwargs.get("email") or "").strip()
        if not login_id or password is None:
            return None
        user = find_local_by_login(login_id)
        if user is None:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
