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
