/* ═══════════════════════════════════════════════════════════════════════════
   AI Usage — Token & Cost Tracking Dashboard  v3
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  let dailyChart = null;
  let opChart    = null;

  const PALETTE = [
    "#6366f1","#8b5cf6","#ec4899","#f59e0b",
    "#10b981","#3b82f6","#ef4444","#14b8a6",
    "#f97316","#a855f7",
  ];

  const OP_LABELS = {
    "generate_post":          "توليد بوست",
    "generate_carousel":      "توليد كاروسيل",
    "generate_video_script":  "سكريبت فيديو",
    "ai_extractor":           "استخراج مقالات AI",
    "ai_insights":            "تحليل Claude",
    "content_ideas":          "أفكار محتوى",
    "claude_call":            "استدعاء عام",
  };

  const OP_ICONS = {
    "generate_post":         "✍️",
    "generate_carousel":     "🎠",
    "generate_video_script": "🎬",
    "ai_extractor":          "🕷️",
    "ai_insights":           "🧠",
    "content_ideas":         "💡",
    "claude_call":           "⚡",
  };

  function opLabel(op)  { return OP_LABELS[op]  || op; }
  function opIcon(op)   { return OP_ICONS[op]   || "🔧"; }

  function fmtNum(n) {
    if (!n) return "0";
    if (n >= 1_000_000) return (n/1_000_000).toFixed(1) + "M";
    if (n >= 1_000)     return (n/1_000).toFixed(1)     + "K";
    return String(n);
  }

  function fmtCost(c) {
    if (!c || c === 0) return "$0.00";
    if (c < 0.0001) return "$" + c.toFixed(7);
    if (c < 0.01)   return "$" + c.toFixed(5);
    if (c < 1)      return "$" + c.toFixed(4);
    return "$" + c.toFixed(2);
  }

  function deltaBadge(curr, prev, higherIsBad = false) {
    if (!prev || prev === 0) return "";
    const diff = ((curr - prev) / prev * 100);
    const up   = curr >= prev;
    const bad  = higherIsBad ? up : !up;
    return `<span class="usage-delta ${bad ? "usage-delta--bad" : "usage-delta--good"}">
      ${up ? "▲" : "▼"} ${Math.abs(diff).toFixed(0)}%
    </span>`;
  }

  function showError(msg) {
    const loading = document.getElementById("usage-loading");
    if (loading) {
      loading.style.display = "flex";
      loading.innerHTML = `
        <div style="text-align:center;">
          <div style="font-size:2rem;margin-bottom:12px;">⚠️</div>
          <div style="color:#f87171;font-size:0.9rem;margin-bottom:8px;">${msg}</div>
          <button onclick="loadAiUsage()" style="
            background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);
            color:#818cf8;padding:8px 20px;border-radius:10px;cursor:pointer;
            font-family:inherit;font-size:0.85rem;">🔄 إعادة المحاولة</button>
        </div>`;
    }
  }

  /* ── KPI Cards ──────────────────────────────────────────────────────────── */
  function renderKPI(s) {
    const row = document.getElementById("usage-kpi-row");
    if (!row) return;

    const cards = [
      {
        icon: "📞", label: "إجمالي الطلبات",
        value: fmtNum(s.total_calls || 0),
        sub: `${fmtNum(s.prev_calls || 0)} في الفترة السابقة`,
        delta: deltaBadge(s.total_calls, s.prev_calls),
        accent: "#6366f1", glow: "rgba(99,102,241,0.18)",
      },
      {
        icon: "🔤", label: "إجمالي التوكن",
        value: fmtNum(s.total_tokens || 0),
        sub: `📥 ${fmtNum(s.input_tokens || 0)}  ·  📤 ${fmtNum(s.output_tokens || 0)}`,
        delta: "",
        accent: "#8b5cf6", glow: "rgba(139,92,246,0.18)",
      },
      {
        icon: "💵", label: "التكلفة الإجمالية",
        value: fmtCost(s.cost_usd || 0),
        sub: `سابقاً: ${fmtCost(s.prev_cost_usd || 0)}`,
        delta: deltaBadge(s.cost_usd, s.prev_cost_usd, true),
        accent: "#f59e0b", glow: "rgba(245,158,11,0.18)",
      },
      {
        icon: "📊", label: "متوسط / طلب",
        value: fmtCost(s.total_calls ? (s.cost_usd / s.total_calls) : 0),
        sub: "متوسط تكلفة كل استدعاء Claude",
        delta: "",
        accent: "#10b981", glow: "rgba(16,185,129,0.18)",
      },
    ];

    row.innerHTML = cards.map(c => `
      <div class="usage-kpi-card" style="--kpi-accent:${c.accent};--kpi-glow:${c.glow};">
        <div class="usage-kpi-top">
          <span class="usage-kpi-icon">${c.icon}</span>
          <span class="usage-kpi-val">${c.value}</span>
        </div>
        <div class="usage-kpi-label">${c.label}</div>
        <div class="usage-kpi-sub">${c.sub} ${c.delta}</div>
        <div class="usage-kpi-bar"></div>
      </div>
    `).join("");
  }

  /* ── Daily Line Chart ───────────────────────────────────────────────────── */
  function renderDailyChart(trend) {
    const ctx = document.getElementById("usage-daily-chart");
    const emptyEl = document.getElementById("usage-daily-empty");
    if (!ctx) return;
    if (dailyChart) { dailyChart.destroy(); dailyChart = null; }

    if (!trend || !trend.length) {
      ctx.style.display = "none";
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }
    ctx.style.display = "block";
    if (emptyEl) emptyEl.style.display = "none";

    if (typeof Chart === "undefined") return;

    const labels = trend.map(d => {
      const parts = d.date.split("-");
      return `${parts[2]}/${parts[1]}`;
    });
    const data = trend.map(d => d.cost_usd);

    dailyChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "التكلفة USD",
          data,
          borderColor: "#6366f1",
          backgroundColor: (ctx2) => {
            const g = ctx2.chart.ctx.createLinearGradient(0, 0, 0, 200);
            g.addColorStop(0, "rgba(99,102,241,0.25)");
            g.addColorStop(1, "rgba(99,102,241,0)");
            return g;
          },
          fill: true,
          tension: 0.45,
          pointRadius: 4,
          pointBackgroundColor: "#6366f1",
          pointBorderColor: "#0f0f23",
          pointBorderWidth: 2,
          pointHoverRadius: 7,
          borderWidth: 2.5,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1e1b4b",
            borderColor: "rgba(99,102,241,0.4)",
            borderWidth: 1,
            callbacks: { label: ctx => "  $" + ctx.parsed.y.toFixed(6) },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: "#64748b", callback: v => "$" + v.toFixed(4), font: { size: 11 } },
            grid:  { color: "rgba(148,163,184,.06)" },
            border: { display: false },
          },
          x: {
            ticks: { color: "#64748b", font: { size: 11 } },
            grid:  { display: false },
            border: { display: false },
          },
        },
      },
    });
  }

  /* ── Operation Donut Chart ──────────────────────────────────────────────── */
  function renderOpChart(byOp) {
    const ctx     = document.getElementById("usage-op-chart");
    const legend  = document.getElementById("usage-op-legend");
    const wrap    = document.getElementById("usage-op-wrap");
    const emptyEl = document.getElementById("usage-op-empty");
    if (!ctx || !legend) return;
    if (opChart) { opChart.destroy(); opChart = null; }

    if (!byOp || !byOp.length) {
      if (wrap) wrap.style.display = "none";
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }
    if (wrap) wrap.style.display = "flex";
    if (emptyEl) emptyEl.style.display = "none";

    if (typeof Chart === "undefined") return;

    const labels = byOp.map(o => opLabel(o.operation));
    const data   = byOp.map(o => o.cost_usd);
    const colors = byOp.map((_, i) => PALETTE[i % PALETTE.length]);

    opChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data, backgroundColor: colors,
          borderWidth: 3, borderColor: "#0f0f23",
          hoverOffset: 8,
        }],
      },
      options: {
        cutout: "68%",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1e1b4b",
            borderColor: "rgba(255,255,255,0.1)",
            borderWidth: 1,
            callbacks: { label: c => "  $" + c.parsed.toFixed(6) },
          },
        },
      },
    });

    legend.innerHTML = byOp.slice(0, 8).map((o, i) => `
      <div class="usage-legend-item">
        <span class="usage-legend-dot" style="background:${colors[i]}"></span>
        <span class="usage-legend-name">${opIcon(o.operation)} ${opLabel(o.operation)}</span>
        <span class="usage-legend-val" style="color:${colors[i]}">${fmtCost(o.cost_usd)}</span>
      </div>
    `).join("");
  }

  /* ── Operation Breakdown Table ──────────────────────────────────────────── */
  function renderOpTable(byOp) {
    const tbody = document.getElementById("usage-op-table");
    if (!tbody) return;
    const maxCost = (byOp && byOp.length) ? Math.max(...byOp.map(o => o.cost_usd), 0.000001) : 1;

    tbody.innerHTML = byOp && byOp.length ? byOp.map((o, i) => {
      const pct   = (o.cost_usd / maxCost * 100).toFixed(1);
      const color = PALETTE[i % PALETTE.length];
      return `
        <tr class="usage-trow">
          <td style="padding:14px 16px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:1.2rem;">${opIcon(o.operation)}</span>
              <span style="font-weight:600;color:var(--text);">${opLabel(o.operation)}</span>
            </div>
          </td>
          <td style="padding:14px 16px;text-align:center;">
            <span class="usage-badge" style="background:rgba(99,102,241,.12);color:#818cf8;">${o.calls}</span>
          </td>
          <td style="padding:14px 16px;text-align:center;color:var(--muted);">${fmtNum(o.input_tokens)}</td>
          <td style="padding:14px 16px;text-align:center;color:var(--muted);">${fmtNum(o.output_tokens)}</td>
          <td style="padding:14px 16px;text-align:center;">
            <span style="font-weight:700;color:${color};">${fmtCost(o.cost_usd)}</span>
          </td>
          <td style="padding:14px 16px;min-width:120px;">
            <div class="usage-bar-track">
              <div class="usage-bar-fill" style="width:${pct}%;background:${color};"></div>
            </div>
          </td>
        </tr>`;
    }).join("") : `<tr><td colspan="6" class="usage-empty">لا توجد بيانات بعد — ولّد محتوى وستظهر هنا 🚀</td></tr>`;
  }

  /* ── Model Cards ────────────────────────────────────────────────────────── */
  function renderModelCards(byModel) {
    const wrap = document.getElementById("usage-model-cards");
    if (!wrap) return;

    wrap.innerHTML = (byModel && byModel.length) ? byModel.map((m, i) => {
      const color = PALETTE[(i + 3) % PALETTE.length];
      const avg   = m.calls ? m.cost_usd / m.calls : 0;
      return `
        <div class="usage-model-card" style="--mc:${color};">
          <div class="usage-model-icon">🤖</div>
          <div class="usage-model-name">${m.model.replace("claude-", "")}</div>
          <div class="usage-model-cost">${fmtCost(m.cost_usd)}</div>
          <div class="usage-model-meta">
            <span>${fmtNum(m.calls)} طلب</span>
            <span>·</span>
            <span>${fmtNum(m.total_tokens)} توكن</span>
          </div>
          <div class="usage-model-avg">متوسط: ${fmtCost(avg)} / طلب</div>
        </div>`;
    }).join("") : `<p style="color:var(--muted);padding:20px 0;font-size:0.85rem;">لا يوجد بيانات بعد</p>`;
  }

  /* ── Recent Logs Table ──────────────────────────────────────────────────── */
  function renderLogTable(logs) {
    const tbody = document.getElementById("usage-log-table");
    if (!tbody) return;

    tbody.innerHTML = (logs && logs.length) ? logs.map((r) => {
      const dt  = new Date(r.created_at);
      const ts  = dt.toLocaleString("ar-EG", { month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" });
      const costBg = r.cost_usd > 0.01 ? "rgba(245,158,11,.12)" : r.cost_usd > 0.001 ? "rgba(99,102,241,.1)" : "rgba(100,116,139,.1)";
      const costCl = r.cost_usd > 0.01 ? "#f59e0b" : r.cost_usd > 0.001 ? "#818cf8" : "#94a3b8";
      return `
        <tr class="usage-trow">
          <td style="padding:10px 14px;color:#475569;font-size:0.78rem;">${r.id}</td>
          <td style="padding:10px 14px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span>${opIcon(r.operation)}</span>
              <span style="font-weight:500;">${opLabel(r.operation)}</span>
            </div>
          </td>
          <td style="padding:10px 14px;">
            <span class="usage-badge" style="background:rgba(139,92,246,.1);color:#a78bfa;font-size:0.75rem;">
              ${r.model.replace("claude-", "")}
            </span>
          </td>
          <td style="padding:10px 14px;text-align:center;color:#64748b;">${fmtNum(r.input_tokens)}</td>
          <td style="padding:10px 14px;text-align:center;color:#64748b;">${fmtNum(r.output_tokens)}</td>
          <td style="padding:10px 14px;text-align:center;">
            <span class="usage-badge" style="background:${costBg};color:${costCl};font-weight:700;">
              ${fmtCost(r.cost_usd)}
            </span>
          </td>
          <td style="padding:10px 14px;color:#64748b;font-size:0.78rem;">${ts}</td>
        </tr>`;
    }).join("") : `<tr><td colspan="7" class="usage-empty">لا يوجد سجلات بعد</td></tr>`;
  }

  /* ── Main Load Function ─────────────────────────────────────────────────── */
  window.loadAiUsage = async function () {
    const loading = document.getElementById("usage-loading");
    const content = document.getElementById("usage-content");
    if (!loading || !content) return;

    const period = document.getElementById("usage-period-select")?.value ?? 30;

    // Reset state
    loading.style.display = "flex";
    loading.innerHTML = `<span class="an-spin">🪙</span><span>جاري تحميل بيانات الاستهلاك...</span>`;
    content.style.display = "none";

    try {
      const token = localStorage.getItem("access_token") || "";

      // Timeout after 15 seconds
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);

      const res = await fetch(`/api/ai-usage/overview?days=${period}`, {
        headers: { Authorization: "Bearer " + token },
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (res.status === 401) {
        showError("انتهت الجلسة — يرجى تسجيل الدخول مرة أخرى");
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => res.statusText);
        showError(`خطأ من السيرفر (${res.status}): ${txt.slice(0, 120)}`);
        return;
      }

      const data = await res.json();

      renderKPI        (data.summary      || {});
      renderDailyChart (data.daily_trend  || []);
      renderOpChart    (data.by_operation || []);
      renderOpTable    (data.by_operation || []);
      renderModelCards (data.by_model     || []);
      renderLogTable   (data.recent_logs  || []);

      loading.style.display = "none";
      content.style.display = "block";

    } catch (err) {
      if (err.name === "AbortError") {
        showError("انتهت مهلة الاتصال — تأكد من أن السيرفر يعمل");
      } else {
        showError("فشل الاتصال: " + (err.message || String(err)));
      }
      console.error("[AI Usage]", err);
    }
  };

  function showError(msg) {
    const loading = document.getElementById("usage-loading");
    const content = document.getElementById("usage-content");
    if (content) content.style.display = "none";
    if (loading) {
      loading.style.display = "flex";
      loading.innerHTML = `
        <div style="text-align:center;">
          <div style="font-size:2.5rem;margin-bottom:14px;">⚠️</div>
          <div style="color:#f87171;font-size:0.9rem;margin-bottom:16px;max-width:400px;line-height:1.6;">${msg}</div>
          <button onclick="loadAiUsage()" style="
            background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);
            color:#818cf8;padding:9px 22px;border-radius:10px;cursor:pointer;
            font-family:inherit;font-size:0.85rem;transition:.15s;"
            onmouseover="this.style.background='rgba(99,102,241,.25)'"
            onmouseout="this.style.background='rgba(99,102,241,.15)'">
            🔄 إعادة المحاولة
          </button>
        </div>`;
    }
  }

})();
