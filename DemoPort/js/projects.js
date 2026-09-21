// 프로젝트 데이터. 항목을 추가/수정하면 카드가 자동으로 갱신됩니다.
// demo / source 가 null 이면 해당 버튼은 표시되지 않습니다.
const projects = [
  {
    title: "뱀 게임 (Snake)",
    description: "사람이 조종하는 뱀과 AI 뱀이 사과를 두고 경쟁하는 대전형 게임. AI는 BFS로 사과까지의 최단 경로를 찾습니다.",
    tags: ["Python", "tkinter", "BFS"],
    demo: null,
    source: "projects/snake/snake.py",
    thumbnail: "assets/images/snake.svg",
    alt: "사람 뱀과 AI 뱀이 사과를 먹는 게임 화면",
    note: "실행: python snake.py",
  },
  {
    title: "테트리스",
    description: "홀드, 고스트 피스, 다음 블록 미리보기, 레벨 시스템을 갖춘 웹 테트리스.",
    tags: ["HTML5", "Canvas", "CSS3", "JavaScript"],
    demo: "projects/tetris/tetris.html",
    source: null,
    thumbnail: "assets/images/tetris.svg",
    alt: "색색의 블록이 쌓인 테트리스 화면",
  },
  {
    title: "종스크롤 슈팅 게임",
    description: "제비우스 스타일의 공중/지상 이중 공격 슈팅 게임입니다.",
    tags: ["HTML5", "Canvas", "JavaScript"],
    demo: null,
    source: null,
    thumbnail: "assets/images/shooter.svg",
    alt: "전투기가 적을 향해 발사하는 종스크롤 슈팅 게임 화면",
    status: "개발 예정",
  },
  {
    title: "개발자 프로필 사이트",
    description: "지금 보고 계신 이 웹사이트입니다. 다크/라이트 테마와 반응형 레이아웃을 지원합니다.",
    tags: ["HTML5", "CSS3", "JavaScript"],
    demo: null,
    source: null,
    thumbnail: "assets/images/site.svg",
    alt: "개발자 프로필 웹사이트 화면",
    status: "현재 페이지",
  },
];

// 필터 버튼 (태그와 일치하는 프로젝트만 표시)
const projectFilters = ["전체", "Python", "HTML5"];

(function () {
  "use strict";

  const grid = document.getElementById("project-grid");
  const filterBox = document.getElementById("project-filters");
  if (!grid || !filterBox) return;

  let current = "전체";

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function linkButton(label, href, className) {
    const a = el("a", "btn btn-sm " + className, label);
    a.href = href;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  }

  function createCard(p, instant) {
    const card = el("article", "card project-card reveal" + (instant ? " in-view" : ""));

    const thumb = el("div", "project-thumb");
    const img = document.createElement("img");
    img.src = p.thumbnail;
    img.alt = p.alt || p.title;
    img.width = 400;
    img.height = 240;
    img.loading = "lazy";
    thumb.appendChild(img);
    if (p.status) thumb.appendChild(el("span", "status-badge", p.status));
    card.appendChild(thumb);

    const body = el("div", "project-body");
    body.appendChild(el("h3", "", p.title));
    body.appendChild(el("p", "", p.description));

    const tags = el("ul", "tag-list");
    p.tags.forEach((t) => tags.appendChild(el("li", "tag", t)));
    body.appendChild(tags);

    const links = el("div", "project-links");
    if (p.demo) links.appendChild(linkButton("데모 보기", p.demo, "btn-primary"));
    if (p.source) links.appendChild(linkButton("소스 코드", p.source, "btn-outline"));
    if (p.note) links.appendChild(el("span", "tag", p.note));
    if (!p.demo && !p.source && p.status) {
      const disabled = el("span", "btn btn-sm btn-outline", p.status);
      disabled.setAttribute("aria-disabled", "true");
      links.appendChild(disabled);
    }
    body.appendChild(links);

    card.appendChild(body);
    return card;
  }

  function render(filter, instant) {
    current = filter;
    grid.textContent = "";
    const list = projects.filter((p) => filter === "전체" || p.tags.includes(filter));
    if (!list.length) {
      grid.appendChild(el("p", "empty", "해당하는 프로젝트가 없습니다."));
      return;
    }
    list.forEach((p) => grid.appendChild(createCard(p, instant)));
  }

  function renderFilters() {
    filterBox.textContent = "";
    projectFilters.forEach((name) => {
      const btn = el("button", "filter-btn", name);
      btn.type = "button";
      btn.setAttribute("aria-pressed", String(name === current));
      btn.addEventListener("click", () => {
        if (name === current) return;
        render(name, true);
        renderFilters();
      });
      filterBox.appendChild(btn);
    });
  }

  render(current, false);
  renderFilters();
})();
