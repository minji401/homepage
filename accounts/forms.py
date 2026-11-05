from django import forms

from .password_policy import PASSWORD_RULE, email_error, name_error, password_error, phone_error
from .shared_users import normalize_phone


def first_form_error(form):
    if form.non_field_errors():
        return str(form.non_field_errors()[0])
    for errors in form.errors.values():
        if errors:
            return str(errors[0])
    return "입력 내용을 확인해 주세요."


class LoginApiForm(forms.Form):
    id = forms.CharField(required=False, max_length=80)
    username = forms.CharField(required=False, max_length=80)
    password = forms.CharField(required=True, max_length=128)
    next = forms.CharField(required=False, max_length=200)

    def clean(self):
        cleaned = super().clean()
        login_id = (cleaned.get("id") or cleaned.get("username") or "").strip()
        if not login_id:
            raise forms.ValidationError("아이디와 비밀번호를 입력해 주세요.")
        nxt = (cleaned.get("next") or "").strip()
        if nxt and (not nxt.startswith("/") or nxt.startswith("//")):
            nxt = ""
        cleaned["login_id"] = login_id
        cleaned["next"] = nxt
        return cleaned


class SignupApiForm(forms.Form):
    email = forms.EmailField(required=True, error_messages={"required": "이메일을 입력해 주세요.", "invalid": "이메일 형식을 확인해 주세요."})
    id = forms.CharField(required=False, max_length=120)
    password = forms.CharField(required=True, max_length=16, min_length=8)
    passwordConfirm = forms.CharField(required=False, max_length=16)
    password_confirm = forms.CharField(required=False, max_length=16)
    name = forms.CharField(required=True, max_length=40)
    phone = forms.CharField(required=True, max_length=20)
    agree = forms.BooleanField(required=False)
    age14 = forms.BooleanField(required=False)
    marketing = forms.BooleanField(required=False)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        message = email_error(email)
        if message:
            raise forms.ValidationError(message)
        return email

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        message = name_error(name)
        if message:
            raise forms.ValidationError(message)
        return name

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email") or (cleaned.get("id") or "").strip().lower()
        if email_error(email):
            raise forms.ValidationError("이메일, 비밀번호, 이름, 연락처는 필수입니다. 이메일을 로그인 ID로 사용해 주세요.")
        cleaned["email"] = email
        password = cleaned.get("password") or ""
        if password_error(password):
            raise forms.ValidationError(PASSWORD_RULE)
        confirm = cleaned.get("passwordConfirm") or cleaned.get("password_confirm") or ""
        if password != confirm:
            raise forms.ValidationError("비밀번호가 서로 다릅니다.")
        if not cleaned.get("agree"):
            raise forms.ValidationError("이용약관 및 개인정보 처리에 동의해 주세요.")
        if not cleaned.get("age14"):
            raise forms.ValidationError("만 14세 이상만 가입할 수 있습니다.")
        digits = normalize_phone(cleaned.get("phone") or "")
        message = phone_error(digits)
        if message:
            raise forms.ValidationError(message)
        cleaned["phone"] = digits
        return cleaned


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(required=True)


class PasswordResetConfirmForm(forms.Form):
    token = forms.CharField(required=True, max_length=200)
    password = forms.CharField(required=True, max_length=16, min_length=8)

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        if password_error(password):
            raise forms.ValidationError(PASSWORD_RULE)
        return password
