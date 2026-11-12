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

(function () {
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
    function csrfToken() {
        const input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input && input.value) return input.value;
        return getCookie("csrftoken") || getCookie("CSRF-TOKEN");
    }
    function ensureModal() {
        let overlay = document.getElementById("cancelAppModal");
        if (overlay) return overlay;
        overlay = document.createElement("div");
        overlay.id = "cancelAppModal";
        overlay.className = "consult-done-overlay";
        overlay.innerHTML =
            '<div class="consult-done-box" role="dialog" aria-modal="true">' +
            "<h2>상담/견학 신청을 취소하시겠습니까?</h2>" +
            '<label class="cancel-reason-label" for="cancelReasonSelect">취소 사유</label>' +
            '<select id="cancelReasonSelect">' +
            '<option value="일정 변경">일정 변경</option>' +
            '<option value="타 시설 이용">타 시설 이용</option>' +
            '<option value="단순 문의 해결">단순 문의 해결</option>' +
            '<option value="기타">기타 직접 입력</option>' +
            "</select>" +
            '<input id="cancelReasonOther" type="text" maxlength="200" placeholder="기타 사유를 입력해 주세요" hidden>' +
            '<div class="consult-done-actions">' +
            '<button type="button" class="ghost-btn" id="cancelAppClose">닫기</button>' +
            '<button type="button" class="btn-gold" id="cancelAppConfirm">취소 확정</button>' +
            "</div></div>";
        document.body.appendChild(overlay);
        return overlay;
    }
    function openModal(overlay) {
        overlay.hidden = false;
        overlay.classList.add("is-open");
        overlay.style.display = "flex";
        overlay.style.zIndex = "9999";
    }
    function closeModal(overlay) {
        if (!overlay) return;
        overlay.classList.remove("is-open");
        overlay.hidden = true;
        overlay.style.display = "none";
        const confirmBtn = overlay.querySelector("#cancelAppConfirm");
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = "취소 확정";
        }
    }
    let cancelTarget = null;
    document.addEventListener("click", function (e) {
        const closeBtn = e.target.closest("#cancelAppClose");
        if (closeBtn) {
            closeModal(document.getElementById("cancelAppModal"));
            cancelTarget = null;
            return;
        }
        const confirmBtn = e.target.closest("#cancelAppConfirm");
        if (confirmBtn) {
            e.preventDefault();
            const overlay = document.getElementById("cancelAppModal");
            const id = cancelTarget && (cancelTarget.getAttribute("data-id") || "").trim();
            if (!id) {
                window.alert("취소할 신청을 찾지 못했습니다. 페이지를 새로고침해 주세요.");
                return;
            }
            const select = document.getElementById("cancelReasonSelect");
            const other = document.getElementById("cancelReasonOther");
            let reason = (select && select.value) || "기타";
            if (reason === "기타") reason = ((other && other.value) || "").trim() || "기타";
            const token = csrfToken();
            if (!token) {
                window.alert("보안 토큰을 읽지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.");
                return;
            }
            confirmBtn.disabled = true;
            confirmBtn.textContent = "처리 중...";
            fetch("/api/applications/" + encodeURIComponent(id) + "/cancel/", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json", "X-CSRFToken": token },
                body: JSON.stringify({ cancel_reason: reason })
            }).then(function (res) {
                return res.text().then(function (text) {
                    let data = {};
                    try { data = text ? JSON.parse(text) : {}; } catch (_err) { data = { message: text.slice(0, 180) }; }
                    return { status: res.status, data: data };
                });
            }).then(function (result) {
                const data = result.data || {};
                if (!data.ok) {
                    window.alert(data.message || ("취소하지 못했습니다. (HTTP " + result.status + ")"));
                    confirmBtn.disabled = false;
                    confirmBtn.textContent = "취소 확정";
                    return;
                }
                window.alert("상담 신청이 취소되었습니다.");
                closeModal(overlay);
                window.location.reload();
            }).catch(function (err) {
                window.alert("서버에 연결할 수 없습니다. " + (err && err.message ? err.message : ""));
                confirmBtn.disabled = false;
                confirmBtn.textContent = "취소 확정";
            });
            return;
        }
        const btn = e.target.closest(".js-cancel-app, .js-consult-cancel");
        if (!btn) return;
        e.preventDefault();
        cancelTarget = btn;
        const overlay = ensureModal();
        const other = overlay.querySelector("#cancelReasonOther");
        const select = overlay.querySelector("#cancelReasonSelect");
        if (select && other) {
            other.hidden = select.value !== "기타";
        }
        openModal(overlay);
    });
    document.addEventListener("change", function (e) {
        if (e.target && e.target.id === "cancelReasonSelect") {
            const other = document.getElementById("cancelReasonOther");
            if (other) other.hidden = e.target.value !== "기타";
        }
    });
    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") closeModal(document.getElementById("cancelAppModal"));
    });
})();
