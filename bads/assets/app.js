/* BADS app helpers: fold the latest brief, service worker, install hint. */
(function () {
  var root = document.documentElement.getAttribute("data-root") || "./";
  foldBrief(root);
  eventStrip();
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(root + "sw.js", { scope: root }).catch(function () {});
    });
  }

  var standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  var box = document.getElementById("install-hint");
  if (!box || standalone) return;
  var dismissed = false;
  try { dismissed = localStorage.getItem("bads-install-dismissed") === "1"; } catch (e) {}
  if (dismissed) return;

  var text = box.querySelector(".install-text");
  var btn = box.querySelector(".install-btn");
  var close = box.querySelector(".install-close");
  close.addEventListener("click", function () {
    box.hidden = true;
    try { localStorage.setItem("bads-install-dismissed", "1"); } catch (e) {}
  });

  var ua = navigator.userAgent || "";
  var isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (isIOS) {
    text.innerHTML = 'Get BADS as an app: tap <strong>Share</strong> <span aria-hidden="true">&#x2191;</span> in Safari, then <strong>Add to Home Screen</strong>.';
    btn.hidden = true;
    box.hidden = false;
    return;
  }

  var deferred = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    text.textContent = "Install BADS on your phone or desktop for one-tap access and offline reading.";
    btn.hidden = false;
    box.hidden = false;
  });
  btn.addEventListener("click", function () {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.finally(function () { deferred = null; box.hidden = true; });
  });
  window.addEventListener("appinstalled", function () { box.hidden = true; });
})();

function foldBrief(root) {
  if (root.indexOf("..") === 0) return;
  var article = document.querySelector("main article.brief");
  if (!article || article.classList.contains("v2") || article.getAttribute("data-folded") === "1") return; // v2 = events-first layout, built server-side
  article.setAttribute("data-folded", "1");

  var hero = document.createElement("figure");
  hero.className = "hero-photo";
  var img = document.createElement("img");
  img.src = "/assets/bay.jpg";
  img.alt = "San Francisco Bay at dusk, from above the Bay Bridge looking toward the Golden Gate";
  img.width = 1792;
  img.height = 1008;
  img.addEventListener("error", function () { hero.remove(); });
  hero.appendChild(img);
  article.parentNode.insertBefore(hero, article);

  var nodes = Array.prototype.slice.call(article.childNodes);
  var intro = document.createElement("div");
  intro.className = "brief-intro";
  var sections = [];
  var current = null;
  nodes.forEach(function (node) {
    var isH2 = node.nodeType === 1 && node.tagName === "H2";
    if (isH2) {
      current = { title: node.textContent.replace(/\s+/g, " ").trim(), nodes: [node] };
      sections.push(current);
      return;
    }
    if (!current && node.nodeType === 1 && node.tagName === "HR") return;
    if (current) current.nodes.push(node);
    else intro.appendChild(node);
  });

  var ORDER = ["What's on", "Eat", "Weather", "Traffic", "Getting around", "Stay", "Notes", "Unchecked"];
  function rank(sec) { var k = ORDER.indexOf(pillLabel(sec.title)); return k < 0 ? ORDER.length : k; }
  sections = sections.map(function (sec, i) { return { sec: sec, i: i }; })
    .sort(function (a, b) { return rank(a.sec) - rank(b.sec) || a.i - b.i; })
    .map(function (x) { return x.sec; });

  article.textContent = "";
  article.appendChild(intro);

  var nav = document.createElement("div");
  nav.className = "pills";
  nav.setAttribute("role", "tablist");
  nav.setAttribute("aria-label", "Brief sections");
  var panels = sections.map(function (sec, i) {
    var panel = document.createElement("section");
    panel.className = "pill-panel";
    panel.hidden = true;
    panel.id = "pill-panel-" + i;
    sec.nodes.forEach(function (node) { panel.appendChild(node); });
    article.appendChild(panel);
    return panel;
  });

  var open = -1;
  sections.forEach(function (sec, i) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "pill";
    button.textContent = pillLabel(sec.title);
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("aria-controls", panels[i].id);
    button.addEventListener("click", function () {
      open = open === i ? -1 : i;
      panels.forEach(function (panel, j) {
        var on = j === open;
        panel.hidden = !on;
        nav.children[j].classList.toggle("on", on);
        nav.children[j].setAttribute("aria-selected", on ? "true" : "false");
      });
      if (open < 0) return;
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      panels[open].scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "nearest" });
    });
    nav.appendChild(button);
  });
  intro.after(nav);
}

function pillLabel(title) {
  var t = title.toLowerCase();
  if (t.indexOf("weather") >= 0) return "Weather";
  if (t.indexOf("road") >= 0 || t.indexOf("traffic") >= 0) return "Traffic";
  if (t.indexOf("what") >= 0) return "What's on";
  if (t.indexOf("eat") >= 0) return "Eat";
  if (t.indexOf("getting") >= 0) return "Getting around";
  if (t.indexOf("stay") >= 0) return "Stay";
  if (t.indexOf("assumption") >= 0) return "Notes";
  if (t.indexOf("verified") >= 0) return "Unchecked";
  return title.length > 18 ? title.slice(0, 16) + "…" : title;
}

/* Events strip: arrows + drag-to-scroll on desktop; native swipe on touch. */
function eventStrip() {
  var list = document.querySelector(".brief.v2 .ev-grid");
  if (!list) return;
  var wrap = document.createElement("div");
  wrap.className = "ev-strip";
  list.parentNode.insertBefore(wrap, list);
  wrap.appendChild(list);
  function mk(cls, label, txt, dir) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "ev-arrow " + cls; b.setAttribute("aria-label", label); b.innerHTML = txt;
    b.addEventListener("click", function () {
      var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      list.scrollBy({ left: dir * list.clientWidth * 0.85, behavior: reduce ? "auto" : "smooth" });
    });
    wrap.appendChild(b); return b;
  }
  var prev = mk("prev", "Previous events", "&#8249;", -1), next = mk("next", "More events", "&#8250;", 1);
  function update() {
    prev.disabled = list.scrollLeft < 4;
    next.disabled = list.scrollLeft + list.clientWidth >= list.scrollWidth - 4;
  }
  list.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  update();
  var down = false, x0 = 0, s0 = 0, moved = false;
  list.addEventListener("pointerdown", function (e) {
    if (e.pointerType !== "mouse") return;
    down = true; moved = false; x0 = e.clientX; s0 = list.scrollLeft;
  });
  window.addEventListener("pointermove", function (e) {
    if (!down) return;
    var dx = e.clientX - x0;
    if (Math.abs(dx) > 5) { moved = true; list.classList.add("dragging"); }
    if (moved) { list.scrollLeft = s0 - dx; e.preventDefault(); }
  });
  window.addEventListener("pointerup", function () { down = false; list.classList.remove("dragging"); });
  list.addEventListener("click", function (e) { if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
  list.addEventListener("dragstart", function (e) { e.preventDefault(); });
}
