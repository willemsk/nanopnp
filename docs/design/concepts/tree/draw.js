/* The tree round's drawings of 2WCD's solved fields (window.TREE, from generators/tree/extract.py), in
   Plotly or ECharts. Each function draws one plot into an element; the boards call them. Nothing here is
   the shell: the shell's numbers come from the library, as these do through extract.py. */
(function () {
  "use strict";
  const T = window.TREE;
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const theme = () => ({
    ink: css("--canvas-plot-ink") || "#16181d",
    bg: css("--canvas-plot") || "#ffffff",
    muted: css("--muted") || "#4f5563",
    line: css("--line") || "#d9dce3",
    accent: css("--accent") || "#5b3fd6",
    info: css("--info") || "#1f5fae",
    warn: css("--warn") || "#8a5200",
    font: css("--font-ui") || "system-ui, sans-serif",
  });
  // Positive blue, negative red, through a light middle (WB-39); a dark middle on the dark theme (WB-49).
  const dark = () => matchMedia("(prefers-color-scheme: dark)").matches || document.documentElement.dataset.theme === "dark";
  const diverging = () => dark()
    ? [[0, "#e0584f"], [0.5, "#20232a"], [1, "#5b9be6"]]
    : [[0, "#b2182b"], [0.25, "#ef8a62"], [0.5, "#f7f7f7"], [0.75, "#67a9cf"], [1, "#2166ac"]];
  const viridis = "Viridis";
  const quantity = (key) => (key === "potential" ? T.maps.potential : T.maps[key]);
  const label = (map) => `${map.name} (${map.unit})`;
  const flat = (rows) => rows.flat().filter((v) => v !== null);
  const percentile = (values, p) => {
    const sorted = values.map(Math.abs).sort((a, b) => a - b);
    return sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
  };
  const symmetric = (map) => { const s = percentile(flat(map.v), 99); return [-s, s]; };
  const outlineXY = (mirror) => {
    const x = [], y = [];
    for (const [r0, z0, r1, z1] of T.outline) { x.push(mirror ? -r0 : r0, mirror ? -r1 : r1, null); y.push(z0, z1, null); }
    return { x, y };
  };
  const plotlyBase = (t, extra) => Object.assign({
    paper_bgcolor: t.bg, plot_bgcolor: t.bg, font: { family: t.font, size: 12, color: t.ink },
    margin: { l: 52, r: 10, t: 8, b: 40 }, showlegend: false,
  }, extra);
  const axis = (t, title, extra) => Object.assign({
    title: { text: title, standoff: 6 }, color: t.ink, gridcolor: t.line, zerolinecolor: t.line, linecolor: t.muted, ticks: "outside", mirror: true, showline: true,
  }, extra);
  const config = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["toImage", "sendDataToCloud", "lasso2d", "select2d"] };

  // A map in (r, z): the surface, and on request contours, arrows, the outline and a second run mirrored.
  function plotlyMap(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const map = o.map || quantity(key);
    const div = o.diverging !== undefined ? o.diverging : key === "potential";
    const range = div ? symmetric(map) : [Math.min(...flat(map.v)), Math.max(...flat(map.v))];
    const traces = [];
    const surface = (m, mirror) => ({
      type: "heatmap", x: mirror ? m.r.map((r) => -r) : m.r, y: m.z, z: m.v, zmin: range[0], zmax: range[1],
      colorscale: div ? diverging() : viridis, zsmooth: "best", hoverongaps: false, showscale: !mirror,
      colorbar: { title: { text: label(map), side: "right" }, thickness: 12, len: 0.9, outlinecolor: t.ink, outlinewidth: 1, tickfont: { size: 11 } },
      hovertemplate: `r %{x:.2f} nm<br>z %{y:.2f} nm<br>${map.name} %{z:.4g} ${map.unit}<extra>${mirror ? T.runs.second.label : T.runs.first.label}</extra>`,
    });
    if (o.surface !== false) traces.push(surface(map, false));
    if (o.mirrored) traces.push(surface(T.mirrored, true));
    if (o.contours) {
      const step = o.step || (div ? 0.005 : (range[1] - range[0]) / 10);
      traces.push({ type: "contour", x: map.r, y: map.z, z: map.v, showscale: false, hoverinfo: "skip",
        contours: { coloring: o.surface === false ? "lines" : "none", start: div ? -10 * step * 4 : range[0], end: div ? 10 * step * 4 : range[1], size: step, showlabels: !!o.contourLabels, labelfont: { size: 10, color: t.ink } },
        line: { width: 1, color: o.surface === false ? undefined : t.ink, smoothing: 0.8 }, colorscale: div ? diverging() : viridis, opacity: 0.75 });
    }
    if (o.arrows) {
      const a = T.arrows, x = [], y = [], size = [];
      let top = 0;
      for (let i = 0; i < a.r.length; i++) if (a.ur[i] !== null) top = Math.max(top, Math.hypot(a.ur[i], a.uz[i]));
      const scale = 0.9 / top;
      for (let i = 0; i < a.r.length; i++) {
        if (a.ur[i] === null || a.uz[i] === null) continue;
        const m = Math.hypot(a.ur[i], a.uz[i]);
        if (m < 0.04 * top) continue;
        x.push(a.r[i], a.r[i] + a.ur[i] * scale, null); y.push(a.z[i], a.z[i] + a.uz[i] * scale, null); size.push(0, 7, 0);
      }
      traces.push({ type: "scatter", mode: "lines+markers", x, y, hoverinfo: "skip", line: { color: t.ink, width: 1.2 },
        marker: { symbol: "arrow", angleref: "previous", size, color: t.ink } });
    }
    // The solids, where the field has no value, drawn over the contours and arrows that a gap would cross.
    const solid = dark() ? "#2b2f37" : "#e3e6eb";
    const mask = (m, mirror) => ({ type: "heatmap", x: mirror ? m.r.map((r) => -r) : m.r, y: m.z, z: m.v.map((row) => row.map((v) => (v === null ? 1 : null))),
      colorscale: [[0, solid], [1, solid]], showscale: false, hoverinfo: "skip", zsmooth: false });
    traces.push(mask(map, false));
    if (o.mirrored) traces.push(mask(T.mirrored, true));
    if (o.outline !== false) {
      const xy = outlineXY(false);
      traces.push({ type: "scatter", mode: "lines", x: xy.x, y: xy.y, hoverinfo: "skip", line: { color: t.ink, width: 1 } });
      if (o.mirrored) { const m = outlineXY(true); traces.push({ type: "scatter", mode: "lines", x: m.x, y: m.y, hoverinfo: "skip", line: { color: t.ink, width: 1 } }); }
    }
    if (o.probes) {
      traces.push({ type: "scatter", mode: "markers+text", x: [0.02, 1.2], y: [0, 3], text: ["P1", "P2"], textposition: "middle right",
        marker: { symbol: "circle-open", size: 10, color: t.accent, line: { width: 2 } }, textfont: { color: t.accent }, hoverinfo: "skip" });
    }
    if (o.cutline) {
      traces.push({ type: "scatter", mode: "lines", x: [0.02, 0.02], y: [T.window_nm[2], T.window_nm[3]], hoverinfo: "skip", line: { color: t.accent, width: 2, dash: "dash" } });
    }
    const w = T.window_nm;
    const xr = o.mirrored ? [-w[1], w[1]] : [w[0], w[1]];
    Plotly.newPlot(el, traces, plotlyBase(t, {
      xaxis: axis(t, "r (nm)", { range: xr, constrain: "domain" }),
      yaxis: axis(t, "z (nm)", { range: [w[2], w[3]], scaleanchor: "x", scaleratio: 1, constrain: "domain" }),
      margin: { l: 48, r: 8, t: 6, b: 38 },
      annotations: o.mirrored ? [
        { x: -w[1] / 2, y: w[3], yanchor: "top", text: T.runs.second.label, showarrow: false, font: { size: 11 }, bgcolor: t.bg },
        { x: w[1] / 2, y: w[3], yanchor: "top", text: T.runs.first.label, showarrow: false, font: { size: 11 }, bgcolor: t.bg }] : [],
    }), config);
  }

  // A line along the axis: a series per run and quantity.
  function plotlyCut(el, o) {
    const t = theme();
    const which = o.quantity || "potential";
    const series = T.cut.series.filter((s) => s.quantity === which);
    const colours = [t.info, t.warn];
    const traces = series.map((s, i) => ({ type: "scatter", mode: "lines", x: T.cut.z, y: s.v, name: s.label,
      line: { color: colours[i % 2], width: 2, dash: i ? "dash" : "solid" }, hovertemplate: `z %{x:.2f} nm<br>%{y:.4g} ${s.unit}<extra>${s.label}</extra>` }));
    const s0 = series[0];
    Plotly.newPlot(el, traces, plotlyBase(t, {
      showlegend: true, legend: { orientation: "h", y: 1.02, yanchor: "bottom", x: 0, font: { size: 11 } },
      margin: { l: 56, r: 10, t: 22, b: 38 },
      xaxis: axis(t, "z (nm)"), yaxis: axis(t, `${s0.name} (${s0.unit})`, { type: o.log ? "log" : "linear" }),
    }), config);
  }

  // A global quantity against the swept value: the I–V, or the conductance.
  function plotlyGlobal(el, o) {
    const t = theme();
    const y = o.conductance ? T.iv.map((p) => p.conductance_nS) : T.iv.map((p) => p.current_nA);
    const x = T.iv.map((p) => p.bias_mV);
    const shown = T.iv.findIndex((p) => p.bias_mV === 50);
    Plotly.newPlot(el, [
      { type: "scatter", mode: o.scatter ? "markers" : "lines+markers", x, y, line: { color: t.info, width: 2 }, marker: { size: 8, color: t.info },
        hovertemplate: `%{x} mV<br>%{y:.4g} ${o.conductance ? "nS" : "nA"}<extra></extra>` },
      { type: "scatter", mode: "markers", x: [x[shown]], y: [y[shown]], marker: { size: 13, symbol: "circle-open", color: t.accent, line: { width: 2.5 } }, hoverinfo: "skip" },
    ], plotlyBase(t, {
      xaxis: axis(t, "bias (mV)", { zeroline: true, tickvals: x }), yaxis: axis(t, o.conductance ? "conductance (nS)" : "current (nA)", { zeroline: true }),
    }), config);
  }

  // A probe's value against the swept value (COMSOL's point graph).
  function plotlyPoint(el) {
    const t = theme();
    const x = T.iv.map((p) => p.bias_mV), y = T.iv.map((p) => p.probe);
    const sp = T.species[0].replace("_mol_m3", "").replace("c_", "");
    Plotly.newPlot(el, [{ type: "scatter", mode: "lines+markers", x, y, line: { color: t.warn, width: 2 }, marker: { size: 8 } }],
      plotlyBase(t, { xaxis: axis(t, "bias (mV)", { tickvals: x }), yaxis: axis(t, `c ${sp} at P1 (mol/m³)`) }), config);
  }

  // The (r, z) field turned about the axis and cut open: the two cut faces carry the field, the walls are grey.
  function plotlyRevolution(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const m = T.revolved[key];
    const div = key === "potential";
    const values = flat(m.v);
    const range = div ? (() => { const s = percentile(values, 99); return [-s, s]; })() : [Math.min(...values), Math.max(...values)];
    const face = (angle, scale) => {
      const x = [], y = [], z = [];
      for (let j = 0; j < m.z.length; j++) {
        x.push(m.r.map((r) => r * Math.cos(angle))); y.push(m.r.map((r) => r * Math.sin(angle))); z.push(m.r.map(() => m.z[j]));
      }
      return { type: "surface", x, y, z, surfacecolor: m.v, cmin: range[0], cmax: range[1], colorscale: div ? diverging() : viridis,
        showscale: scale, colorbar: { title: { text: `${m.name} (${m.unit})`, side: "right" }, thickness: 12, len: 0.7, outlinecolor: t.ink, outlinewidth: 1 },
        hovertemplate: `${m.name} %{surfacecolor:.4g} ${m.unit}<extra></extra>` };
    };
    // The walls: each outline segment turned through three quarters of a turn.
    const X = [], Y = [], Z = [], I = [], J = [], K = [];
    const steps = 18, sweep = 1.5 * Math.PI;
    for (const [r0, z0, r1, z1] of T.outline) {
      if (Math.max(r0, r1) > T.window_nm[1] + 1e-9) continue;
      const base = X.length;
      for (let k = 0; k <= steps; k++) {
        const a = (k / steps) * sweep;
        X.push(r0 * Math.cos(a), r1 * Math.cos(a)); Y.push(r0 * Math.sin(a), r1 * Math.sin(a)); Z.push(z0, z1);
      }
      for (let k = 0; k < steps; k++) {
        const p = base + 2 * k;
        I.push(p, p + 1); J.push(p + 1, p + 3); K.push(p + 2, p + 2);
      }
    }
    const traces = [face(0, true), face(sweep, false),
      { type: "mesh3d", x: X, y: Y, z: Z, i: I, j: J, k: K, color: dark() ? "#9aa0ab" : "#b9bec8", opacity: 0.55, flatshading: true, hoverinfo: "skip",
        lighting: { ambient: 0.75, diffuse: 0.5 } }];
    const sceneAxis = (title) => ({ title: { text: title }, color: t.ink, gridcolor: t.line, backgroundcolor: t.bg, showbackground: false });
    Plotly.newPlot(el, traces, plotlyBase(t, {
      margin: { l: 0, r: 0, t: 0, b: 0 },
      scene: { xaxis: sceneAxis("x (nm)"), yaxis: sceneAxis("y (nm)"), zaxis: sceneAxis("z (nm)"), aspectmode: "data",
        camera: { eye: { x: 1.9, y: 1.1, z: 0.45 } } },
    }), config);
  }

  // ---- ECharts: the same plots, as far as the library draws them ----
  function ecTheme(t) {
    return { backgroundColor: t.bg, textStyle: { fontFamily: t.font, color: t.ink, fontSize: 12 }, animation: false };
  }
  const ecAxis = (t, name, extra) => Object.assign({ name, nameLocation: "middle", nameGap: 28, axisLine: { lineStyle: { color: t.muted } },
    axisLabel: { color: t.ink }, splitLine: { lineStyle: { color: t.line } } }, extra);
  const ecColours = (div) => div ? (dark() ? ["#e0584f", "#20232a", "#5b9be6"] : ["#b2182b", "#ef8a62", "#f7f7f7", "#67a9cf", "#2166ac"])
    : ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];

  function echartsMap(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const map = quantity(key);
    const div = key === "potential";
    const range = div ? symmetric(map) : [Math.min(...flat(map.v)), Math.max(...flat(map.v))];
    const data = [];
    for (let j = 0; j < map.z.length; j++) for (let i = 0; i < map.r.length; i++) { const v = map.v[j][i]; if (v !== null) data.push([i, j, v]); }
    const chart = echarts.init(el, null, { renderer: "canvas" });
    const w = T.window_nm;
    const series = [{ type: "heatmap", data, progressive: 0, emphasis: { disabled: true } }];
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 50, right: 70, top: 10, bottom: 40 },
      tooltip: { formatter: (p) => p.value ? `r ${map.r[p.value[0]].toFixed(2)} nm, z ${map.z[p.value[1]].toFixed(2)} nm<br>${map.name} ${Number(p.value[2]).toPrecision(4)} ${map.unit}` : "" },
      xAxis: ecAxis(t, "r (nm)", { type: "category", data: map.r.map((r) => r.toFixed(1)), axisLabel: { interval: Math.floor(map.r.length / 5), color: t.ink } }),
      yAxis: ecAxis(t, "z (nm)", { type: "category", data: map.z.map((z) => z.toFixed(1)), axisLabel: { interval: Math.floor(map.z.length / 8), color: t.ink } }),
      visualMap: { min: range[0], max: range[1], calculable: true, orient: "vertical", right: 4, top: "middle", itemHeight: 220,
        inRange: { color: ecColours(div) }, text: [map.unit, ""], textStyle: { color: t.ink }, precision: 3 },
      series,
    }));
    if (o.note) el.insertAdjacentHTML("beforeend", "");
    return chart;
  }

  function echartsCut(el, o) {
    const t = theme();
    const which = o.quantity || "potential";
    const series = T.cut.series.filter((s) => s.quantity === which);
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 64, right: 12, top: 28, bottom: 40 }, legend: { top: 0, left: 0, textStyle: { color: t.ink } },
      tooltip: { trigger: "axis" }, dataZoom: [{ type: "inside" }],
      xAxis: ecAxis(t, "z (nm)", { type: "value", min: T.window_nm[2], max: T.window_nm[3] }),
      yAxis: ecAxis(t, `${series[0].name} (${series[0].unit})`, { type: o.log ? "log" : "value", nameGap: 48, scale: true }),
      series: series.map((s, i) => ({ type: "line", name: s.label, showSymbol: false, data: T.cut.z.map((z, k) => [z, s.v[k]]),
        lineStyle: { width: 2, type: i ? "dashed" : "solid", color: i ? t.warn : t.info }, itemStyle: { color: i ? t.warn : t.info } })),
    }));
  }

  function echartsGlobal(el) {
    const t = theme();
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 56, right: 12, top: 12, bottom: 40 }, tooltip: { trigger: "item" },
      xAxis: ecAxis(t, "bias (mV)", { type: "value" }), yAxis: ecAxis(t, "current (nA)", { type: "value", nameGap: 40 }),
      series: [{ type: "line", data: T.iv.map((p) => [p.bias_mV, p.current_nA]), symbolSize: 8, lineStyle: { color: t.info, width: 2 }, itemStyle: { color: t.info } }],
    }));
  }

  function echartsRevolution(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const m = T.revolved[key];
    const div = key === "potential";
    const values = flat(m.v);
    const range = div ? (() => { const s = percentile(values, 99); return [-s, s]; })() : [Math.min(...values), Math.max(...values)];
    const data = [];
    for (const angle of [0, 1.5 * Math.PI]) for (let j = 0; j < m.z.length; j++) for (let i = 0; i < m.r.length; i++) {
      const v = m.v[j][i]; if (v === null) continue;
      data.push([m.r[i] * Math.cos(angle), m.r[i] * Math.sin(angle), m.z[j], v]);
    }
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      visualMap: { min: range[0], max: range[1], dimension: 3, inRange: { color: ecColours(div) }, right: 4, top: "middle", textStyle: { color: t.ink }, calculable: true },
      xAxis3D: { name: "x (nm)", type: "value" }, yAxis3D: { name: "y (nm)", type: "value" }, zAxis3D: { name: "z (nm)", type: "value" },
      grid3D: { axisLine: { lineStyle: { color: t.muted } }, axisLabel: { textStyle: { color: t.ink } }, viewControl: { alpha: 15, beta: 40 }, boxDepth: 80, boxWidth: 80, boxHeight: 160 },
      series: [{ type: "scatter3D", data, symbolSize: 3.2 }],
    }));
  }

  // The second run less the first on their shared grid: a board's stand-in for the library's difference.
  function difference() {
    const a = T.maps.potential, b = T.mirrored;
    return { name: "Δ potential φ", unit: a.unit, r: a.r, z: a.z, v: a.v.map((row, j) => row.map((v, i) => (v === null || b.v[j][i] === null ? null : b.v[j][i] - v))) };
  }

  window.draw = { difference,  plotlyMap, plotlyCut, plotlyGlobal, plotlyPoint, plotlyRevolution, echartsMap, echartsCut, echartsGlobal, echartsRevolution };
})();
