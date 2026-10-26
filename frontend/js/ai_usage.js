/* ═══════════════════════════════════════════════════════════════════════════
   AI Usage — Token & Cost Tracking Dashboard
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ── Chart.js instances (destroyed & re-created on each load) ─────────── */
  let dailyChart = null;
  let opChart    = null;

  /* ── Colour palette ───────────────────────────────────────────────────── */
  const PALETTE = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f59e0b",
    "#10b981", "#3b82f6", "#ef4444", "#14b8a6",
    "#f97316", "#a855f7",
  ];

  /* ── Arabic operation labels ──────────────────────────────────────────── */
  const OP_LABELS = {
    "generate_post":          "توليد بوست",
    "generate_carousel":      "توليد كاروسيل",
    "generate_video_script":  "توليد سكريبت فيديو",
    "ai_extractor":           "استخراج AI للمقالات",
    "ai_insights":            "تحليل Claude الذكي",
    "content_ideas":          "أفكار المحتوى",
    "claude_call":            "استدعاء Claude عام",
  };

  function opLabel(op) {
    return OP_LABELS[op] || op;
  }

  /* ── Number helpers ───────────────────────────────────────────────────── */
  function fmtNum(n) {
    if (!n) return "0";
    return n.toLocaleString("ar-SA");
  }

  function fmtCost(c) {
    if (!c) return "$0.000000";
    if (c < 0.001) return "$" + c.toFixed(6);
    if (c < 1)    return "$" + c.toFixed(4);
    return "$" + c.toFixed(2);
  }

  function deltaBadge(curr, prev, higher_is_bad = false) {
    if (!prev) return "";
    const pct = ((curr - prev) / Math.max(prev, 0.000001) * 100).toFixed(0);
    const up  = curr >= prev;
    const bad = higher_is_bad ? up : !up;
    return `<span style="font-size:0.72rem;padding:2px 6px;border-radius:6px;
      background:${bad ? "rgba(239,68,68,.12)" : "rgba(16,185,129,.12)"};
      color:${bad ? "#f87171" : "#34d399"};">
      ${up ? "▲" : "▼"} ${Math.abs(pct)}%
    </span>`;
  }

  /* ── KPI Cards ────────────────────────────────────────────────────────── */
  function renderKPI(s) {
    const row = document.getElementById("usage-kpi-row");
    if (!row) return;

    const cards = [
      {
        icon: "📞", label: "إجمالي الطلبات",
        value: fmtNum(s.total_calls),
        sub: `مقارنة بـ ${fmtNum(s.prev_calls)} ${deltaBadge(s.total_calls, s.prev_calls)}`,
        accent: "#6366f1",
      },
      {
        icon: "🔤", label: "إجمالي التوكن",
        value: fmtNum(s.total_tokens),
        sub: `إدخال: ${fmtNum(s.input_tokens)} · إخراج: ${fmtNum(s.output_tokens)}`,
        accent: "#8b5cf6",
      },
      {
        icon: "💵", label: "التكلفة الإجمالية",
        value: fmtCost(s.cost_usd),
        sub: `الفترة السابقة: ${fmtCost(s.prev_cost_usd)} ${deltaBadge(s.cost_usd, s.prev_cost_usd, true)}`,
        accent: "#f59e0b",
      },
      {
        icon: "📊", label: "متوسط التكلفة / طلب",
        value: fmtCost(s.total_calls ? s.cost_usd / s.total_calls : 0),
        sub: "متوسط تكلفة كل استدعاء Claude",
        accent: "#10b981",
      },
    ];

    row.innerHTML = cards.map(c => `
      <div class="an-kpi" style="border-top:3px solid ${c.accent};">
        <div style="font-size:1.6rem;margin-bottom:6px;">${c.icon}</div>
        <div class="an-kpi-val">${c.value}</div>
        <div class="an-kpi-label">${c.label}</div>
        <div style="font-size:0.75rem;color:var(--muted);margin-top:4px;">${c.sub}</div>
      </div>
    `).join("");
  }

  /* ── Daily Cost Line Chart ────────────────────────────────────────────── */
  function renderDailyChart(trend) {
    const ctx = document.getElementById("usage-daily-chart");
    if (!ctx) return;
    if (dailyChart) { dailyChart.destroy(); dailyChart = null; }

    const labels = trend.map(d => d.date.slice(5)); // MM-DD
    const data   = trend.map(d => d.cost_usd);

    dailyChart = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "التكلفة USD",
          data,
          borderColor: "#6366f1",
          backgroundColor: "rgba(99,102,241,0.08)",
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: "#6366f1",
          pointHoverRadius: 6,
        }],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => " $" + ctx.parsed.y.toFixed(6),
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: "#94a3b8", callback: v => "$" + v.toFixed(4) },
            grid: { color: "rgba(148,163,184,.1)" },
          },
          x: {
            ticks: { color: "#94a3b8" },
            grid: { display: false },
          },
        },
      },
    });
  }

  /* ── Operation Donut Chart ────────────────────────────────────────────── */
  function renderOpChart(byOp) {
    const ctx = document.getElementById("usage-op-chart");
    const legend = document.getElementById("usage-op-legend");
    if (!ctx || !legend) return;
    if (opChart) { opChart.destroy(); opChart = null; }

    const labels = byOp.map(o => opLabel(o.operation));
    const data   = byOp.map(o => o.cost_usd);
    const colors = byOp.map((_, i) => PALETTE[i % PALETTE.length]);

    opChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: "var(--bg)" }],
      },
      options: {
        cutout: "62%",
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => " $" + ctx.parsed.toFixed(6) } },
        },
      },
    });

    // Custom legend
    legend.innerHTML = byOp.slice(0, 8).map((o, i) => `
      <div style="display:flex;align-items:center;gap:8px;">
        <span style="width:10px;height:10px;border-radius:50%;background:${colors[i]};flex-shrink:0;"></span>
        <span style="color:var(--muted);flex:1;">${opLabel(o.operation)}</span>
        <span style="font-weight:600;color:var(--text);">${fmtCost(o.cost_usd)}</span>
      </div>
    `).join("");
  }

  /* ── Operation Table ──────────────────────────────────────────────────── */
  function renderOpTable(byOp) {
    const tbody = document.getElementById("usage-op-table");
    if (!tbody) return;
    const maxCost = byOp.length ? Math.max(...byOp.map(o => o.cost_usd)) : 1;

    tbody.innerHTML = byOp.map((o, i) => {
      const pct = maxCost > 0 ? (o.cost_usd / maxCost * 100).toFixed(1) : 0;
      const color = PALETTE[i % PALETTE.length];
      return `<tr style="border-bottom:1px solid var(--line);">
        <td style="padding:12px 16px;font-weight:600;color:var(--text);">${opLabel(o.operation)}</td>
        <td style="padding:12px 16px;text-align:center;color:var(--muted);">${fmtNum(o.calls)}</td>
        <td style="padding:12px 16px;text-align:center;color:var(--muted);">${fmtNum(o.input_tokens)}</td>
        <td style="padding:12px 16px;text-align:center;color:var(--muted);">${fmtNum(o.output_tokens)}</td>
        <td style="padding:12px 16px;text-align:center;font-weight:700;color:${color};">${fmtCost(o.cost_usd)}</td>
        <td style="padding:12px 16px;">
          <div style="background:rgba(255,255,255,.06);border-radius:99px;height:8px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:${color};border-radius:99px;transition:.4s;"></div>
          </div>
        </td>
      </tr>`;
    }).join("") || `<tr><td colspan="6" style="padding:24px;text-align:center;color:var(--muted);">لا توجد بيانات بعد</td></tr>`;
  }

  /* ── Model Cards ──────────────────────────────────────────────────────── */
  function renderModelCards(byModel) {
    const wrap = document.getElementById("usage-model-cards");
    if (!wrap) return;

    wrap.innerHTML = byModel.map((m, i) => {
      const color = PALETTE[(i + 2) % PALETTE.length];
      return `
        <div class="an-card" style="flex:1;min-width:220px;padding:20px;border-top:3px solid ${color};">
          <div style="font-size:0.75rem;color:var(--muted);margin-bottom:8px;">🤖 ${m.model}</div>
          <div style="font-size:1.4rem;font-weight:800;color:${color};margin-bottom:4px;">${fmtCost(m.cost_usd)}</div>
          <div style="font-size:0.82rem;color:var(--muted);">${fmtNum(m.calls)} طلب · ${fmtNum(m.total_tokens)} توكن</div>
        </div>`;
    }).join("") || `<p style="color:var(--muted);">لا توجد بيانات بعد</p>`;
  }

  /* ── Recent Logs Table ────────────────────────────────────────────────── */
  function renderLogTable(logs) {
    const tbody = document.getElementById("usage-log-table");
    if (!tbody) return;

    tbody.innerHTML = logs.map(r => {
      const dt = new Date(r.created_at);
      const timeStr = dt.toLocaleString("ar-SA", { month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" });
      const costColor = r.cost_usd > 0.01 ? "#f59e0b" : r.cost_usd > 0.001 ? "#818cf8" : "#94a3b8";
      return `<tr style="border-bottom:1px solid rgba(255,255,255,.04);">
        <td style="padding:9px 14px;color:var(--muted);font-size:0.78rem;">${r.id}</td>
        <td style="padding:9px 14px;font-weight:600;">${opLabel(r.operation)}</td>
        <td style="padding:9px 14px;color:var(--muted);font-size:0.78rem;">${r.model.replace("claude-","")}</td>
        <td style="padding:9px 14px;text-align:center;color:var(--muted);">${fmtNum(r.input_tokens)}</td>
        <td style="padding:9px 14px;text-align:center;color:var(--muted);">${fmtNum(r.output_tokens)}</td>
        <td style="padding:9px 14px;text-align:center;font-weight:700;color:${costColor};">${fmtCost(r.cost_usd)}</td>
        <td style="padding:9px 14px;color:var(--muted);font-size:0.78rem;">${timeStr}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="7" style="padding:24px;text-align:center;color:var(--muted);">لا يوجد سجلات بعد</td></tr>`;
  }

  /* ── Main Load Function ───────────────────────────────────────────────── */
  window.loadAiUsage = async function () {
    const loading = document.getElementById("usage-loading");
    const content = document.getElementById("usage-content");
    const period  = document.getElementById("usage-period-select")?.value ?? 30;
    if (!loading || !content) return;

    loading.style.display = "flex";
    content.style.display = "none";

    try {
      const token = localStorage.getItem("access_token") || "";
      const res   = await fetch(`/api/ai-usage/overview?days=${period}`, {
        headers: { Authorization: "Bearer " + token },
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const s    = data.summary;

      renderKPI(s);
      renderDailyChart(data.daily_trend   || []);
      renderOpChart   (data.by_operation  || []);
      renderOpTable   (data.by_operation  || []);
      renderModelCards(data.by_model      || []);
      renderLogTable  (data.recent_logs   || []);

      loading.style.display = "none";
      content.style.display = "block";
    } catch (err) {
      loading.innerHTML = `<span style="color:#f87171;">❌ فشل تحميل البيانات: ${err.message}</span>`;
      console.error("[AI Usage]", err);
    }
  };

  /* ── Auto-load when page becomes visible ─────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    const origGo = window.go;
    window.go = function (el) {
      origGo && origGo(el);
      const page = (el && el.dataset && el.dataset.page) || el;
      if (page === "page-ai-usage") loadAiUsage();
    };
  });
})();
