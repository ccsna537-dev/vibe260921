(function () {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const EMAIL = "ccsna537@gmail.com";

  /* ---------- 토스트 ---------- */
  const toast = $("#toast");
  let toastTimer;
  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 2200);
  }

  /* ---------- 테마 전환 ---------- */
  const root = document.documentElement;
  const themeBtn = $("#theme-toggle");

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    const isDark = theme === "dark";
    themeBtn.firstElementChild.textContent = isDark ? "☀️" : "🌙";
    themeBtn.setAttribute("aria-label", isDark ? "라이트 테마로 전환" : "다크 테마로 전환");
    const meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", isDark ? "#0d1117" : "#ffffff");
  }

  applyTheme(root.getAttribute("data-theme") === "light" ? "light" : "dark");

  themeBtn.addEventListener("click", () => {
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("theme", next); } catch (e) { /* 저장 불가 시 무시 */ }
  });

  /* ---------- 모바일 메뉴 ---------- */
  const navToggle = $("#nav-toggle");
  const navMenu = $("#nav-menu");

  function setMenu(open) {
    navMenu.classList.toggle("open", open);
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  }

  navToggle.addEventListener("click", () => setMenu(!navMenu.classList.contains("open")));
  navMenu.addEventListener("click", (e) => { if (e.target.closest("a")) setMenu(false); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && navMenu.classList.contains("open")) {
      setMenu(false);
      navToggle.focus();
    }
  });

  /* ---------- 스크롤 등장 애니메이션 ---------- */
  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, obs) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("in-view");
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    $$(".reveal:not(.in-view)").forEach((node) => revealObserver.observe(node));
  } else {
    $$(".reveal").forEach((node) => node.classList.add("in-view"));
  }

  /* ---------- 현재 섹션 내비 강조 ---------- */
  const navLinks = $$('.nav-menu a[href^="#"]');
  const sections = navLinks
    .map((a) => $(a.getAttribute("href")))
    .filter(Boolean);

  function setActive(id) {
    navLinks.forEach((a) => {
      const active = a.getAttribute("href") === "#" + id;
      a.classList.toggle("active", active);
      if (active) a.setAttribute("aria-current", "true");
      else a.removeAttribute("aria-current");
    });
  }

  if ("IntersectionObserver" in window) {
    const sectionObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    sections.forEach((s) => sectionObserver.observe(s));

    // 히어로 영역에서는 강조 해제
    const hero = $("#home");
    if (hero) {
      new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) setActive("");
      }, { rootMargin: "-45% 0px -50% 0px" }).observe(hero);
    }
  }

  /* ---------- 이메일 복사 ---------- */
  $("#copy-email").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(EMAIL);
      showToast("이메일 주소가 복사되었습니다");
    } catch (e) {
      // 클립보드 API를 쓸 수 없는 환경(file:// 등) 대비: 선택 복사 → 실패 시 메일 앱 열기
      const ta = document.createElement("textarea");
      ta.value = EMAIL;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      let ok = false;
      try { ok = document.execCommand("copy"); } catch (err) { /* 무시 */ }
      ta.remove();
      if (ok) showToast("이메일 주소가 복사되었습니다");
      else window.location.href = "mailto:" + EMAIL;
    }
  });

  /* ---------- 히어로 터미널 타이핑 효과 ---------- */
  const term = $("#terminal-body");
  const script = [
    { type: "cmd", text: "whoami" },
    { type: "out", text: "최수나 (Suna Choi)" },
    { type: "cmd", text: "cat skills.txt" },
    { type: "out", text: "바이브코딩 · Python · HTML5" },
    { type: "cmd", text: "python snake.py --vs-ai" },
    { type: "out", text: "Game started. Good luck!" },
  ];

  function lineNode(item) {
    const line = document.createElement("span");
    if (item.type === "cmd") {
      const p = document.createElement("span");
      p.className = "prompt";
      p.textContent = "$ ";
      line.appendChild(p);
    } else {
      line.className = "out";
    }
    return line;
  }

  function renderTerminalStatic() {
    script.forEach((item) => {
      const line = lineNode(item);
      line.appendChild(document.createTextNode(item.text));
      term.appendChild(line);
      term.appendChild(document.createTextNode("\n"));
    });
  }

  function typeTerminal() {
    const cursor = document.createElement("span");
    cursor.className = "cursor";
    let i = 0;

    function nextLine() {
      if (i >= script.length) return;
      const item = script[i++];
      const line = lineNode(item);
      term.insertBefore(line, cursor.parentNode === term ? cursor : null);
      if (!cursor.parentNode) term.appendChild(cursor);

      if (item.type === "out") {
        line.appendChild(document.createTextNode(item.text));
        term.insertBefore(document.createTextNode("\n"), cursor);
        setTimeout(nextLine, 350);
        return;
      }
      let n = 0;
      const timer = setInterval(() => {
        line.appendChild(document.createTextNode(item.text[n++]));
        if (n >= item.text.length) {
          clearInterval(timer);
          term.insertBefore(document.createTextNode("\n"), cursor);
          setTimeout(nextLine, 300);
        }
      }, 55);
    }
    nextLine();
  }

  if (term) {
    if (reduceMotion) renderTerminalStatic();
    else setTimeout(typeTerminal, 500);
  }

  /* ---------- 푸터 연도 ---------- */
  const year = $("#year");
  if (year) year.textContent = new Date().getFullYear();
})();
