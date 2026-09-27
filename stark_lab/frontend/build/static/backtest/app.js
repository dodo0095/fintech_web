/* 策略回測實驗室 — 前端（無框架）
 * 策略狀態 = 後端同一份 JSON schema（backtest/engine/rules.py）
 */
(function () {
  "use strict";

  const META = JSON.parse(document.getElementById("bt-meta").textContent);
  const IND = META.indicators;
  const OPS = META.operators;
  const MAX_CONDS = 8;
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const state = {
    symbol: "",          // 使用者選到的代號（或輸入的文字）
    stockLabel: "",
    strategy: null,
    presetId: null,
  };

  // ------------------------------------------------------------ 工具
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
  function el(tag, attrs, children) {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === "text") n.textContent = v;
      else if (k === "class") n.className = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else if (v !== undefined && v !== null && v !== false) n.setAttribute(k, v);
    });
    (children || []).forEach((c) => c && n.appendChild(c));
    return n;
  }
  function getCookie(name) {
    const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }
  function fmtPct(v, sign) {
    if (v === null || v === undefined) return "—";
    return (sign && v > 0 ? "+" : "") + Number(v).toFixed(2) + "%";
  }
  function fmtNum(v, nd) {
    if (v === null || v === undefined) return "—";
    return Number(v).toLocaleString("zh-TW", { minimumFractionDigits: nd || 0, maximumFractionDigits: nd || 0 });
  }
  function cls(v) { return v > 0 ? "pos" : v < 0 ? "neg" : ""; }
  function isoDate(d) {
    const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return z.toISOString().slice(0, 10);
  }
  function b64encode(str) { return btoa(unescape(encodeURIComponent(str))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""); }
  function b64decode(s) {
    s = s.replace(/-/g, "+").replace(/_/g, "/");
    while (s.length % 4) s += "=";
    return decodeURIComponent(escape(atob(s)));
  }

  // ------------------------------------------------------------ 運算元
  function defaultParams(name) {
    const out = {};
    (IND[name].params || []).forEach((p) => { out[p.key] = p.default; });
    return out;
  }
  function indOperand(name, params) {
    return { kind: "ind", name: name, params: Object.assign(defaultParams(name), params || {}), mult: 1 };
  }
  function normalizeOperand(o) {
    if (!o || o.kind === "num") return { kind: "num", value: o ? o.value : 0 };
    if (!IND[o.name]) return indOperand("close");
    return { kind: "ind", name: o.name, params: Object.assign(defaultParams(o.name), o.params || {}), mult: o.mult || 1 };
  }
  function normalizeStrategy(s) {
    s = clone(s || {});
    const blk = (b, logic) => ({
      logic: (b && b.logic) || logic,
      conditions: ((b && b.conditions) || []).slice(0, MAX_CONDS).map((c) => ({
        left: normalizeOperand(c.left), op: OPS[c.op] ? c.op : "gt", right: normalizeOperand(c.right),
      })),
    });
    return { entry: blk(s.entry, "all"), exit: blk(s.exit, "any"), risk: Object.assign({}, s.risk || {}) };
  }

  function indicatorSelect(current, allowNum) {
    const sel = el("select", { "aria-label": "指標" });
    if (allowNum) sel.appendChild(el("option", { value: "__num", text: "數值" }));
    const groups = {};
    Object.entries(IND).forEach(([key, spec]) => {
      if (!groups[spec.group]) {
        groups[spec.group] = el("optgroup", { label: spec.group });
        sel.appendChild(groups[spec.group]);
      }
      groups[spec.group].appendChild(el("option", { value: key, text: spec.label }));
    });
    sel.value = current;
    return sel;
  }

  function renderOperand(op, side, onChange) {
    const wrap = el("span", { class: "operand" });
    const isNum = op.kind === "num";
    const sel = indicatorSelect(isNum ? "__num" : op.name, side === "right");
    sel.addEventListener("change", () => {
      if (sel.value === "__num") onChange({ kind: "num", value: 0 }, true);
      else onChange(indOperand(sel.value), true);
    });
    wrap.appendChild(sel);

    if (isNum) {
      const inp = el("input", { type: "number", step: "any", value: op.value, "aria-label": "數值" });
      inp.addEventListener("input", () => { op.value = inp.value === "" ? "" : Number(inp.value); });
      wrap.appendChild(inp);
      return wrap;
    }
    (IND[op.name].params || []).forEach((p) => {
      wrap.appendChild(el("span", { class: "p-label", text: p.label }));
      const inp = el("input", {
        type: "number", min: p.min, max: p.max, step: p.step, value: op.params[p.key], "aria-label": p.label,
      });
      inp.addEventListener("input", () => { op.params[p.key] = inp.value === "" ? "" : Number(inp.value); });
      wrap.appendChild(inp);
    });
    if (side === "right") {
      wrap.appendChild(el("span", { class: "p-label", text: "×" }));
      const m = el("input", { type: "number", min: 0.01, max: 100, step: 0.05, value: op.mult || 1, "aria-label": "倍數", title: "倍數，例如 1.5 = 1.5 倍" });
      m.addEventListener("input", () => { op.mult = m.value === "" ? 1 : Number(m.value); });
      wrap.appendChild(m);
    }
    return wrap;
  }

  function renderBlock(blockEl, block) {
    const list = $("[data-conds]", blockEl);
    list.innerHTML = "";
    $("[data-logic]", blockEl).value = block.logic;
    if (!block.conditions.length) {
      list.appendChild(el("p", { class: "empty-note", text: blockEl.id === "exit-block"
        ? "沒有賣出條件：只靠下方風險控制出場。" : "請新增至少一條買進條件。" }));
    }
    block.conditions.forEach((c, i) => {
      const row = el("div", { class: "cond" });
      const rerender = () => renderBlock(blockEl, block);
      row.appendChild(renderOperand(c.left, "left", (nv) => { c.left = nv; markCustom(); rerender(); }));
      const opSel = el("select", { class: "op", "aria-label": "比較方式" });
      Object.entries(OPS).forEach(([k, label]) => opSel.appendChild(el("option", { value: k, text: label })));
      opSel.value = c.op;
      opSel.addEventListener("change", () => { c.op = opSel.value; markCustom(); });
      row.appendChild(opSel);
      row.appendChild(renderOperand(c.right, "right", (nv) => { c.right = nv; markCustom(); rerender(); }));
      row.appendChild(el("button", {
        type: "button", class: "del", title: "刪除條件", "aria-label": "刪除條件", text: "×",
        onclick: () => { block.conditions.splice(i, 1); markCustom(); rerender(); },
      }));
      row.addEventListener("input", markCustom);
      list.appendChild(row);
    });
    $("[data-add]", blockEl).disabled = block.conditions.length >= MAX_CONDS;
  }

  function renderRisk() {
    const box = $("#risk-fields");
    box.innerHTML = "";
    Object.entries(META.risk_fields).forEach(([key, f]) => {
      const id = "risk-" + key;
      const inp = el("input", {
        id: id, type: "number", min: f.min, max: f.max, step: key === "max_hold_days" ? 1 : 0.5,
        placeholder: "不使用", value: state.strategy.risk[key] || "",
      });
      inp.addEventListener("input", () => {
        state.strategy.risk[key] = inp.value === "" ? null : Number(inp.value);
        markCustom();
      });
      box.appendChild(el("div", { class: "field" }, [el("label", { for: id, text: f.label }), inp]));
    });
  }

  function renderStrategy() {
    renderBlock($("#entry-block"), state.strategy.entry);
    renderBlock($("#exit-block"), state.strategy.exit);
    renderRisk();
    $$("#presets button").forEach((b) => b.classList.toggle("on", b.dataset.id === state.presetId));
  }

  function markCustom() {
    if (state.presetId) {
      state.presetId = null;
      $$("#presets button").forEach((b) => b.classList.remove("on"));
    }
  }

  function applyPreset(p) {
    state.strategy = normalizeStrategy(p.strategy);
    state.presetId = p.id;
    renderStrategy();
  }

  function initBuilder() {
    const box = $("#presets");
    META.presets.forEach((p) => {
      box.appendChild(el("button", { type: "button", "data-id": p.id, title: p.desc, text: p.name, onclick: () => applyPreset(p) }));
    });
    [["#entry-block", "entry"], ["#exit-block", "exit"]].forEach(([sel, key]) => {
      const blockEl = $(sel);
      $("[data-logic]", blockEl).addEventListener("change", (e) => { state.strategy[key].logic = e.target.value; markCustom(); });
      $("[data-add]", blockEl).addEventListener("click", () => {
        const b = state.strategy[key];
        if (b.conditions.length >= MAX_CONDS) return;
        b.conditions.push({ left: indOperand("close"), op: key === "entry" ? "gt" : "lt", right: indOperand("sma", { period: 20 }) });
        markCustom();
        renderBlock(blockEl, b);
      });
    });
  }

  // ------------------------------------------------------------ 股票搜尋
  function initStockSearch() {
    const input = $("#stock-input");
    const list = $("#stock-list");
    const picked = $("#stock-picked");
    let items = [];
    let active = -1;
    let timer = null;
    let seq = 0;

    function close() { list.hidden = true; input.setAttribute("aria-expanded", "false"); active = -1; }
    function choose(it) {
      state.symbol = it.code;
      state.stockLabel = it.code + " " + it.name;
      input.value = it.code + " " + it.name;
      picked.textContent = "已選：" + it.code + " " + it.name + (it.market ? "（" + it.market + "）" : "");
      picked.className = "hint ok";
      close();
    }
    function draw() {
      list.innerHTML = "";
      items.forEach((it, i) => {
        const li = el("li", { role: "option", id: "opt-" + i, "aria-selected": i === active ? "true" : "false" }, [
          el("b", { text: it.code }), el("span", { text: it.name }), el("small", { text: it.market }),
        ]);
        li.addEventListener("mousedown", (e) => { e.preventDefault(); choose(it); });
        list.appendChild(li);
      });
      list.hidden = !items.length;
      input.setAttribute("aria-expanded", items.length ? "true" : "false");
      if (active >= 0) input.setAttribute("aria-activedescendant", "opt-" + active);
    }
    input.addEventListener("input", () => {
      state.symbol = input.value.trim();
      state.stockLabel = state.symbol;  // 沒從清單選時，分享連結的標籤要跟著變
      picked.textContent = "";
      picked.className = "hint";
      clearTimeout(timer);
      const q = input.value.trim();
      if (!q) { items = []; draw(); return; }
      timer = setTimeout(() => {
        const my = ++seq;
        fetch("/backtest/api/search?q=" + encodeURIComponent(q))
          .then((r) => r.json())
          .then((d) => { if (my !== seq) return; items = d.results || []; active = items.length ? 0 : -1; draw(); })
          .catch(() => {});
      }, 150);
    });
    input.addEventListener("keydown", (e) => {
      if (list.hidden) return;
      if (e.key === "ArrowDown") { active = Math.min(items.length - 1, active + 1); draw(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { active = Math.max(0, active - 1); draw(); e.preventDefault(); }
      else if (e.key === "Enter" && active >= 0) { choose(items[active]); e.preventDefault(); }
      else if (e.key === "Escape") close();
    });
    input.addEventListener("blur", () => setTimeout(close, 120));
    return { choose: choose };
  }

  // ------------------------------------------------------------ 日期
  function setRange(years) {
    const end = new Date();
    let start;
    if (years === "all") start = new Date(META.earliest);
    else { start = new Date(end); start.setFullYear(end.getFullYear() - Number(years)); }
    $("#start").value = isoDate(start);
    $("#end").value = isoDate(end);
    $$("#range-chips button").forEach((b) => b.classList.toggle("on", b.dataset.years === String(years)));
  }
  function initDates() {
    $("#start").min = META.earliest; $("#end").min = META.earliest;
    $("#start").max = META.today; $("#end").max = META.today;
    $$("#range-chips button").forEach((b) => b.addEventListener("click", () => setRange(b.dataset.years)));
    ["#start", "#end"].forEach((s) => $(s).addEventListener("change", () => $$("#range-chips button").forEach((b) => b.classList.remove("on"))));
    setRange(5);
  }

  // ------------------------------------------------------------ 送出
  function collectPayload() {
    return {
      symbol: state.symbol,
      start: $("#start").value,
      end: $("#end").value,
      strategy: state.strategy,
      settings: {
        capital: Number($("#capital").value) || 1000000,
        fee_discount: Number($("#fee_discount").value),
        slippage_pct: $("#slippage_pct").value === "" ? 0.1 : Number($("#slippage_pct").value),
        board_lot: $("#board_lot").value === "1",
      },
    };
  }

  function showError(msg) {
    const e = $("#form-error");
    e.textContent = msg || "";
    e.hidden = !msg;
  }

  function run() {
    showError("");
    if (!state.symbol) { showError("請先選擇股票"); $("#stock-input").focus(); return; }
    if (!state.strategy.entry.conditions.length) { showError("請至少新增一條買進條件"); return; }
    const payload = collectPayload();
    const btn = $("#run-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>回測中…';
    fetch("/backtest/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
      credentials: "same-origin",
      body: JSON.stringify(payload),
    })
      .then((r) => r.json().catch(() => ({ ok: false, error: "伺服器回應異常（" + r.status + "）" })))
      .then((d) => {
        if (!d.ok) { showError(d.error || "回測失敗"); return; }
        saveHash(payload);
        renderResult(d);
      })
      .catch(() => showError("網路連線失敗，請稍後再試"))
      .finally(() => { btn.disabled = false; btn.textContent = "開始回測"; });
  }

  // ------------------------------------------------------------ 分享連結
  function saveHash(payload) {
    const data = { s: payload.symbol, l: state.stockLabel, a: payload.start, b: payload.end, st: payload.strategy, cfg: payload.settings };
    try { history.replaceState(null, "", "#r=" + b64encode(JSON.stringify(data))); } catch (e) { /* ignore */ }
  }
  function loadHash(stock) {
    const m = location.hash.match(/#r=([A-Za-z0-9_-]+)/);
    if (!m) return false;
    try {
      const d = JSON.parse(b64decode(m[1]));
      state.strategy = normalizeStrategy(d.st);
      state.presetId = null;
      if (d.s) {
        const label = d.l || d.s;
        state.symbol = d.s;
        state.stockLabel = label;
        $("#stock-input").value = label;
        $("#stock-picked").textContent = "已選：" + label;
        $("#stock-picked").className = "hint ok";
      }
      if (d.a) $("#start").value = d.a;
      if (d.b) $("#end").value = d.b;
      $$("#range-chips button").forEach((b) => b.classList.remove("on"));
      if (d.cfg) {
        if (d.cfg.capital) $("#capital").value = d.cfg.capital;
        if (d.cfg.fee_discount !== undefined) $("#fee_discount").value = String(d.cfg.fee_discount);
        if (d.cfg.slippage_pct !== undefined) $("#slippage_pct").value = d.cfg.slippage_pct;
        $("#board_lot").value = d.cfg.board_lot ? "1" : "0";
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  // ------------------------------------------------------------ 結果
  let charts = [];

  function kpi(label, value, sub, colorVal) {
    return '<div class="kpi"><span>' + esc(label) + '</span><strong class="' + (colorVal === undefined ? "" : cls(colorVal)) + '">' +
      esc(value) + "</strong>" + (sub ? "<small>" + esc(sub) + "</small>" : "") + "</div>";
  }

  function renderResult(d) {
    const s = d.stats.strategy;
    const bh = d.stats.buy_hold;
    const bm = d.stats.benchmark;
    $("#result").hidden = false;
    $("#r-title").textContent = d.stock.code + " " + d.stock.name + "　回測結果";
    $("#r-period").textContent = d.period.start + " ～ " + d.period.end + "（" + d.period.days + " 個交易日）";
    $("#r-desc").innerHTML = d.description.map((x) => "<li>" + esc(x) + "</li>").join("");
    $("#r-notes").innerHTML = (d.notes || []).map((x) => "<li>" + esc(x) + "</li>").join("");

    $("#r-kpis").innerHTML = [
      kpi("策略總報酬", fmtPct(s.total_return, true), "買進持有 " + fmtPct(bh.total_return, true), s.total_return),
      kpi("年化報酬", fmtPct(s.cagr, true), bm ? "0050 " + fmtPct(bm.cagr, true) : "", s.cagr),
      kpi("最大回撤", fmtPct(s.max_drawdown), "買進持有 " + fmtPct(bh.max_drawdown)),
      kpi("夏普值", s.sharpe === null ? "—" : Number(s.sharpe).toFixed(2), "買進持有 " + (bh.sharpe === null ? "—" : Number(bh.sharpe).toFixed(2))),
      kpi("勝率", s.trades ? fmtPct(s.win_rate) : "—", s.trades ? "獲利因子 " + (s.profit_factor === null ? "—" : s.profit_factor) : ""),
      kpi("交易次數", String(s.trades), s.trades ? "平均持有 " + s.avg_hold_days + " 天" : "期間內沒有觸發買進"),
    ].join("");

    renderCompare(d);
    renderYearly(d);
    renderTrades(d);
    renderCharts(d);
    $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderCompare(d) {
    const cols = [["strategy", "策略"], ["buy_hold", "買進持有"]];
    if (d.stats.benchmark) cols.push(["benchmark", "0050"]);
    const rows = [
      ["總報酬", "total_return", (v) => fmtPct(v, true), true],
      ["年化報酬", "cagr", (v) => fmtPct(v, true), true],
      ["最大回撤", "max_drawdown", (v) => fmtPct(v)],
      ["年化波動", "volatility", (v) => fmtPct(v)],
      ["夏普值", "sharpe", (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(2))],
      ["期末資產", "final_equity", (v) => fmtNum(v)],
    ];
    let h = "<thead><tr><th>指標</th>" + cols.map((c) => "<th>" + c[1] + "</th>").join("") + "</tr></thead><tbody>";
    rows.forEach(([label, key, f, color]) => {
      h += "<tr><td>" + label + "</td>" + cols.map((c) => {
        const v = (d.stats[c[0]] || {})[key];
        return '<td class="' + (color ? cls(v) : "") + '">' + f(v) + "</td>";
      }).join("") + "</tr>";
    });
    const s = d.stats.strategy;
    if (s.trades) {
      h += "<tr><td>平均每筆</td><td class='" + cls(s.avg_return) + "'>" + fmtPct(s.avg_return, true) + "</td>" + cols.slice(1).map(() => "<td>—</td>").join("") + "</tr>";
      h += "<tr><td>最多連續虧損</td><td>" + s.max_consecutive_losses + " 次</td>" + cols.slice(1).map(() => "<td>—</td>").join("") + "</tr>";
      h += "<tr><td>持股時間占比</td><td>" + fmtPct(s.exposure) + "</td>" + cols.slice(1).map(() => "<td>100%</td>").join("") + "</tr>";
    }
    $("#r-compare").innerHTML = h + "</tbody>";
  }

  function renderYearly(d) {
    const hasB = !!d.stats.benchmark;
    let h = "<thead><tr><th>年度</th><th>策略</th><th>買進持有</th>" + (hasB ? "<th>0050</th>" : "") + "</tr></thead><tbody>";
    d.yearly.slice().reverse().forEach((y) => {
      h += "<tr><td>" + y.year + "</td><td class='" + cls(y.strategy) + "'>" + fmtPct(y.strategy, true) + "</td><td class='" +
        cls(y.buy_hold) + "'>" + fmtPct(y.buy_hold, true) + "</td>" + (hasB ? "<td class='" + cls(y.benchmark) + "'>" + fmtPct(y.benchmark, true) + "</td>" : "") + "</tr>";
    });
    $("#r-yearly").innerHTML = h + "</tbody>";
  }

  function renderTrades(d) {
    $("#r-trade-count").textContent = d.trades.length ? "（共 " + d.trades.length + " 筆，新到舊）" : "";
    if (!d.trades.length) { $("#r-trades").innerHTML = "<tbody><tr><td>回測期間沒有任何交易。可以放寬買進條件或拉長期間。</td></tr></tbody>"; return; }
    let h = "<thead><tr><th>買進日</th><th>買價</th><th>賣出日</th><th>賣價</th><th>股數</th><th>持有天數</th><th>報酬</th><th>損益（元）</th><th>出場原因</th></tr></thead><tbody>";
    d.trades.slice().reverse().forEach((t) => {
      h += "<tr><td>" + t.entry_date + "</td><td>" + fmtNum(t.entry_price, 2) + "</td><td>" + t.exit_date + "</td><td>" +
        fmtNum(t.exit_price, 2) + "</td><td>" + fmtNum(t.shares) + "</td><td>" + t.hold_days + "</td><td class='" + cls(t.return_pct) + "'>" +
        fmtPct(t.return_pct, true) + "</td><td class='" + cls(t.pnl) + "'>" + fmtNum(t.pnl) + "</td><td style='text-align:left'>" + esc(t.reason) + "</td></tr>";
    });
    $("#r-trades").innerHTML = h + "</tbody>";
  }

  function renderCharts(d) {
    charts.forEach((c) => c.dispose());
    charts = [];
    if (!window.echarts) return;
    const css = getComputedStyle(document.documentElement);
    const blue = css.getPropertyValue("--blue").trim() || "#0D6FB8";
    const up = css.getPropertyValue("--up").trim() || "#d23c3c";
    const down = css.getPropertyValue("--down").trim() || "#1f9d55";
    const muted = "#8a97a8";
    const amber = "#d08b1a";
    const dates = d.curve.dates;
    const pair = (arr) => dates.map((x, i) => [x, arr[i]]);
    const money = (v) => Number(v).toLocaleString("zh-TW", { maximumFractionDigits: 0 });

    const eq = echarts.init($("#equity-chart"));
    const series = [
      { name: "策略", type: "line", data: pair(d.curve.strategy), showSymbol: false, lineStyle: { width: 2, color: blue }, itemStyle: { color: blue } },
      { name: "買進持有", type: "line", data: pair(d.curve.buy_hold), showSymbol: false, lineStyle: { width: 1.5, color: muted }, itemStyle: { color: muted } },
    ];
    if (d.curve.benchmark) {
      series.push({ name: "0050", type: "line", data: pair(d.curve.benchmark), showSymbol: false, lineStyle: { width: 1.5, color: amber, type: "dashed" }, itemStyle: { color: amber } });
    }
    series.push({
      name: "策略回撤", type: "line", xAxisIndex: 1, yAxisIndex: 1, data: pair(d.curve.drawdown), showSymbol: false,
      lineStyle: { width: 1, color: down }, areaStyle: { color: down, opacity: 0.18 }, itemStyle: { color: down },
    });
    eq.setOption({
      animation: false,
      textStyle: { fontFamily: "Noto Sans TC, sans-serif" },
      legend: { top: 0, type: "scroll", data: series.map((x) => x.name) },
      tooltip: {
        trigger: "axis",
        valueFormatter: (v) => (v === null || v === undefined ? "—" : Math.abs(v) < 101 && v <= 0 ? v.toFixed(2) + "%" : money(v)),
      },
      axisPointer: { link: [{ xAxisIndex: "all" }] },
      grid: [{ left: 64, right: 16, top: 36, height: "58%" }, { left: 64, right: 16, top: "76%", height: "14%" }],
      xAxis: [
        { type: "time", gridIndex: 0, axisLabel: { show: false } },
        { type: "time", gridIndex: 1 },
      ],
      yAxis: [
        { type: "value", scale: true, gridIndex: 0, axisLabel: { formatter: (v) => (v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : money(v)) } },
        { type: "value", gridIndex: 1, max: 0, splitNumber: 2, axisLabel: { formatter: "{value}%" } },
      ],
      dataZoom: [{ type: "inside", xAxisIndex: [0, 1] }],
      series: series,
    });
    charts.push(eq);

    const pc = echarts.init($("#price-chart"));
    const buys = d.trades.map((t) => [t.entry_date, t.entry_price]);
    const sells = d.trades.filter((t) => t.reason.indexOf("未平倉") < 0).map((t) => [t.exit_date, t.exit_price, t.reason, t.return_pct]);
    pc.setOption({
      animation: false,
      textStyle: { fontFamily: "Noto Sans TC, sans-serif" },
      legend: { top: 0, type: "scroll", data: ["收盤價", "買進", "賣出"] },
      tooltip: {
        trigger: "item",
        formatter: (p) => {
          if (p.seriesName === "賣出") return p.value[0] + "<br>賣出 " + p.value[1] + "（" + esc(p.value[2]) + "，" + fmtPct(p.value[3], true) + "）";
          return p.value[0] + "<br>" + p.seriesName + " " + p.value[1];
        },
      },
      grid: { left: 56, right: 16, top: 36, bottom: 40 },
      xAxis: { type: "time" },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }],
      series: [
        { name: "收盤價", type: "line", data: pair(d.price.close), showSymbol: false, lineStyle: { width: 1.2, color: muted }, itemStyle: { color: muted } },
        { name: "買進", type: "scatter", data: buys, symbol: "triangle", symbolSize: 11, itemStyle: { color: up } },
        { name: "賣出", type: "scatter", data: sells, symbol: "triangle", symbolRotate: 180, symbolSize: 11, itemStyle: { color: down } },
      ],
    });
    charts.push(pc);
  }

  window.addEventListener("resize", () => charts.forEach((c) => c.resize()));

  // ------------------------------------------------------------ 啟動
  initBuilder();
  initDates();
  const stock = initStockSearch();
  $("#bt-form").addEventListener("submit", (e) => { e.preventDefault(); run(); });
  $("#share-btn").addEventListener("click", () => {
    const url = location.href;
    const done = () => { $("#share-btn").textContent = "已複製連結 ✓"; setTimeout(() => { $("#share-btn").textContent = "複製分享連結"; }, 1800); };
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, () => prompt("複製這個連結：", url));
    else prompt("複製這個連結：", url);
  });

  if (loadHash(stock)) {
    renderStrategy();
    if (state.symbol) run();  // 分享連結直接跑出結果
  } else {
    applyPreset(META.presets[0]);
    stock.choose({ code: "2330", name: "台積電", market: "上市" });
  }
})();
