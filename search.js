/* ==========================================================================
   헤리움 케어센터 통합검색
   컴포넌트 구조 (정적 HTML 기준):
   - SearchOverlay     : 네비 아래 검색 레이어 열림/닫힘
   - SearchForm        : 키워드 제출 → 결과 페이지 이동
   - SearchFilterBar   : 검색범위 · 검색기간 필터
   - PopularKeywords   : 인기검색어(주간/일간)
   - ResultTabs        : 카테고리 탭
   - ResultSummary     : 메뉴/게시판 건수
   - ResultList        : 검색 결과 목록
   ========================================================================== */

(function () {
    "use strict";

    function getBasePath() {
        const link = document.querySelector('link[href*="main.css"]');
        const href = link ? link.getAttribute("href") : "";
        return href && href.indexOf("../") === 0 ? "../" : "";
    }

    const BASE = getBasePath();
    const SEARCH_PAGE = BASE + "search.html";
    const SITEMAP_PAGE = BASE + "sitemap.html";

    const RECOMMENDED = ["입소안내", "이용요금", "주야간보호", "방문요양", "오시는 길", "자원봉사", "식단표"];

    const POPULAR = {
        week: ["입소안내", "이용요금", "주야간보호", "방문요양", "오시는 길", "자원봉사", "식단표", "면회", "장기요양등급", "치매프로그램"],
        day: ["주야간보호", "면회", "식단표", "입소안내", "방문목욕", "이용요금", "오시는 길", "후원", "공지사항", "견학신청"]
    };

    const SEARCH_INDEX = [
        { type: "menu", tab: "about", title: "인사말", body: "헤리움 케어센터을 찾아주신 여러분을 환영합니다. 따뜻한 돌봄으로 어르신을 모시겠습니다.", path: "요양원 소개 > 인사말", url: "about/about.html", date: "2026-03-01" },
        { type: "menu", tab: "about", title: "시설 둘러보기", body: "생활실, 프로그램실, 식당, 재활치료실 등 시설 공간을 소개합니다.", path: "요양원 소개 > 시설 둘러보기", url: "about/facility.html", date: "2026-03-01" },
        { type: "menu", tab: "about", title: "오시는 길", body: "영천시 역전로 16(완산동 1081-5), 대표전화 054-334-9986", path: "요양원 소개 > 오시는 길", url: "about/location.html", date: "2026-03-02" },
        { type: "menu", tab: "about", title: "조직표", body: "원장, 사무국, 간호팀, 요양팀, 사회복지팀, 영양팀 조직 구성", path: "요양원 소개 > 조직표", url: "about/organization.html", date: "2026-03-02" },
        { type: "menu", tab: "about", title: "경영공시", body: "일반현황, 기관운영, 주요사업 및 경영성과, 대내외 평가 등 경영공시 항목을 안내합니다.", path: "요양원 소개 > 경영공시", url: "about/disclosure.html", date: "2026-03-03" },
        { type: "menu", tab: "about", title: "제도소개", body: "노인장기요양보험의 목적, 적용대상, 장기요양인정 절차를 안내합니다.", path: "요양원 소개 > 제도소개", url: "about/system.html", date: "2026-03-03" },
        { type: "menu", tab: "about", title: "협력기관", body: "지역 의료기관 및 복지기관과 협력하여 어르신 건강을 지원합니다.", path: "요양원 소개 > 협력기관", url: "about/partners.html", date: "2026-03-03" },
        { type: "menu", tab: "service", title: "주야간보호", body: "주야간보호 서비스로 낮 동안 식사, 프로그램, 건강관리를 제공합니다.", path: "서비스 안내 > 주야간보호", url: "service/nighttime.html", date: "2026-04-01" },
        { type: "menu", tab: "service", title: "요양원", body: "24시간 입소 요양 서비스와 맞춤형 케어를 안내합니다.", path: "서비스 안내 > 요양원", url: "service/nursing.html", date: "2026-04-01" },
        { type: "menu", tab: "service", title: "가정방문급여", body: "방문요양과 방문목욕 등 가정으로 찾아가는 재가급여를 안내합니다.", path: "서비스 안내 > 가정방문급여", url: "service/home_visit.html", date: "2026-04-02" },
        { type: "menu", tab: "service", title: "방문목욕", body: "이동식 목욕 차량과 방문목욕 서비스를 안내합니다.", path: "서비스 안내 > 방문목욕", url: "service/home_bath.html", date: "2026-04-02" },
        { type: "menu", tab: "service", title: "치매·재활 프로그램", body: "치매 예방과 인지 자극, 재활 운동 프로그램을 운영합니다.", path: "서비스 안내 > 치매·재활 프로그램", url: "service/dementia.html", date: "2026-04-03" },
        { type: "menu", tab: "service", title: "맞춤형 케어 일정표", body: "월간 프로그램과 맞춤형 케어 일정을 안내합니다.", path: "서비스 안내 > 맞춤형 케어 일정표", url: "service/monthly.html", date: "2026-04-03" },
        { type: "menu", tab: "admission", title: "서비스 이용 절차", body: "상담, 시설 견학, 입소 계약 등 서비스 이용 절차를 안내합니다.", path: "이용 방법 > 서비스 이용 절차", url: "admission/procedure.html", date: "2026-05-01" },
        { type: "menu", tab: "admission", title: "이용 요금 및 급여 안내", body: "장기요양 급여와 본인부담금, 이용요금 안내입니다.", path: "이용 방법 > 이용 요금 및 급여 안내", url: "admission/fees.html", date: "2026-05-01" },
        { type: "menu", tab: "admission", title: "이용 현황", body: "입소시설과 주야간보호 정원, 현원, 대기 인원을 안내합니다.", path: "이용 방법 > 이용 현황", url: "admission/status.html", date: "2026-09-15" },
        { type: "menu", tab: "admission", title: "대기자 명단", body: "어르신 성명으로 대기 순번을 조회할 수 있습니다.", path: "이용 방법 > 대기자 명단", url: "admission/waitlist.html", date: "2026-09-15" },
        { type: "menu", tab: "admission", title: "장기요양등급 신청 안내", body: "국민건강보험공단 장기요양등급 신청 방법과 필요 서류를 안내합니다.", path: "이용 방법 > 장기요양등급 신청 안내", url: "admission/period.html", date: "2026-05-02" },
        { type: "menu", tab: "admission", title: "시설 방문/견학 신청", body: "시설 방문 및 견학 신청 방법을 안내합니다.", path: "이용 방법 > 시설 방문/견학 신청", url: "admission/tour.html", date: "2026-05-02" },
        { type: "menu", tab: "admission", title: "입소 준비물 및 유의사항", body: "입소 시 준비물, 면회, 외출 등 유의사항을 안내합니다.", path: "이용 방법 > 입소 준비물 및 유의사항", url: "admission/requirements.html", date: "2026-05-03" },
        { type: "menu", tab: "volunteer", title: "자원봉사", body: "재능기부, 위문 공연, 말벗 봉사 등 자원봉사 활동을 안내합니다.", path: "사랑나눔 > 자원봉사", url: "volunteer/intro.html", date: "2026-06-01" },
        { type: "menu", tab: "volunteer", title: "후원", body: "물품 후원과 지정기탁 등 후원 안내입니다.", path: "사랑나눔 > 후원", url: "volunteer/application.html", date: "2026-06-01" },
        { type: "menu", tab: "community", title: "공지사항", body: "요양원 운영 공지와 프로그램 안내를 확인하실 수 있습니다.", path: "요양원 소식 > 공지사항", url: "community/notice.html", date: "2026-06-10" },
        { type: "menu", tab: "community", title: "활동 갤러리", body: "어르신 활동 사진과 행사 모습을 소개합니다.", path: "요양원 소식 > 활동 갤러리", url: "community/gallery.html", date: "2026-06-10" },
        { type: "menu", tab: "community", title: "주간 식단표", body: "이번 주 조식, 중식, 석식 식단을 안내합니다.", path: "요양원 소식 > 주간 식단표", url: "community/menu.html", date: "2026-09-08" },
        { type: "menu", tab: "community", title: "자주 묻는 질문", body: "입소, 면회, 이용요금 등 자주 묻는 질문과 답변입니다.", path: "요양원 소식 > 자주 묻는 질문", url: "community/faq.html", date: "2026-06-12" },
        { type: "menu", tab: "community", title: "1:1 상담 및 문의", body: "입소 상담과 서비스 이용 문의를 받습니다.", path: "요양원 소식 > 1:1 상담 및 문의", url: "community/inquiry.html", date: "2026-06-12" },
        { type: "board", tab: "community", title: "2026년 9월 프로그램 안내", body: "원예치료, 음악치료, 인지프로그램 등 9월 월간 프로그램 일정입니다.", path: "요양원 소식 > 공지사항", url: "community/notice.html", date: "2026-09-01" },
        { type: "board", tab: "community", title: "시설 점검 안내", body: "소방설비 및 시설 안전 점검으로 일부 프로그램이 조정됩니다.", path: "요양원 소식 > 공지사항", url: "community/notice.html", date: "2026-09-10" },
        { type: "board", tab: "volunteer", title: "자원봉사자 모집 공고", body: "말벗 봉사와 프로그램 보조 자원봉사자를 모집합니다.", path: "사랑나눔 > 자원봉사", url: "volunteer/intro.html", date: "2026-09-05" },
        { type: "board", tab: "admission", title: "입소 절차 변경 안내", body: "입소 상담 예약 후 견학, 계약 순으로 절차가 안내됩니다.", path: "이용 방법 > 서비스 이용 절차", url: "admission/procedure.html", date: "2026-08-20" },
        { type: "board", tab: "admission", title: "신규 면회 수칙 안내", body: "면회 시간, 예약 방법, 감염 예방 수칙을 안내합니다.", path: "이용 방법 > 입소 준비물 및 유의사항", url: "admission/requirements.html", date: "2026-09-07" },
        { type: "board", tab: "service", title: "주야간보호 이용 안내", body: "주야간보호 대상, 이용 시간, 차량 운행 노선을 안내합니다.", path: "서비스 안내 > 주야간보호", url: "service/nighttime.html", date: "2026-08-28" },
        { type: "board", tab: "community", title: "이번 주 식단 안내", body: "잡곡밥, 쇠고기 미역국, 고등어 구이 등 이번 주 식단입니다.", path: "요양원 소식 > 주간 식단표", url: "community/menu.html", date: "2026-09-14" }
    ];

    const TAB_LABELS = [
        { id: "all", label: "전체" },
        { id: "about", label: "요양원 소개" },
        { id: "service", label: "서비스 안내" },
        { id: "admission", label: "이용 방법" },
        { id: "volunteer", label: "사랑나눔" },
        { id: "community", label: "요양원 소식" }
    ];

    /* ---------- SearchOverlay ---------- */
    const SearchOverlay = {
        overlay: null,
        button: null,
        input: null,
        isOpen: false,

        init: function () {
            this.overlay = document.getElementById("searchOverlay");
            this.button = document.querySelector(".js-open-search");
            if (!this.overlay) return;

            const form = this.overlay.querySelector(".js-search-form");
            if (form) form.setAttribute("action", SEARCH_PAGE);

            this.input = this.overlay.querySelector(".js-overlay-input");

            document.querySelectorAll(".js-open-search").forEach((el) => {
                el.addEventListener("click", (e) => {
                    e.preventDefault();
                    if (this.isOpen) this.close();
                    else this.open();
                });
            });

            document.querySelectorAll(".js-close-search").forEach((el) => {
                el.addEventListener("click", (e) => {
                    e.preventDefault();
                    this.close();
                });
            });

            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && this.isOpen) this.close();
            });

            this.overlay.querySelectorAll(".js-recommend-tag").forEach((btn) => {
                btn.addEventListener("click", () => {
                    goSearch(btn.getAttribute("data-q") || "");
                });
            });

            if (form) {
                form.addEventListener("submit", (e) => {
                    const q = (this.input && this.input.value || "").trim();
                    if (!q) {
                        e.preventDefault();
                        if (this.input) this.input.focus();
                    }
                });
            }
        },

        open: function () {
            this.isOpen = true;
            this.overlay.hidden = false;
            document.body.classList.add("is-search-open");
            if (this.button) {
                this.button.classList.add("is-open");
                this.button.setAttribute("aria-expanded", "true");
            }
            if (this.input) {
                setTimeout(() => this.input.focus(), 50);
            }
        },

        close: function () {
            this.isOpen = false;
            this.overlay.hidden = true;
            document.body.classList.remove("is-search-open");
            if (this.button) {
                this.button.classList.remove("is-open");
                this.button.setAttribute("aria-expanded", "false");
            }
        }
    };

    function goSearch(q, extra) {
        extra = extra || {};
        const params = new URLSearchParams();
        params.set("q", q);
        if (extra.scope) params.set("scope", extra.scope);
        if (extra.period) params.set("period", extra.period);
        if (extra.from) params.set("from", extra.from);
        if (extra.to) params.set("to", extra.to);
        if (extra.tab) params.set("tab", extra.tab);
        if (q) {
            fetch("/api/search/log/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": decodeURIComponent((document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "")
                },
                body: JSON.stringify({ q: q })
            }).catch(function () {});
        }
        window.location.href = SEARCH_PAGE + "?" + params.toString();
    }

    /* ---------- 검색 엔진 ---------- */
    function parseDate(value) {
        if (!value) return null;
        return new Date(value + "T00:00:00");
    }

    function periodRange(period, from, to) {
        const today = new Date("2026-09-14T00:00:00");
        if (period === "week") return { from: addDays(today, -7), to: today };
        if (period === "month") return { from: addDays(today, -30), to: today };
        if (period === "year") return { from: addDays(today, -365), to: today };
        if (period === "custom") return { from: parseDate(from), to: parseDate(to) };
        return { from: null, to: null };
    }

    function addDays(date, days) {
        const next = new Date(date);
        next.setDate(next.getDate() + days);
        return next;
    }

    function inRange(itemDate, range) {
        if (!range.from && !range.to) return true;
        const d = parseDate(itemDate);
        if (!d) return true;
        if (range.from && d < range.from) return false;
        if (range.to && d > range.to) return false;
        return true;
    }

    function escapeHtml(text) {
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function highlight(text, query) {
        const safe = escapeHtml(text);
        if (!query) return safe;
        const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        return safe.replace(new RegExp(escaped, "gi"), (m) => "<em>" + m + "</em>");
    }

    function filterItems(state) {
        const q = state.query.trim();
        const range = periodRange(state.period, state.from, state.to);

        return SEARCH_INDEX.filter((item) => {
            if (!inRange(item.date, range)) return false;

            if (q) {
                const inTitle = item.title.indexOf(q) !== -1;
                const inBody = item.body.indexOf(q) !== -1;
                if (state.scope === "title" && !inTitle) return false;
                if (state.scope === "body" && !inBody) return false;
                if (state.scope === "all" && !inTitle && !inBody && item.path.indexOf(q) === -1) return false;
            }

            if (state.tab !== "all" && item.tab !== state.tab) return false;
            return true;
        });
    }

    /* ---------- SearchResults Page ---------- */
    const SearchResults = {
        state: {
            query: "",
            scope: "all",
            period: "all",
            from: "",
            to: "",
            tab: "all",
            popular: "week"
        },

        init: function () {
            const app = document.getElementById("searchResultApp");
            if (!app) return;

            const params = new URLSearchParams(window.location.search);
            this.state.query = params.get("q") || "";
            this.state.scope = params.get("scope") || "all";
            this.state.period = params.get("period") || "all";
            this.state.from = params.get("from") || "";
            this.state.to = params.get("to") || "";
            this.state.tab = params.get("tab") || "all";

            this.bindFilter();
            this.bindPopular();
            this.render();
        },

        bindFilter: function () {
            const form = document.getElementById("searchFilterForm");
            const periodInputs = form.querySelectorAll('input[name="period"]');
            const dateRange = document.getElementById("searchDateRange");

            form.querySelector('input[name="q"]').value = this.state.query;

            form.querySelectorAll('input[name="scope"]').forEach((el) => {
                el.checked = el.value === this.state.scope;
            });
            periodInputs.forEach((el) => {
                el.checked = el.value === this.state.period;
            });
            form.querySelector('input[name="from"]').value = this.state.from;
            form.querySelector('input[name="to"]').value = this.state.to;
            this.toggleDates(this.state.period === "custom");

            periodInputs.forEach((el) => {
                el.addEventListener("change", () => {
                    this.toggleDates(el.value === "custom");
                });
            });

            form.addEventListener("submit", (e) => {
                e.preventDefault();
                const data = new FormData(form);
                goSearch((data.get("q") || "").trim(), {
                    scope: data.get("scope"),
                    period: data.get("period"),
                    from: data.get("from"),
                    to: data.get("to"),
                    tab: "all"
                });
            });
        },

        toggleDates: function (enabled) {
            const wrap = document.getElementById("searchDateRange");
            wrap.classList.toggle("is-disabled", !enabled);
            wrap.querySelectorAll("input").forEach((el) => {
                el.disabled = !enabled;
            });
        },

        bindPopular: function () {
            const weekBtn = document.getElementById("popularWeek");
            const dayBtn = document.getElementById("popularDay");
            weekBtn.addEventListener("click", () => {
                this.state.popular = "week";
                weekBtn.classList.add("is-active");
                dayBtn.classList.remove("is-active");
                this.renderPopular();
            });
            dayBtn.addEventListener("click", () => {
                this.state.popular = "day";
                dayBtn.classList.add("is-active");
                weekBtn.classList.remove("is-active");
                this.renderPopular();
            });
            this.renderPopular();
        },

        renderPopular: function () {
            const list = document.getElementById("popularList");
            const words = POPULAR[this.state.popular];
            list.innerHTML = words.map((word, i) => (
                '<li><a href="' + SEARCH_PAGE + "?q=" + encodeURIComponent(word) + '">' +
                '<span class="popular-rank">' + (i + 1) + "</span>" +
                "<span>" + escapeHtml(word) + "</span></a></li>"
            )).join("");
        },

        render: function () {
            const q = this.state.query;
            document.getElementById("searchQueryLabel").textContent = q ? "‘" + q + "’" : "전체";

            const tabFilteredState = Object.assign({}, this.state, { tab: "all" });
            const allMatched = filterItems(tabFilteredState);

            const tabs = document.getElementById("resultTabs");
            tabs.innerHTML = TAB_LABELS.map((tab) => {
                const count = tab.id === "all"
                    ? allMatched.length
                    : allMatched.filter((item) => item.tab === tab.id).length;
                const active = tab.id === this.state.tab ? " is-active" : "";
                return '<button type="button" class="' + active.trim() + '" data-tab="' + tab.id + '">' +
                    tab.label + " (" + count + ")</button>";
            }).join("");

            tabs.querySelectorAll("button").forEach((btn) => {
                btn.addEventListener("click", () => {
                    this.state.tab = btn.getAttribute("data-tab");
                    const url = new URL(window.location.href);
                    url.searchParams.set("tab", this.state.tab);
                    window.history.replaceState({}, "", url);
                    this.render();
                });
            });

            const matched = filterItems(this.state);
            document.getElementById("resultTotal").innerHTML =
                "총 <em>" + matched.length + "</em>건이 검색되었습니다.";

            const menuCount = matched.filter((item) => item.type === "menu").length;
            const boardCount = matched.filter((item) => item.type === "board").length;
            document.getElementById("resultSummary").innerHTML =
                '<div class="result-summary-card"><span>메뉴</span><strong>' + menuCount + "건</strong></div>" +
                '<div class="result-summary-card"><span>게시판</span><strong>' + boardCount + "건</strong></div>";

            const listEl = document.getElementById("resultList");
            if (!this.state.query) {
                listEl.innerHTML = '<div class="search-empty"><strong>검색어를 입력해 주세요.</strong>상단 검색창에 키워드를 입력하면 메뉴와 게시판을 함께 찾습니다.</div>';
                return;
            }
            if (!matched.length) {
                listEl.innerHTML = '<div class="search-empty"><strong>검색 결과가 없습니다.</strong>다른 검색어나 기간을 선택해 보세요.</div>';
                return;
            }

            const groups = [
                { type: "menu", title: "메뉴" },
                { type: "board", title: "게시판" }
            ];
            listEl.innerHTML = groups.map((group) => {
                const items = matched.filter((item) => item.type === group.type);
                if (!items.length) return "";
                return '<section class="result-group"><h3>' + group.title + " (" + items.length + ")</h3>" +
                    items.map((item) => this.itemHtml(item, q)).join("") +
                    "</section>";
            }).join("");
        },

        itemHtml: function (item, q) {
            const badgeClass = item.type === "board" ? " is-board" : "";
            const badgeText = item.type === "board" ? "게시판" : "메뉴";
            return (
                '<article class="result-item">' +
                    '<div class="result-item-head">' +
                        '<span class="result-badge' + badgeClass + '">' + badgeText + "</span>" +
                        '<a class="result-item-title" href="' + BASE + item.url + '">' + highlight(item.title, q) + "</a>" +
                    "</div>" +
                    '<div class="result-item-meta">' +
                        "<span>" + escapeHtml(item.path) + "</span>" +
                        "<span>" + escapeHtml(item.date) + "</span>" +
                    "</div>" +
                    '<p class="result-item-snippet">' + highlight(item.body, q) + "</p>" +
                "</article>"
            );
        }
    };

    function bindAllMenuLink() {
        document.querySelectorAll(".sp").forEach(function (el) {
            el.setAttribute("role", "link");
            el.setAttribute("tabindex", "0");
            el.setAttribute("aria-label", "전체메뉴");
            function go(e) {
                e.preventDefault();
                window.location.href = SITEMAP_PAGE;
            }
            el.addEventListener("click", go);
            el.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    go(e);
                }
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        SearchOverlay.init();
        SearchResults.init();
        bindAllMenuLink();
        fetch("/api/search/keywords/", { credentials: "same-origin" }).then(function (res) {
            return res.json();
        }).then(function (data) {
            if (!data || !data.ok) return;
            if (data.recommended && data.recommended.length) {
                document.querySelectorAll(".search-recommend-tags").forEach(function (box) {
                    box.innerHTML = data.recommended.map(function (word) {
                        return '<a href="' + SEARCH_PAGE + "?q=" + encodeURIComponent(word) + '">' + word + "</a>";
                    }).join("");
                });
            }
            if (data.popular && data.popular.length) {
                POPULAR.week = data.popular;
            }
        }).catch(function () {});
    });
})();
