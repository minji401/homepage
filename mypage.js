(function () {
    "use strict";

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.indexOf(name + "=") === 0) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return "";
    }

    function headers() {
        return { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") };
    }

    function showMessage(el, text, ok) {
        if (!el) return;
        el.textContent = text;
        el.classList.remove("is-error", "is-ok");
        el.classList.add(ok ? "is-ok" : "is-error");
    }

    const profileForm = document.getElementById("mypageProfileForm");
    if (profileForm) {
        const message = document.getElementById("profileMessage");
        profileForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const payload = {
                name: (profileForm.name.value || "").trim(),
                email: (profileForm.email.value || "").trim(),
                phone: (profileForm.phone.value || "").trim(),
                currentPassword: profileForm.currentPassword.value || "",
                newPassword: profileForm.newPassword.value || ""
            };
            fetch("/accounts/mypage/profile/", {
                method: "POST",
                credentials: "same-origin",
                headers: headers(),
                body: JSON.stringify(payload)
            }).then(function (res) { return res.json(); }).then(function (data) {
                showMessage(message, data.message || (data.ok ? "저장했습니다." : "저장하지 못했습니다."), data.ok);
                if (data.ok && payload.newPassword) {
                    profileForm.currentPassword.value = "";
                    profileForm.newPassword.value = "";
                }
            }).catch(function () {
                showMessage(message, "서버에 연결할 수 없습니다.", false);
            });
        });
    }

    const seniorForm = document.getElementById("seniorForm");
    const seniorGrid = document.getElementById("seniorGrid");
    const openBtn = document.getElementById("openSeniorForm");
    const cancelBtn = document.getElementById("cancelSeniorForm");

    function openForm(data) {
        if (!seniorForm) return;
        seniorForm.hidden = false;
        seniorForm.id.value = data && data.id ? data.id : "";
        seniorForm.name.value = data && data.name ? data.name : "";
        seniorForm.relationship.value = data && data.relationship ? data.relationship : "기타";
        seniorForm.birth_date.value = data && data.birth_date ? data.birth_date : "";
        seniorForm.care_grade.value = data && data.care_grade ? data.care_grade : "";
        seniorForm.note.value = data && data.note ? data.note : "";
        document.getElementById("seniorFormTitle").textContent = seniorForm.id.value ? "어르신 정보 수정" : "새 어르신 등록";
        seniorForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    if (openBtn) openBtn.addEventListener("click", function () { openForm(null); });
    if (cancelBtn) cancelBtn.addEventListener("click", function () { seniorForm.hidden = true; });

    if (seniorForm) {
        seniorForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const id = seniorForm.id.value;
            const payload = {
                name: (seniorForm.name.value || "").trim(),
                relationship: seniorForm.relationship.value,
                birth_date: seniorForm.birth_date.value,
                care_grade: seniorForm.care_grade.value,
                note: seniorForm.note.value
            };
            const url = id ? "/accounts/seniors/" + id + "/" : "/accounts/seniors/";
            fetch(url, {
                method: "POST",
                credentials: "same-origin",
                headers: headers(),
                body: JSON.stringify(payload)
            }).then(function (res) { return res.json(); }).then(function (data) {
                if (!data.ok) {
                    window.alert(data.message || "저장하지 못했습니다.");
                    return;
                }
                window.location.reload();
            }).catch(function () {
                window.alert("서버에 연결할 수 없습니다.");
            });
        });
    }

    if (seniorGrid) {
        seniorGrid.addEventListener("click", function (e) {
            const edit = e.target.closest(".js-edit-senior");
            const del = e.target.closest(".js-del-senior");
            if (edit) {
                const card = edit.closest(".senior-item");
                openForm({
                    id: edit.getAttribute("data-id"),
                    name: card.querySelector("h3").textContent,
                    relationship: (card.querySelector("strong") || {}).textContent || "기타",
                    care_grade: "",
                    note: (card.querySelector(".senior-note") || {}).textContent || ""
                });
                fetch("/accounts/seniors/", { credentials: "same-origin" })
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        const found = (data.items || []).find(function (item) { return String(item.id) === String(edit.getAttribute("data-id")); });
                        if (found) openForm(found);
                    });
            }
            if (del) {
                if (!window.confirm("이 어르신 정보를 삭제할까요?")) return;
                fetch("/accounts/seniors/" + del.getAttribute("data-id") + "/", {
                    method: "DELETE",
                    credentials: "same-origin",
                    headers: headers()
                }).then(function (res) { return res.json(); }).then(function (data) {
                    if (data.ok) window.location.reload();
                    else window.alert(data.message || "삭제하지 못했습니다.");
                });
            }
        });
    }

    const cancelModal = document.getElementById("cancelAppModal");
    const reasonSelect = document.getElementById("cancelReasonSelect");
    const reasonOther = document.getElementById("cancelReasonOther");
    const confirmBtn = document.getElementById("cancelAppConfirm");
    const closeBtn = document.getElementById("cancelAppClose");
    let cancelTarget = null;

    function closeCancelModal() {
        if (cancelModal) cancelModal.hidden = true;
        cancelTarget = null;
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "취소 확정";
        }
    }

    if (reasonSelect && reasonOther) {
        reasonSelect.addEventListener("change", function () {
            const other = reasonSelect.value === "기타";
            reasonOther.hidden = !other;
            if (other) reasonOther.focus();
        });
    }
    if (closeBtn) closeBtn.addEventListener("click", closeCancelModal);
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && cancelModal && !cancelModal.hidden) closeCancelModal();
    });

    document.querySelectorAll(".js-cancel-app").forEach(function (btn) {
        btn.addEventListener("click", function () {
            cancelTarget = btn;
            if (cancelModal) cancelModal.hidden = false;
        });
    });

    if (confirmBtn) {
        confirmBtn.addEventListener("click", function () {
            if (!cancelTarget) return;
            const id = cancelTarget.getAttribute("data-id");
            if (!id) return;
            let reason = (reasonSelect && reasonSelect.value) || "기타";
            if (reason === "기타") {
                reason = ((reasonOther && reasonOther.value) || "").trim() || "기타";
            }
            confirmBtn.disabled = true;
            confirmBtn.textContent = "처리 중...";
            fetch("/api/applications/" + id + "/cancel/", {
                method: "POST",
                credentials: "same-origin",
                headers: headers(),
                body: JSON.stringify({ cancel_reason: reason })
            }).then(function (res) { return res.json().then(function (data) { return { status: res.status, data: data }; }); }).then(function (result) {
                const data = result.data || {};
                if (!data.ok) {
                    window.alert(data.message || "취소하지 못했습니다.");
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = "취소 확정";
                    return;
                }
                const row = cancelTarget.closest("tr");
                if (row) {
                    const badge = row.querySelector(".js-status-badge");
                    if (badge) {
                        badge.textContent = data.status_label || "취소됨";
                        badge.className = "status-badge status-cancelled js-status-badge";
                    }
                    const actions = row.querySelector(".consult-actions");
                    if (actions) actions.textContent = "-";
                }
                closeCancelModal();
            }).catch(function () {
                window.alert("서버에 연결할 수 없습니다.");
                confirmBtn.disabled = false;
                confirmBtn.textContent = "취소 확정";
            });
        });
    }
})();
