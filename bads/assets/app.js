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
    text.innerHTML = 'Get Urban Concierge as an app: tap <strong>Share</strong> <span aria-hidden="true">&#x2191;</span> in Safari, then <strong>Add to Home Screen</strong>.';
    btn.hidden = true;
    box.hidden = false;
    return;
  }

  var deferred = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    text.textContent = "Install Urban Concierge on your phone or desktop for one-tap access and offline reading.";
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

/* Bay Area scores ticker: live / recent finals / upcoming times from ESPN's public scoreboard API. */
(function () {
  var track = document.getElementById("scores-track");
  var sr = document.getElementById("scores-sr");
  if (!track) return;

  var ESPN = "https://site.api.espn.com/apis/site/v2/sports/";
  var TZ = "America/Los_Angeles";
  var FEEDS = [
    { path: "basketball/nba/teams/9/schedule", sport: "basketball/nba", id: "9", kind: "NBA" },
    { path: "basketball/wnba/teams/129689/schedule", sport: "basketball/wnba", id: "129689", kind: "WNBA" },
    { path: "football/nfl/teams/25/schedule", sport: "football/nfl", id: "25", kind: "NFL" },
    { path: "baseball/mlb/teams/26/schedule", sport: "baseball/mlb", id: "26", kind: "MLB" },
    { path: "baseball/mlb/teams/11/schedule", sport: "baseball/mlb", id: "11", kind: "MLB" },
    { path: "hockey/nhl/teams/18/schedule", sport: "hockey/nhl", id: "18", kind: "NHL" },
    { path: "soccer/usa.1/teams/191/schedule", sport: "soccer/usa.1", id: "191", kind: "MLS" },
    { path: "soccer/usa.nwsl/teams/22187/schedule", sport: "soccer/usa.nwsl", id: "22187", kind: "NWSL" },
    { path: "football/college-football/teams/24/schedule", sport: "football/college-football", id: "24", kind: "Football" },
    { path: "football/college-football/teams/25/schedule", sport: "football/college-football", id: "25", kind: "Football" },
    { path: "football/college-football/teams/23/schedule", sport: "football/college-football", id: "23", kind: "Football" },
    { path: "basketball/mens-college-basketball/teams/24/schedule", sport: "basketball/mens-college-basketball", id: "24", kind: "Men" },
    { path: "basketball/mens-college-basketball/teams/25/schedule", sport: "basketball/mens-college-basketball", id: "25", kind: "Men" },
    { path: "basketball/mens-college-basketball/teams/23/schedule", sport: "basketball/mens-college-basketball", id: "23", kind: "Men" },
    { path: "basketball/mens-college-basketball/teams/2608/schedule", sport: "basketball/mens-college-basketball", id: "2608", kind: "Men" },
    { path: "basketball/mens-college-basketball/teams/2539/schedule", sport: "basketball/mens-college-basketball", id: "2539", kind: "Men" },
    { path: "basketball/mens-college-basketball/teams/2541/schedule", sport: "basketball/mens-college-basketball", id: "2541", kind: "Men" },
    { path: "basketball/womens-college-basketball/teams/24/schedule", sport: "basketball/womens-college-basketball", id: "24", kind: "Women" },
    { path: "basketball/womens-college-basketball/teams/25/schedule", sport: "basketball/womens-college-basketball", id: "25", kind: "Women" },
    { path: "basketball/womens-college-basketball/teams/23/schedule", sport: "basketball/womens-college-basketball", id: "23", kind: "Women" },
    { path: "basketball/womens-college-basketball/teams/2608/schedule", sport: "basketball/womens-college-basketball", id: "2608", kind: "Women" },
    { path: "basketball/womens-college-basketball/teams/2539/schedule", sport: "basketball/womens-college-basketball", id: "2539", kind: "Women" },
    { path: "basketball/womens-college-basketball/teams/2541/schedule", sport: "basketball/womens-college-basketball", id: "2541", kind: "Women" }
  ];
  var LABELS = {
    "basketball/nba": { "9": "Warriors" },
    "basketball/wnba": { "129689": "Valkyries" },
    "football/nfl": { "25": "49ers" },
    "baseball/mlb": { "26": "Giants", "11": "Athletics (Sacramento)" },
    "hockey/nhl": { "18": "Sharks" },
    "soccer/usa.1": { "191": "Earthquakes" },
    "soccer/usa.nwsl": { "22187": "Bay FC" },
    "football/college-football": { "24": "Stanford", "25": "Cal", "23": "San José State" },
    "basketball/mens-college-basketball": { "24": "Stanford", "25": "Cal", "23": "San José State", "2608": "Saint Mary's", "2539": "USF", "2541": "Santa Clara" },
    "basketball/womens-college-basketball": { "24": "Stanford", "25": "Cal", "23": "San José State", "2608": "Saint Mary's", "2539": "USF", "2541": "Santa Clara" }
  };
  var COLLEGE_KINDS = { Football: 1, Men: 1, Women: 1 };
  var timer = null;

  function ptYmd(d) {
    return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
  }
  function isYesterdayOrToday(d) {
    var g = ptYmd(d), today = ptYmd(new Date());
    var yest = ptYmd(new Date(Date.now() - 24 * 60 * 60 * 1000));
    return g === today || g === yest;
  }
  function isTodayOrTomorrow(d) {
    var g = ptYmd(d), today = ptYmd(new Date());
    var tom = ptYmd(new Date(Date.now() + 24 * 60 * 60 * 1000));
    return g === today || g === tom;
  }
  function formatWhen(iso, timeValid) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var weekday = new Intl.DateTimeFormat("en-US", { timeZone: TZ, weekday: "short" }).format(d);
    if (timeValid === false) return weekday + " " + new Intl.DateTimeFormat("en-US", { timeZone: TZ, month: "short", day: "numeric" }).format(d) + " (time TBD)";
    var time = new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" }).format(d);
    var today = ptYmd(new Date()), g = ptYmd(d);
    if (g === today) return "Today " + time + " PT";
    return weekday + " " + time + " PT";
  }
  function scoreOf(c) {
    var s = c && c.score;
    if (s == null) return "";
    if (typeof s === "object") {
      if (s.displayValue != null && s.displayValue !== "") return String(s.displayValue);
      if (s.value != null && s.value !== "") return String(s.value);
      return "";
    }
    return String(s);
  }
  function teamName(sport, team) {
    var id = String((team && team.id) || "");
    var map = LABELS[sport] || {};
    if (map[id]) return map[id];
    if (!team) return "TBD";
    return team.shortDisplayName || team.nickname || team.displayName || team.abbreviation || "TBD";
  }
  function normalizeState(type) {
    type = type || {};
    var state = (type.state || "").toLowerCase();
    var desc = (type.shortDetail || type.detail || type.description || "");
    if (state === "in") return { key: "live", label: desc || "Live" };
    if (state === "post") {
      var lab = desc || "Final";
      if (/^ft$|^full[- ]?time$/i.test(lab)) lab = "Final";
      return { key: "final", label: lab };
    }
    return { key: "pre", label: desc };
  }

  function parseEvent(ev, sport, kind) {
    var comp = (ev.competitions && ev.competitions[0]) || ev;
    var status = normalizeState((comp.status || ev.status || {}).type);
    var competitors = (comp.competitors || []).slice();
    if (competitors.length < 2) return null;
    var ours = [];
    competitors.forEach(function (c) {
      var id = String((c.team || {}).id || c.id || "");
      if ((LABELS[sport] || {})[id]) ours.push(c);
    });
    if (!ours.length) return null;
    // Watched team first; if both are Bay Area teams and the game is scored, winner first.
    var left;
    if (ours.length === 1) {
      left = ours[0];
    } else {
      var s0 = Number(scoreOf(ours[0])), s1 = Number(scoreOf(ours[1]));
      if (scoreOf(ours[0]) !== "" && scoreOf(ours[1]) !== "" && s0 !== s1) {
        left = s0 > s1 ? ours[0] : ours[1];
      } else {
        left = ours.filter(function (c) { return c.homeAway === "home"; })[0] || ours[0];
      }
    }
    var right = competitors.filter(function (c) { return c !== left; })[0];
    var dateIso = comp.date || ev.date;
    var when = new Date(dateIso);
    if (isNaN(when.getTime())) return null;
    return {
      id: String(comp.id || ev.id || (dateIso + sport + kind)),
      sport: sport,
      kind: kind,
      status: status.key,
      statusLabel: status.label,
      date: when,
      timeValid: comp.timeValid !== false,
      leftName: teamName(sport, left.team),
      rightName: teamName(sport, right && right.team),
      leftScore: scoreOf(left),
      rightScore: scoreOf(right)
    };
  }

  function inWindow(g) {
    var now = Date.now();
    if (g.status === "live") return true;
    if (g.status === "final") return isYesterdayOrToday(g.date);
    if (g.status === "pre") return isTodayOrTomorrow(g.date) && g.date.getTime() >= now - 2 * 60 * 60 * 1000;
    return false;
  }

  function rank(g) {
    if (g.status === "live") return 0;
    if (g.status === "final") return 1;
    return 2;
  }

  function matchText(g) {
    if (g.status === "pre") return g.leftName + " vs " + g.rightName;
    return g.leftName + " " + g.leftScore + "–" + g.rightScore + " " + g.rightName;
  }

  function itemParts(g) {
    var state = g.status === "live" ? "LIVE" : (g.status === "final" ? g.statusLabel : "");
    var when = g.status === "pre" ? formatWhen(g.date.toISOString(), g.timeValid) : (g.status === "live" ? g.statusLabel : "");
    var kind = COLLEGE_KINDS[g.kind] ? g.kind : "";
    return { state: state, live: g.status === "live", match: matchText(g), kind: kind, when: when, spoken: spoken(g, state, when, kind) };
  }
  function spoken(g, state, when, kind) {
    var bits = [];
    if (state) bits.push(state);
    bits.push(matchText(g));
    if (kind) bits.push(kind);
    if (when && g.status !== "live") bits.push(when);
    else if (g.status === "live" && g.statusLabel) bits.push(g.statusLabel);
    return bits.join(", ");
  }

  function renderItems(games) {
    var parts = games.map(itemParts);
    track.textContent = "";
    track.style.animation = "none";
    if (!parts.length) {
      var empty = document.createElement("p");
      empty.className = "scores-status";
      empty.textContent = "No Bay Area games right now";
      track.appendChild(empty);
      if (sr) sr.textContent = "No Bay Area games right now";
      return;
    }
    function fill(into) {
      parts.forEach(function (p) {
        var item = document.createElement("div");
        item.className = "score-item";
        if (p.state) {
          var st = document.createElement("span");
          st.className = "state" + (p.live ? " live" : "");
          st.textContent = p.state;
          item.appendChild(st);
        }
        var match = document.createElement("span");
        match.className = "match";
        match.textContent = p.match;
        item.appendChild(match);
        if (p.kind) {
          var kind = document.createElement("span");
          kind.className = "kind";
          kind.textContent = p.kind;
          item.appendChild(kind);
        }
        if (p.when) {
          var when = document.createElement("span");
          when.className = "when";
          when.textContent = p.when;
          item.appendChild(when);
        }
        into.appendChild(item);
      });
    }
    var copy = document.createElement("div");
    copy.className = "scores-copy";
    fill(copy);
    track.appendChild(copy);
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var viewport = document.getElementById("scores-viewport");
    var needsScroll = !reduce && viewport && copy.scrollWidth > viewport.clientWidth;
    if (!needsScroll && !reduce && viewport && copy.scrollWidth > 0) {
      // Still scroll if a few items would otherwise sit still; duplicate only when animating.
      needsScroll = parts.length >= 4;
    }
    if (needsScroll) {
      var copy2 = copy.cloneNode(true);
      copy2.setAttribute("aria-hidden", "true");
      track.appendChild(copy2);
      var duration = Math.max(28, parts.length * 5);
      track.style.setProperty("--scores-duration", duration + "s");
      // Force restart of the animation after content swap.
      void track.offsetWidth;
      track.style.animation = "";
    }
    if (sr) sr.textContent = parts.map(function (p) { return p.spoken; }).join(". ");
  }

  function showMessage(msg) {
    track.textContent = "";
    track.style.animation = "none";
    var p = document.createElement("p");
    p.className = "scores-status";
    p.textContent = msg;
    track.appendChild(p);
    if (sr) sr.textContent = msg;
  }

  function load() {
    var results = Promise.all(FEEDS.map(function (feed) {
      return fetch(ESPN + feed.path, { cache: "no-store" }).then(function (res) {
        if (!res.ok) throw new Error("espn " + res.status);
        return res.json();
      }).then(function (data) {
        return { feed: feed, events: data.events || [], ok: true };
      }).catch(function () {
        return { feed: feed, events: [], ok: false };
      });
    }));

    results.then(function (rows) {
      var ok = 0, failed = 0;
      var byId = {};
      rows.forEach(function (row) {
        if (row.ok) ok += 1; else failed += 1;
        (row.events || []).forEach(function (ev) {
          var g = parseEvent(ev, row.feed.sport, row.feed.kind);
          if (!g || !inWindow(g)) return;
          var prev = byId[g.id];
          if (!prev) byId[g.id] = g;
        });
      });
      if (!ok) {
        showMessage("Scores unavailable");
        scheduleNext(false);
        return;
      }
      var games = [];
      Object.keys(byId).forEach(function (k) { games.push(byId[k]); });
      games.sort(function (a, b) {
        var r = rank(a) - rank(b);
        if (r) return r;
        return a.date.getTime() - b.date.getTime();
      });
      renderItems(games);
      var live = games.some(function (g) { return g.status === "live"; });
      scheduleNext(live);
    }).catch(function () {
      showMessage("Scores unavailable");
      scheduleNext(false);
    });
  }

  function scheduleNext(live) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(load, live ? 60 * 1000 : 3 * 60 * 1000);
  }

  load();
})();

/* Email signup: POST to the Worker in site.json signup.form_action. */
(function () {
  var f = document.getElementById("bads-signup"); if (!f) return;
  var i = document.getElementById("bads-email");
  var m = document.getElementById("signup-msg");
  var hp = document.getElementById("bads-company");
  f.addEventListener("submit", function (e) {
    e.preventDefault();
    m.textContent = "";
    m.className = "signup-msg";
    var email = (i.value || "").trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      m.textContent = "Please enter a valid email address.";
      m.className = "signup-msg err";
      i.focus();
      return;
    }
    var endpoint = f.getAttribute("data-endpoint");
    if (!endpoint) {
      m.textContent = "Signup is not available right now.";
      m.className = "signup-msg err";
      return;
    }
    var btn = f.querySelector("button[type=submit]");
    if (btn) btn.disabled = true;
    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email,
        company: hp ? hp.value : "",
        source: "bads"
      })
    }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, data: data };
      }).catch(function () { return { ok: res.ok, data: {} }; });
    }).then(function (r) {
      if (r.ok && r.data && r.data.ok) {
        m.textContent = "You're on the list.";
        m.className = "signup-msg ok";
        f.reset();
      } else {
        m.textContent = (r.data && r.data.error) || "Something went wrong. Please try again.";
        m.className = "signup-msg err";
      }
    }).catch(function () {
      m.textContent = "Something went wrong. Please try again.";
      m.className = "signup-msg err";
    }).finally(function () { if (btn) btn.disabled = false; });
  });
})();
