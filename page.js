document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".footer-info .info-text p:first-child").forEach(function (row) {
        if (row.textContent.indexOf("기관명") >= 0) return;
        const span = document.createElement("span");
        span.textContent = "기관명 : 헤리움 케어센터";
        row.insertBefore(span, row.firstChild);
    });

    const careForm = document.getElementById("careConsultForm");
    if (careForm) {
        careForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const payload = {};
            careForm.querySelectorAll("input, select, textarea").forEach(function (el) {
                if (!el.name) return;
                payload[el.name] = el.type === "checkbox" ? el.checked : el.value;
            });
            const csrf = (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
            const headers = { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) };
            try {
                const token = localStorage.getItem("sso_access_token");
                if (token) headers.Authorization = "Bearer " + token;
            } catch (_err) {}
            fetch("/api/care/consultations/", {
                method: "POST",
                credentials: "same-origin",
                headers: headers,
                body: JSON.stringify(payload)
            }).then(function (res) { return res.json(); }).then(function (data) {
                const done = document.getElementById("careConsultDone") || document.getElementById("careDone");
                if (data.ok && done) {
                    careForm.hidden = true;
                    done.hidden = false;
                    return;
                }
                alert(data.message || "신청을 접수하지 못했습니다.");
            }).catch(function () {
                alert("서버에 연결할 수 없습니다.");
            });
        });
    }

    document.querySelectorAll(".js-demo-form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            const kind = form.getAttribute("data-apply");
            if (!kind) {
                alert(form.getAttribute("data-success") || "접수되었습니다. 담당자가 확인 후 연락드리겠습니다. (임시)");
                form.reset();
                return;
            }
            const payload = { kind: kind };
            form.querySelectorAll("input, select, textarea").forEach(function (el) {
                if (!el.name || el.type === "checkbox") return;
                payload[el.name] = el.value;
            });
            const csrf = (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
            fetch("/api/apply/", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) },
                body: JSON.stringify(payload)
            }).then(function (res) { return res.json(); }).then(function (data) {
                alert(data.message || form.getAttribute("data-success") || "접수되었습니다.");
                if (data.ok) form.reset();
            }).catch(function () {
                alert("서버에 연결할 수 없습니다. Django를 실행한 뒤 다시 시도해 주세요.");
            });
        });
    });

    function filterBoard(form) {
        const q = ((form.querySelector('[name="q"]') || {}).value || "").trim();
        const scope = (form.querySelector('[name="scope"]') || {}).value || "all";
        const root = form.closest(".page-body") || document;
        const activePanel = root.querySelector(".tab-panel.is-active");
        const items = (activePanel || root).querySelectorAll("[data-title]");
        let shown = 0;
        items.forEach(function (item) {
            const title = item.getAttribute("data-title") || "";
            const body = item.getAttribute("data-body") || "";
            let hit = !q;
            if (q) {
                if (scope === "title") hit = title.indexOf(q) !== -1;
                else if (scope === "body") hit = body.indexOf(q) !== -1;
                else hit = title.indexOf(q) !== -1 || body.indexOf(q) !== -1;
            }
            item.style.display = hit ? "" : "none";
            if (hit) shown += 1;
        });
        const empty = root.querySelector(".board-empty");
        if (empty) empty.style.display = shown ? "none" : "block";
    }

    document.querySelectorAll(".js-board-search").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();
            filterBoard(form);
        });
    });

    document.querySelectorAll(".sub-tabs").forEach(function (tabBar) {
        const buttons = tabBar.querySelectorAll("[data-tab]");
        const root = tabBar.parentElement;
        buttons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                const id = btn.getAttribute("data-tab");
                buttons.forEach(function (b) {
                    b.classList.toggle("is-active", b === btn);
                });
                root.querySelectorAll(":scope > .tab-panel").forEach(function (panel) {
                    panel.classList.toggle("is-active", panel.id === "tab-" + id);
                });
                const searchForm = root.querySelector(".js-board-search");
                if (searchForm) filterBoard(searchForm);
            });
        });
    });

    const waitForm = document.getElementById("waitForm");
    if (waitForm) {
        waitForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const q = (document.getElementById("waitName").value || "").trim();
            const box = document.getElementById("waitResult");
            fetch("/api/waitlist/?name=" + encodeURIComponent(q), { credentials: "same-origin" })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    const hits = data.items || [];
                    if (!hits.length) {
                        box.innerHTML = '<p class="page-note">조회된 대기자가 없습니다. 성명을 다시 확인해 주세요.</p>';
                        return;
                    }
                    box.innerHTML = '<table class="page-table"><thead><tr><th>성명</th><th>구분</th><th>대기 순번</th></tr></thead><tbody>' +
                        hits.map(function (row) {
                            return "<tr><td>" + row.name + "</td><td>" + row.type + "</td><td>" + row.no + "</td></tr>";
                        }).join("") +
                        "</tbody></table>";
                })
                .catch(function () {
                    box.innerHTML = '<p class="page-note">서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.</p>';
                });
        });
    }

    const floorBtns = document.querySelectorAll(".floor-switch [data-floor]");
    const floorMaps = document.querySelectorAll(".floor-map");
    const floorCaption = document.getElementById("floorCaption");
    const floorLabels = {};
    floorBtns.forEach(function (btn) {
        floorLabels[btn.getAttribute("data-floor")] = btn.getAttribute("data-label") || "";
    });
    floorBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
            const floor = btn.getAttribute("data-floor");
            floorBtns.forEach(function (b) {
                b.classList.toggle("is-active", b === btn);
            });
            floorMaps.forEach(function (map) {
                map.classList.toggle("is-active", map.getAttribute("data-floor") === floor);
            });
            if (floorCaption) floorCaption.textContent = floorLabels[floor] || "";
        });
    });
});

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("careConsultForm");
    if (!form) return;
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        const payload = {
            applicant_name: form.applicant_name.value,
            applicant_phone: form.applicant_phone.value,
            relation_type: form.relation_type.value,
            care_level: form.care_level.value,
            mobility_status: form.mobility_status.value,
            preferred_date: form.preferred_date.value,
            preferred_time_slot: form.preferred_time_slot.value,
            privacy_agreed: form.privacy_agreed.checked
        };
        const csrf = (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
        fetch("/api/care/consultations/", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) },
            body: JSON.stringify(payload)
        }).then(function (res) { return res.json(); }).then(function (data) {
            const done = document.getElementById("careDone");
            if (data.ok) {
                form.hidden = true;
                if (done) { done.hidden = false; done.style.fontSize = "1.35rem"; done.style.fontWeight = "700"; done.style.lineHeight = "1.7"; }
            } else {
                alert(data.message || "신청에 실패했습니다.");
            }
        }).catch(function () {
            alert("서버에 연결할 수 없습니다.");
        });
    });
});
