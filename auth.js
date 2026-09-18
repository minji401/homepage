/* ==========================================================================
   헤리움 케어센터 로그인 / 회원가입 (Django 세션)
   ========================================================================== */

(function () {
    "use strict";

    function getBasePath() {
        const link = document.querySelector('link[href*="main.css"]');
        const href = link ? link.getAttribute("href") : "";
        return href && href.indexOf("../") === 0 ? "../" : "";
    }

    const BASE = getBasePath();

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

    function csrfHeaders() {
        return {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        };
    }

    function parseApiResponse(res) {
        return res.text().then(function (text) {
            var data = {};
            if (text) {
                try {
                    data = JSON.parse(text);
                } catch (err) {
                    var message = "서버 응답을 읽을 수 없습니다.";
                    if (res.status === 403) {
                        message = "보안 검증에 실패했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.";
                    } else if (res.status === 404 || res.status === 405) {
                        message = "로그인 서버에 연결되지 않았습니다. 도메인이 Django 사이트와 같은 주소인지 확인해 주세요.";
                    } else if (res.status >= 500) {
                        message = "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
                    }
                    return { ok: false, status: res.status, data: { message: message } };
                }
            }
            return { ok: res.ok && data.ok !== false, status: res.status, data: data };
        });
    }

    function api(url, options) {
        return fetch(url, Object.assign({ credentials: "same-origin" }, options)).then(parseApiResponse);
    }

    function showMessage(el, text, type) {
        if (!el) return;
        el.textContent = text;
        el.classList.remove("is-error", "is-ok");
        el.classList.add(type === "ok" ? "is-ok" : "is-error");
    }

    function bindPasswordToggles(root) {
        root.querySelectorAll(".toggle-pw").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const input = btn.parentElement.querySelector("input");
                const hidden = input.getAttribute("type") === "password";
                input.setAttribute("type", hidden ? "text" : "password");
                btn.innerHTML = hidden ? '<i class="fas fa-eye-slash"></i>' : '<i class="fas fa-eye"></i>';
            });
        });
    }

    const AuthService = {
        loginWithKakao: function () { this.loginWithSocial("kakao"); },
        loginWithNaver: function () { this.loginWithSocial("naver"); },
        loginWithGoogle: function () { this.loginWithSocial("google"); },
        loginWithSocial: function (provider) {
            const names = { kakao: "카카오", naver: "네이버", google: "구글" };
            window.alert(names[provider] + " 로그인 연동을 준비 중입니다.\n(SDK 키를 연결하면 이 함수에서 인증을 시작합니다.)");
        }
    };

    const TopBarAuth = {
        init: function () {
            const menu = document.querySelector(".user-menu");
            if (!menu) return;

            api("/accounts/me/").then(function (result) {
                const data = result.data || {};
                if (data.authenticated) {
                    var extra = data.is_admin ? '<a href="/staff/">관리페이지</a>' : "";
                    menu.innerHTML =
                        '<span class="user-name">' + data.name + "님</span>" + extra +
                        '<a href="/accounts/logout/" id="logoutLink">로그아웃</a>';
                    const logout = document.getElementById("logoutLink");
                    logout.addEventListener("click", function (e) {
                        e.preventDefault();
                        fetch("/accounts/logout/", {
                            method: "POST",
                            credentials: "same-origin",
                            headers: csrfHeaders()
                        }).then(function () {
                            window.location.href = BASE + "main.html";
                        });
                    });
                } else {
                    const links = menu.querySelectorAll("a");
                    if (links[0]) links[0].setAttribute("href", BASE + "login.html");
                    if (links[1]) links[1].setAttribute("href", BASE + "signup.html");
                }
            }).catch(function () {
                const links = menu.querySelectorAll("a");
                if (links[0]) links[0].setAttribute("href", BASE + "login.html");
                if (links[1]) links[1].setAttribute("href", BASE + "signup.html");
            });
        }
    };

    const LoginForm = {
        init: function () {
            const form = document.getElementById("loginForm");
            if (!form) return;
            const message = document.getElementById("authMessage");
            bindPasswordToggles(form);

            form.addEventListener("submit", function (e) {
                e.preventDefault();
                const id = (form.querySelector('[name="id"]').value || "").trim();
                const password = form.querySelector('[name="password"]').value || "";
                if (!id || !password) {
                    showMessage(message, "아이디와 비밀번호를 입력해 주세요.", "error");
                    return;
                }
                api("/accounts/login/", {
                    method: "POST",
                    headers: csrfHeaders(),
                    body: JSON.stringify({ id: id, password: password })
                }).then(function (result) {
                    if (!result.ok) {
                        showMessage(message, result.data.message || "로그인에 실패했습니다.", "error");
                        return;
                    }
                    window.location.href = result.data.redirect || BASE + "main.html";
                }).catch(function () {
                    showMessage(message, "서버에 연결할 수 없습니다. Django를 실행해 주세요.", "error");
                });
            });

            document.querySelectorAll("[data-provider]").forEach(function (btn) {
                btn.addEventListener("click", function () {
                    const provider = btn.getAttribute("data-provider");
                    if (provider === "kakao") AuthService.loginWithKakao();
                    else if (provider === "naver") AuthService.loginWithNaver();
                    else if (provider === "google") AuthService.loginWithGoogle();
                });
            });
        }
    };

    const SignupForm = {
        init: function () {
            const form = document.getElementById("signupForm");
            if (!form) return;
            const message = document.getElementById("authMessage");
            bindPasswordToggles(form);

            form.addEventListener("submit", function (e) {
                e.preventDefault();
                const data = {
                    id: (form.querySelector('[name="id"]').value || "").trim(),
                    password: form.querySelector('[name="password"]').value || "",
                    passwordConfirm: form.querySelector('[name="passwordConfirm"]').value || "",
                    name: (form.querySelector('[name="name"]').value || "").trim(),
                    phone: (form.querySelector('[name="phone"]').value || "").trim(),
                    email: (form.querySelector('[name="email"]').value || "").trim(),
                    agree: form.querySelector('[name="agree"]').checked
                };

                if (!data.id || !data.password || !data.name || !data.phone) {
                    showMessage(message, "아이디, 비밀번호, 이름, 연락처는 필수입니다.", "error");
                    return;
                }
                if (data.id.length < 4) {
                    showMessage(message, "아이디는 4자 이상 입력해 주세요.", "error");
                    return;
                }
                if (data.password.length < 4) {
                    showMessage(message, "비밀번호는 4자 이상 입력해 주세요.", "error");
                    return;
                }
                if (data.password !== data.passwordConfirm) {
                    showMessage(message, "비밀번호가 서로 다릅니다.", "error");
                    return;
                }
                if (!data.agree) {
                    showMessage(message, "이용약관 및 개인정보 처리에 동의해 주세요.", "error");
                    return;
                }

                api("/accounts/signup/", {
                    method: "POST",
                    headers: csrfHeaders(),
                    body: JSON.stringify(data)
                }).then(function (result) {
                    if (!result.ok) {
                        showMessage(message, result.data.message || "회원가입에 실패했습니다.", "error");
                        return;
                    }
                    window.alert("회원가입이 완료되었습니다. 로그인해 주세요.");
                    window.location.href = BASE + "login.html";
                }).catch(function () {
                    showMessage(message, "서버에 연결할 수 없습니다. Django를 실행해 주세요.", "error");
                });
            });
        }
    };

    const FindAccountForm = {
        init: function () {
            const form = document.getElementById("findAccountForm");
            if (!form) return;
            const message = document.getElementById("authMessage");
            const type = new URLSearchParams(window.location.search).get("type") || "id";

            document.querySelectorAll(".auth-tabs a").forEach(function (link) {
                link.classList.toggle("is-active", link.getAttribute("data-type") === type);
            });

            const idField = form.querySelector(".js-find-id");
            const nameField = form.querySelector(".js-find-name");
            if (type === "password") {
                if (idField) idField.hidden = false;
                if (nameField) nameField.hidden = true;
            } else {
                if (idField) idField.hidden = true;
                if (nameField) nameField.hidden = false;
            }

            form.addEventListener("submit", function (e) {
                e.preventDefault();
                const payload = {
                    type: type,
                    phone: (form.querySelector('[name="phone"]').value || "").trim()
                };
                if (type === "password") {
                    payload.id = (form.querySelector('[name="id"]').value || "").trim();
                    if (!payload.id || !payload.phone) {
                        showMessage(message, "아이디와 연락처를 입력해 주세요.", "error");
                        return;
                    }
                } else {
                    payload.name = (form.querySelector('[name="name"]').value || "").trim();
                    if (!payload.name || !payload.phone) {
                        showMessage(message, "이름과 연락처를 입력해 주세요.", "error");
                        return;
                    }
                }

                api("/accounts/find/", {
                    method: "POST",
                    headers: csrfHeaders(),
                    body: JSON.stringify(payload)
                }).then(function (result) {
                    if (!result.ok) {
                        showMessage(message, result.data.message || "일치하는 회원 정보가 없습니다.", "error");
                        return;
                    }
                    showMessage(message, result.data.message, "ok");
                }).catch(function () {
                    showMessage(message, "서버에 연결할 수 없습니다. Django를 실행해 주세요.", "error");
                });
            });
        }
    };

    window.AuthService = AuthService;

    document.addEventListener("DOMContentLoaded", function () {
        TopBarAuth.init();
        LoginForm.init();
        SignupForm.init();
        FindAccountForm.init();
        document.querySelectorAll(".js-close-popup").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const popup = document.getElementById("sitePopup");
                const hideToday = document.getElementById("popupHideToday");
                if (hideToday && hideToday.checked) {
                    const d = new Date();
                    const today = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
                    localStorage.setItem("herium_popup_hide", today);
                }
                if (popup) popup.remove();
            });
        });
    });
})();
