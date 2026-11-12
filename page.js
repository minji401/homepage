document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".footer-info .info-text p:first-child").forEach(function (row) {
        if (row.textContent.indexOf("기관명") >= 0) return;
        const span = document.createElement("span");
        span.textContent = "기관명 : 헤리움 케어센터";
        row.insertBefore(span, row.firstChild);
    });

    const careForm = document.getElementById("careConsultForm");
    if (careForm) {
        const patientSelect = document.getElementById("inq-patient");
        const seniorInput = careForm.querySelector('[name="senior_name"]');
        const submitBtn = careForm.querySelector('button[type="submit"]');
        fetch("/accounts/me/", { credentials: "same-origin" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data || data.authenticated === false) return;
                const nameInput = careForm.querySelector('[name="applicant_name"]');
                const phoneInput = careForm.querySelector('[name="applicant_phone"]');
                if (nameInput && data.name) {
                    nameInput.value = data.name;
                    nameInput.readOnly = true;
                }
                if (phoneInput && data.phone) phoneInput.value = data.phone;
            })
            .catch(function () {});
        if (patientSelect) {
            fetch("/accounts/seniors/", { credentials: "same-origin" })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    (data.items || []).forEach(function (item) {
                        const option = document.createElement("option");
                        option.value = item.id;
                        option.textContent = item.name + " (" + (item.relationship || "") + ")";
                        option.setAttribute("data-name", item.name);
                        patientSelect.appendChild(option);
                    });
                })
                .catch(function () {});
            patientSelect.addEventListener("change", function () {
                const selected = patientSelect.options[patientSelect.selectedIndex];
                if (seniorInput && selected && selected.getAttribute("data-name")) {
                    seniorInput.value = selected.getAttribute("data-name");
                }
            });
        }
        function consultDoneModal(data, payload) {
            let overlay = document.getElementById("consultDoneModal");
            if (!overlay) {
                overlay = document.createElement("div");
                overlay.id = "consultDoneModal";
                overlay.className = "consult-done-overlay";
                overlay.innerHTML =
                    '<div class="consult-done-box" role="dialog" aria-modal="true" aria-labelledby="consultDoneTitle">' +
                    '<h2 id="consultDoneTitle">상담 신청이 완료되었습니다</h2>' +
                    "<p>접수해 주신 내용을 확인 후 담당자가 순차적으로 연락드리겠습니다.</p>" +
                    '<div class="consult-done-summary" id="consultDoneSummary"></div>' +
                    '<button type="button" class="btn-gold consult-done-ok">확인</button>' +
                    "</div>";
                document.body.appendChild(overlay);
            }
            const applicant = (data && data.applicant_name) || payload.applicant_name || "";
            const senior = (data && data.senior_name) || payload.senior_name || "";
            const when = [
                (data && data.preferred_date) || payload.preferred_date || "",
                (data && data.preferred_time_slot) || payload.preferred_time_slot || ""
            ].filter(Boolean).join(" ");
            const summary = document.getElementById("consultDoneSummary");
            if (summary) {
                summary.innerHTML =
                    "<div>신청인: " + applicant + "</div>" +
                    "<div>어르신: " + senior + "</div>" +
                    "<div>희망 일시: " + (when || "미지정") + "</div>";
            }
            overlay.hidden = false;
            const ok = overlay.querySelector(".consult-done-ok");
            if (ok) {
                ok.onclick = function () {
                    window.location.href = (data && data.redirect) || "/mypage.html";
                };
            }
        }
        careForm.addEventListener("submit", function (e) {
            e.preventDefault();
            const payload = {};
            careForm.querySelectorAll("input, select, textarea").forEach(function (el) {
                if (!el.name) return;
                payload[el.name] = el.type === "checkbox" ? el.checked : (typeof el.value === "string" ? el.value.trim() : el.value);
            });
            if (payload.relationship && !payload.relation_type) payload.relation_type = payload.relationship;
            if (!(payload.senior_name || "").trim()) {
                alert("입소 대상 어르신 성명을 입력해 주세요.");
                if (seniorInput) seniorInput.focus();
                return;
            }
            payload.senior_name = payload.senior_name.trim();
            const csrf = (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
            const headers = { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) };
            try {
                const token = localStorage.getItem("sso_access_token");
                if (token) headers.Authorization = "Bearer " + token;
            } catch (_err) {}
            const originalLabel = submitBtn ? submitBtn.textContent : "";
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "처리 중...";
            }
            fetch("/api/care/consultations/", {
                method: "POST",
                credentials: "same-origin",
                headers: headers,
                body: JSON.stringify(payload)
            }).then(function (res) {
                return res.json().then(function (data) { return data; });
            }).then(function (data) {
                if (data && data.ok) {
                    consultDoneModal(data, payload);
                    return;
                }
                alert((data && data.message) || "신청을 접수하지 못했습니다.");
            }).catch(function () {
                alert("서버에 연결할 수 없습니다.");
            }).finally(function () {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalLabel;
                }
            });
        });
    }

    document.querySelectorAll(".js-demo-form").forEach(function (form) {
        fetch("/accounts/me/", { credentials: "same-origin" })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (!data || data.authenticated === false) return;
                const nameInput = form.querySelector('[name="name"]');
                const phoneInput = form.querySelector('[name="phone"]');
                if (nameInput && data.name) {
                    nameInput.value = data.name;
                    nameInput.readOnly = true;
                }
                if (phoneInput && data.phone) phoneInput.value = data.phone;
            })
            .catch(function () {});
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
