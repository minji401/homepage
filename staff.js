(function () {
    const toast = document.getElementById("staffToast");

    function showToast(text, isError) {
        if (!toast || !text) return;
        toast.hidden = false;
        toast.textContent = text;
        toast.classList.toggle("is-error", !!isError);
        clearTimeout(showToast.timer);
        showToast.timer = setTimeout(function () {
            toast.hidden = true;
        }, 2800);
    }

    document.querySelectorAll(".staff-flash li").forEach(function (item) {
        showToast(item.textContent, item.classList.contains("error"));
    });

    const checkAll = document.getElementById("checkAll");
    if (checkAll) {
        checkAll.addEventListener("change", function () {
            document.querySelectorAll('input[name="ids"]').forEach(function (box) {
                box.checked = checkAll.checked;
            });
        });
    }

    const bulkForm = document.getElementById("bulkForm");
    if (bulkForm) {
        bulkForm.addEventListener("submit", function (e) {
            const action = (bulkForm.querySelector('[name="bulk"]') || {}).value;
            const checked = bulkForm.querySelectorAll('input[name="ids"]:checked').length;
            if (!checked) {
                e.preventDefault();
                showToast("항목을 선택해 주세요.", true);
                return;
            }
            if (action === "delete" && !window.confirm("선택한 항목을 삭제할까요?")) {
                e.preventDefault();
            }
        });
    }

    document.querySelectorAll("[data-confirm]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            if (!window.confirm(btn.getAttribute("data-confirm"))) {
                e.preventDefault();
            }
        });
    });

    function csrfToken() {
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input && input.value) return input.value;
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.indexOf("csrftoken=") === 0) {
                return decodeURIComponent(cookie.slice("csrftoken=".length));
            }
        }
        return "";
    }

    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".js-staff-cancel");
        if (!btn) return;
        e.preventDefault();
        const id = btn.getAttribute("data-id");
        if (!id) return;
        const reason = window.prompt("취소 사유를 입력해 주세요:", "관리자 직권 취소");
        if (reason === null) return;
        const form = document.createElement("form");
        form.method = "post";
        form.action = "/staff/applications/" + id + "/";
        const fields = {
            csrfmiddlewaretoken: csrfToken(),
            status: "CANCELLED",
            cancel_reason: reason || "관리자 직권 취소",
            next: window.location.pathname + window.location.search
        };
        Object.keys(fields).forEach(function (key) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = key;
            input.value = fields[key];
            form.appendChild(input);
        });
        document.body.appendChild(form);
        form.submit();
    });

    document.querySelectorAll(".js-image-input").forEach(function (input) {
        input.addEventListener("change", function () {
            const file = input.files && input.files[0];
            const preview = document.querySelector(input.getAttribute("data-preview"));
            if (!file || !preview) return;
            const reader = new FileReader();
            reader.onload = function () {
                preview.src = reader.result;
                preview.hidden = false;
            };
            reader.readAsDataURL(file);
        });
    });
})();
