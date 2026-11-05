from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from .password_policy import PASSWORD_REGEX, PASSWORD_RULE


class SharedPasswordValidator:
    """헤리움·현대의료기 공통: 8~16자, 영문/숫자/특수문자 각 1자 이상."""

    def validate(self, password, user=None):
        del user
        RegexValidator(regex=PASSWORD_REGEX, message=PASSWORD_RULE)(password)

    def get_help_text(self):
        return PASSWORD_RULE
