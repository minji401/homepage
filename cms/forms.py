from django import forms


def first_form_error(form):
    if form.non_field_errors():
        return str(form.non_field_errors()[0])
    for errors in form.errors.values():
        if errors:
            return str(errors[0])
    return "입력 내용을 확인해 주세요."

from accounts.shared_users import normalize_phone

from .care_store import CARE_LEVELS, MOBILITY, SLOTS
from .models import Application


class ConsultCreateForm(forms.Form):
    applicant_name = forms.CharField(required=False, max_length=40)
    name = forms.CharField(required=False, max_length=40)
    applicant_phone = forms.CharField(required=False, max_length=20)
    phone = forms.CharField(required=False, max_length=20)
    relation_type = forms.CharField(required=True, max_length=30)
    care_level = forms.CharField(required=False, max_length=30)
    mobility_status = forms.CharField(required=False, max_length=30)
    preferred_time_slot = forms.CharField(required=False, max_length=40)
    preferred_date = forms.CharField(required=False, max_length=20)
    privacy_agreed = forms.BooleanField(required=True)
    senior_name = forms.CharField(required=False, max_length=50)
    patient_name = forms.CharField(required=False, max_length=50)
    patient_id = forms.CharField(required=False, max_length=80)
    patient = forms.CharField(required=False, max_length=80)
    consult_kind = forms.CharField(required=False, max_length=40)

    def clean_preferred_time_slot(self):
        return self.cleaned_data.get("preferred_time_slot") or "시간무관"

    def clean(self):
        cleaned = super().clean()
        name = (cleaned.get("applicant_name") or cleaned.get("name") or "").strip()
        phone = normalize_phone(cleaned.get("applicant_phone") or cleaned.get("phone") or "")
        if not name or len(phone) < 10:
            raise forms.ValidationError("신청자명과 연락처를 입력해 주세요.")
        cleaned["applicant_name"] = name
        cleaned["applicant_phone"] = phone
        cleaned["senior_name"] = (cleaned.get("senior_name") or cleaned.get("patient_name") or "").strip()
        cleaned["patient_id"] = cleaned.get("patient_id") or cleaned.get("patient") or ""
        if not cleaned["patient_id"] and len(cleaned["senior_name"]) < 2:
            raise forms.ValidationError("입소 대상 어르신 성명을 입력해 주세요.")
        relation = (cleaned.get("relation_type") or "").strip()
        if relation not in ("자녀", "배우자", "본인", "기타"):
            raise forms.ValidationError("어르신과의 관계를 선택해 주세요.")
        cleaned["relation_type"] = relation
        cleaned["consult_kind"] = (cleaned.get("consult_kind") or "입소 상담").strip() or "입소 상담"
        slot = cleaned.get("preferred_time_slot") or "시간무관"
        if slot not in SLOTS:
            raise forms.ValidationError("희망 시간대를 선택해 주세요.")
        cleaned["preferred_time_slot"] = slot
        if not cleaned.get("patient_id"):
            if cleaned.get("care_level") not in CARE_LEVELS:
                raise forms.ValidationError("장기요양등급을 선택해 주세요.")
            if cleaned.get("mobility_status") not in MOBILITY:
                raise forms.ValidationError("보행상태를 선택해 주세요.")
        return cleaned


class ApplicationApiForm(forms.Form):
    kind = forms.ChoiceField(choices=Application.KIND_CHOICES)
    name = forms.CharField(required=True, max_length=40)
    phone = forms.CharField(required=True, max_length=20)
    title = forms.CharField(required=False, max_length=200)
    body = forms.CharField(required=False, max_length=4000)
    memo = forms.CharField(required=False, max_length=4000)
    senior_name = forms.CharField(required=False, max_length=50)
    patient_name = forms.CharField(required=False, max_length=50)
    patient_id = forms.CharField(required=False, max_length=80)
    type = forms.CharField(required=False, max_length=200)
    time = forms.CharField(required=False, max_length=200)
    date = forms.CharField(required=False, max_length=200)
    day = forms.CharField(required=False, max_length=200)
    item = forms.CharField(required=False, max_length=200)
    address = forms.CharField(required=False, max_length=200)


class SearchLogForm(forms.Form):
    q = forms.CharField(required=False, max_length=80)
