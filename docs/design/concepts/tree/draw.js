/* The tree round's drawings of 2WCD's solved fields (window.TREE, from generators/tree/extract.py), in
   Plotly or ECharts. Each function draws one plot into an element; the boards call them. Nothing here is
   the shell, and nothing here computes a number the library did not: every value, the difference
   included, comes from extract.py. The only change is the unit: a potential is drawn in mV, a
   concentration in mM. */
(function () {
  "use strict";
  const T = window.TREE;

  // The potential in mV, as the settings name it: one scale applied to every grid and series in V.
  const toMilli = (grid) => {
    if (grid.unit !== "V") return;
    grid.v = grid.v.map((row) => row.map((v) => (v === null ? null : v * 1e3)));
    grid.unit = "mV";
  };
  [T.maps.potential, T.mirrored, T.difference, T.revolved.potential].forEach(toMilli);
  for (const s of T.cut.series) if (s.unit === "V") { s.v = s.v.map((v) => (v === null ? null : v * 1e3)); s.unit = "mV"; }
  // A concentration in mM, which is mol/m³, as the probes' table names it.
  for (const grid of [...Object.values(T.maps), ...Object.values(T.revolved), ...T.cut.series]) if (grid.unit === "mol/m³") grid.unit = "mM";

  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const theme = () => ({
    ink: css("--canvas-plot-ink") || "#16181d",
    bg: css("--canvas-plot") || "#ffffff",
    muted: css("--muted") || "#4f5563",
    line: css("--line") || "#d9dce3",
    accent: css("--accent") || "#5b3fd6",
    font: css("--font-ui") || "system-ui, sans-serif",
  });
  // The shell's series colours (gui/web/plane.py:SERIES), not the status colours.
  const SERIES = ["#2a78d6", "#d95926", "#199e70", "#c98500"];
  // Positive blue, negative red, through a light middle (WB-39); a dark middle on the dark theme (WB-49).
  const dark = () => matchMedia("(prefers-color-scheme: dark)").matches || document.documentElement.dataset.theme === "dark";
  const diverging = () => dark()
    ? [[0, "#e0584f"], [0.5, "#20232a"], [1, "#5b9be6"]]
    : [[0, "#b2182b"], [0.25, "#ef8a62"], [0.5, "#f7f7f7"], [0.75, "#67a9cf"], [1, "#2166ac"]];
  const solidColour = () => (dark() ? "#3a3f49" : "#d5d9e0");
  const viridis = "Viridis";
  const quantity = (key) => T.maps[key];
  const label = (map) => `${map.name} (${map.unit})`;
  const flat = (rows) => rows.flat().filter((v) => v !== null);
  const percentile = (values, p) => {
    const sorted = values.map(Math.abs).sort((a, b) => a - b);
    return sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
  };
  // A field across zero opens on the 99th percentile of its size, as the explorer's map does (WB-49).
  const symmetric = (map) => { const s = percentile(flat(map.v), 99); return [-s, s]; };
  // A one-signed field opens on its 1st to 99th percentile here; today's explorer opens it on its least and greatest.
  const spread = (values) => {
    const sorted = values.slice().sort((a, b) => a - b);
    const at = (p) => sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
    return [at(1), at(99)];
  };
  const rangeOf = (map, div) => (div ? symmetric(map) : spread(flat(map.v)));
  const outlineXY = (mirror) => {
    const x = [], y = [];
    for (const [r0, z0, r1, z1] of T.outline) { x.push(mirror ? -r0 : r0, mirror ? -r1 : r1, null); y.push(z0, z1, null); }
    return { x, y };
  };
  const plotlyBase = (t, extra) => Object.assign({
    paper_bgcolor: t.bg, plot_bgcolor: t.bg, font: { family: t.font, size: 12, color: t.ink },
    margin: { l: 64, r: 10, t: 8, b: 40 }, showlegend: false,
  }, extra);
  const axis = (t, title, extra) => Object.assign({
    title: { text: title, standoff: 8 }, color: t.ink, gridcolor: t.line, zerolinecolor: t.line, linecolor: t.muted, ticks: "outside", mirror: true, showline: true, automargin: true,
  }, extra);
  // The workbench would draw its own toolbar: Plotly's mode bar misses WCAG's 24 px targets and its focus ring on dark.
  // A board shows it only where the library itself is judged (window.SHOW_MODEBAR, L1).
  const config = () => ({ displaylogo: false, responsive: true, displayModeBar: window.SHOW_MODEBAR ? "hover" : false,
    modeBarButtonsToRemove: ["toImage", "sendDataToCloud", "lasso2d", "select2d"] });
  // A colour bar beside its map, not at the paper's edge, once the map has taken its equal aspect.
  const nearBar = (el) => {
    const domain = el._fullLayout && el._fullLayout.xaxis && el._fullLayout.xaxis.domain;
    if (domain) Plotly.restyle(el, { "colorbar.x": domain[1] + 0.03, "colorbar.xanchor": "left" }, [0]);
  };

  // A map in (r, z): the surface, and on request contours, arrows, the outline, the probes and the cut,
  // and at r < 0 a second run (mirrored) or the same run (reflect), so a pore reads whole.
  function plotlyMap(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const map = o.map || quantity(key);
    const div = o.diverging !== undefined ? o.diverging : map.unit === "mV";
    const range = rangeOf(map, div);
    const traces = [];
    const second = o.reflect ? map : T.mirrored;
    const both = o.mirrored || o.reflect;
    const surface = (m, mirror) => ({
      type: "heatmap", x: mirror ? m.r.map((r) => -r) : m.r, y: m.z, z: m.v, zmin: range[0], zmax: range[1],
      colorscale: div ? diverging() : viridis, zsmooth: "best", hoverongaps: false, showscale: !mirror,
      colorbar: { title: { text: `${label(map)}${o.clipNote === false ? "" : ", ends clipped"}`, side: "right" }, thickness: 12, len: 0.85,
        outlinecolor: t.ink, outlinewidth: 1, tickfont: { size: 12 }, exponentformat: "power" },
      hovertemplate: `r %{x:.2f} nm<br>z %{y:.2f} nm<br>${map.name} %{z:.4g} ${map.unit}<extra>${mirror && !o.reflect ? T.runs.second.label : T.runs.first.label}</extra>`,
    });
    if (o.surface !== false) traces.push(surface(map, false));
    if (both && o.surface !== false) traces.push(surface(second, true));
    if (o.contours) {
      const lines = o.surface === false;
      const step = o.step || (div ? 5 : (range[1] - range[0]) / 8);
      traces.push({ type: "contour", x: map.r, y: map.z, z: map.v, hoverinfo: "skip", showscale: lines,
        colorbar: { title: { text: label(map), side: "right" }, thickness: 12, len: 0.85, outlinecolor: t.ink, outlinewidth: 1 },
        contours: { coloring: lines ? "lines" : "none", start: div ? -40 * step : range[0], end: div ? 40 * step : range[1], size: step,
          showlabels: lines, labelfont: { size: 12, color: t.ink } },
        line: { width: lines ? 1.6 : 1, color: lines ? undefined : t.ink, smoothing: 0.8 }, colorscale: div ? diverging() : viridis });
    }
    if (o.arrows) {
      const a = T.arrows, x = [], y = [], size = [];
      let top = 0;
      for (let i = 0; i < a.r.length; i++) if (a.ur[i] !== null) top = Math.max(top, Math.hypot(a.ur[i], a.uz[i]));
      const scale = 0.9 / top;
      for (let i = 0; i < a.r.length; i++) {
        if (a.ur[i] === null || a.uz[i] === null) continue;
        if (Math.hypot(a.ur[i], a.uz[i]) < 0.04 * top) continue;
        x.push(a.r[i], a.r[i] + a.ur[i] * scale, null); y.push(a.z[i], a.z[i] + a.uz[i] * scale, null); size.push(0, 7, 0);
      }
      traces.push({ type: "scatter", mode: "lines+markers", x, y, hoverinfo: "skip", line: { color: t.ink, width: 1.2 },
        marker: { symbol: "arrow", angleref: "previous", size, color: t.ink } });
      if (o.arrowKey) el.dataset.arrowTop = top.toPrecision(2);
    }
    // The solids, where the field has no value, drawn over the contours and arrows a gap would cross.
    const solid = solidColour();
    const mask = (m, mirror) => ({ type: "heatmap", x: mirror ? m.r.map((r) => -r) : m.r, y: m.z, z: m.v.map((row) => row.map((v) => (v === null ? 1 : null))),
      colorscale: [[0, solid], [1, solid]], showscale: false, hoverinfo: "skip", zsmooth: false });
    traces.push(mask(map, false));
    if (both) traces.push(mask(second, true));
    if (o.outline !== false) {
      const xy = outlineXY(false);
      traces.push({ type: "scatter", mode: "lines", x: xy.x, y: xy.y, hoverinfo: "skip", line: { color: t.ink, width: 1 } });
      if (both) { const m = outlineXY(true); traces.push({ type: "scatter", mode: "lines", x: m.x, y: m.y, hoverinfo: "skip", line: { color: t.ink, width: 1 } }); }
    }
    if (o.cutline) {
      traces.push({ type: "scatter", mode: "lines", x: [0, 0], y: [T.window_nm[2], T.window_nm[3]], hoverinfo: "skip", line: { color: t.accent, width: 2, dash: "dash" } });
    }
    if (o.probes) {
      traces.push({ type: "scatter", mode: "markers+text", x: T.probes.map((p) => p.r_nm), y: T.probes.map((p) => p.z_nm),
        text: T.probes.map((_, i) => `<b>P${i + 1}</b>`), textposition: "middle right",
        marker: { symbol: "circle", size: 11, color: t.bg, line: { width: 2.5, color: t.accent } }, textfont: { color: t.ink, size: 13 }, hoverinfo: "skip" });
    }
    const w = T.window_nm;
    const xr = both ? [-w[1], w[1]] : [w[0], w[1]];
    const note = (x, anchor, text) => ({ x, xanchor: anchor, y: w[3], yanchor: "top", text, showarrow: false, font: { size: 12 }, bgcolor: t.bg, borderpad: 2 });
    const annotations = o.mirrored ? [note(-0.3, "right", "ASP neutral"), note(0.3, "left", "charged")]
      : o.reflect ? [note(-0.3, "right", "reflected"), note(0.3, "left", o.label || T.runs.first.label)] : [];
    Plotly.newPlot(el, traces, plotlyBase(t, {
      xaxis: axis(t, "r (nm)", { range: xr, constrain: "domain" }),
      yaxis: axis(t, "z (nm)", { range: [w[2], w[3]], scaleanchor: "x", scaleratio: 1, constrain: "domain" }),
      margin: { l: 52, r: 8, t: 6, b: 40 }, annotations,
    }), config()).then(() => nearBar(el));
  }

  // A line along the axis: a series per run.
  function plotlyCut(el, o) {
    const t = theme();
    const which = o.quantity || "potential";
    const series = T.cut.series.filter((s) => s.quantity === which);
    const traces = series.map((s, i) => ({ type: "scatter", mode: "lines", x: T.cut.z, y: s.v, name: s.label,
      line: { color: SERIES[i], width: 2, dash: i ? "dash" : "solid" }, hovertemplate: `z %{x:.2f} nm<br>%{y:.4g} ${s.unit}<extra>${s.label}</extra>` }));
    const s0 = series[0];
    Plotly.newPlot(el, traces, plotlyBase(t, {
      showlegend: true, legend: { orientation: "h", y: 1.02, yanchor: "bottom", x: 0, font: { size: 12 } },
      margin: { l: 64, r: 10, t: 24, b: 40 },
      xaxis: axis(t, "z (nm)"), yaxis: axis(t, `${s0.name} (${s0.unit})`, { type: o.log ? "log" : "linear" }),
    }), config());
  }

  // A global quantity against the swept value: the I–V. The ring marks the shown run.
  function plotlyGlobal(el, o) {
    const t = theme();
    const y = T.iv.map((p) => p.current_nA * 1e3);
    const x = T.iv.map((p) => p.bias_mV);
    const shown = T.iv.findIndex((p) => p.bias_mV === 50);
    Plotly.newPlot(el, [
      { type: "scatter", mode: o.scatter ? "markers" : "lines+markers", x, y, line: { color: SERIES[0], width: 2 }, marker: { size: 8, color: SERIES[0] },
        hovertemplate: "%{x} mV<br>%{y:.4g} pA<extra></extra>" },
      { type: "scatter", mode: "markers", x: [x[shown]], y: [y[shown]], marker: { size: 14, symbol: "circle-open", color: t.accent, line: { width: 2.5 } }, hoverinfo: "skip" },
    ], plotlyBase(t, {
      xaxis: axis(t, "bias (mV)", { zeroline: true, tickvals: x }), yaxis: axis(t, "current (pA)", { zeroline: true }),
    }), config());
  }

  // A probe's value against the swept value (COMSOL's point graph).
  function plotlyPoint(el) {
    const t = theme();
    const x = T.iv.map((p) => p.bias_mV), y = T.iv.map((p) => p.probe);
    const sp = T.species[0].replace("_mol_m3", "").replace("c_", "");
    Plotly.newPlot(el, [{ type: "scatter", mode: "lines+markers", x, y, line: { color: SERIES[1], width: 2 }, marker: { size: 8, color: SERIES[1] } }],
      plotlyBase(t, { xaxis: axis(t, "bias (mV)", { tickvals: x }), yaxis: axis(t, `${sp} at P1 (mM)`) }), config());
  }

  // The (r, z) field turned about the axis, a quarter cut away: the cut faces carry the field on the map's
  // colour range (WB-50), the walls are grey.
  function plotlyRevolution(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const m = T.revolved[key];
    const div = m.unit === "mV";
    const range = rangeOf(T.maps[key], div);
    const face = (angle, scale) => {
      const x = [], y = [], z = [];
      for (let j = 0; j < m.z.length; j++) {
        // A solid's cell, where the field has no value, is a hole in the face.
        const keep = (i, v) => (m.v[j][i] === null ? null : v);
        x.push(m.r.map((r, i) => keep(i, r * Math.cos(angle)))); y.push(m.r.map((r, i) => keep(i, r * Math.sin(angle)))); z.push(m.r.map((_, i) => keep(i, m.z[j])));
      }
      return { type: "surface", x, y, z, surfacecolor: m.v, cmin: range[0], cmax: range[1], colorscale: div ? diverging() : viridis,
        showscale: scale, lighting: { ambient: 1, diffuse: 0, specular: 0, fresnel: 0 },
        colorbar: { title: { text: `${m.name} (${m.unit})`, side: "right" }, thickness: 12, len: 0.7, outlinecolor: t.ink, outlinewidth: 1 },
        hovertemplate: `${m.name} %{surfacecolor:.4g} ${m.unit}<extra></extra>` };
    };
    const X = [], Y = [], Z = [], I = [], J = [], K = [];
    const steps = 18, sweep = 1.5 * Math.PI;
    for (const [r0, z0, r1, z1] of T.outline) {
      if (Math.max(r0, r1) > T.window_nm[1] + 1e-9) continue;
      const base = X.length;
      for (let k = 0; k <= steps; k++) {
        const a = (k / steps) * sweep;
        X.push(r0 * Math.cos(a), r1 * Math.cos(a)); Y.push(r0 * Math.sin(a), r1 * Math.sin(a)); Z.push(z0, z1);
      }
      for (let k = 0; k < steps; k++) { const p = base + 2 * k; I.push(p, p + 1); J.push(p + 1, p + 3); K.push(p + 2, p + 2); }
    }
    const traces = [face(0, true), face(sweep, false),
      { type: "mesh3d", x: X, y: Y, z: Z, i: I, j: J, k: K, color: dark() ? "#9aa0ab" : "#b9bec8", opacity: 0.5, flatshading: true, hoverinfo: "skip",
        lighting: { ambient: 0.75, diffuse: 0.5 } }];
    const sceneAxis = (title) => ({ title: { text: title }, color: t.ink, gridcolor: t.line, backgroundcolor: t.bg, showbackground: false });
    Plotly.newPlot(el, traces, plotlyBase(t, {
      margin: { l: 0, r: 0, t: 0, b: 0 },
      scene: { xaxis: sceneAxis("x"), yaxis: sceneAxis("y"), zaxis: sceneAxis("z (nm)"), aspectmode: "data",
        camera: { eye: { x: 1.4, y: -1.4, z: 0.3 } } },
    }), config());
  }

  // ---- ECharts: the same plots, as far as the library draws them, set up as L1's are ----
  function ecTheme(t) {
    return { backgroundColor: t.bg, textStyle: { fontFamily: t.font, color: t.ink, fontSize: 12 }, animation: false };
  }
  const ecAxis = (t, name, extra) => Object.assign({ name, nameLocation: "middle", nameGap: 30, axisLine: { onZero: false, lineStyle: { color: t.muted } },
    axisLabel: { color: t.ink }, splitLine: { lineStyle: { color: t.line } } }, extra);
  const ecColours = (div) => div ? (dark() ? ["#e0584f", "#20232a", "#5b9be6"] : ["#b2182b", "#ef8a62", "#f7f7f7", "#67a9cf", "#2166ac"])
    : ["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"];

  function echartsMap(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const map = quantity(key);
    const div = map.unit === "mV";
    const range = rangeOf(map, div);
    const data = [], solids = [];
    for (let j = 0; j < map.z.length; j++) for (let i = 0; i < map.r.length; i++) {
      const v = map.v[j][i];
      if (v === null) solids.push([i, j, 1]); else data.push([i, j, v]);
    }
    const chart = echarts.init(el, null, { renderer: "canvas" });
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 56, right: 100, top: 10, bottom: 44 },
      tooltip: { formatter: (p) => (p.seriesIndex ? "" : `r ${map.r[p.value[0]].toFixed(2)} nm, z ${map.z[p.value[1]].toFixed(2)} nm<br>${map.name} ${Number(p.value[2]).toPrecision(4)} ${map.unit}`) },
      xAxis: ecAxis(t, "r (nm)", { type: "category", data: map.r.map((r) => r.toFixed(1)), axisLabel: { interval: Math.floor(map.r.length / 5), color: t.ink } }),
      yAxis: ecAxis(t, "z (nm)", { type: "category", data: map.z.map((z) => z.toFixed(1)), axisLabel: { interval: Math.floor(map.z.length / 8), color: t.ink } }),
      visualMap: [
        { seriesIndex: 0, min: range[0], max: range[1], calculable: true, orient: "vertical", right: 8, top: "middle", itemHeight: 220,
          inRange: { color: ecColours(div) }, text: [map.unit, ""], textStyle: { color: t.ink }, precision: 1 },
        { seriesIndex: 1, show: false, min: 0, max: 1, inRange: { color: [solidColour(), solidColour()] } }],
      series: [{ type: "heatmap", data, progressive: 0, emphasis: { disabled: true } },
        { type: "heatmap", data: solids, progressive: 0, emphasis: { disabled: true }, silent: true }],
    }));
    return chart;
  }

  function echartsCut(el, o) {
    const t = theme();
    const which = o.quantity || "potential";
    const series = T.cut.series.filter((s) => s.quantity === which);
    const values = series.flatMap((s) => s.v.filter((v) => v !== null && v > 0));
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 70, right: 14, top: 30, bottom: 44 }, legend: { top: 0, left: 0, textStyle: { color: t.ink } },
      tooltip: { trigger: "axis" }, dataZoom: [{ type: "inside" }],
      xAxis: ecAxis(t, "z (nm)", { type: "value", min: Math.ceil(T.window_nm[2]), max: Math.floor(T.window_nm[3]) }),
      yAxis: ecAxis(t, `${series[0].name} (${series[0].unit})`, { type: o.log ? "log" : "value", nameGap: 52,
        min: Math.floor(Math.min(...values) * 0.9), max: Math.ceil(Math.max(...values) * 1.1) }),
      series: series.map((s, i) => ({ type: "line", name: s.label, showSymbol: false, data: T.cut.z.map((z, k) => [z, s.v[k]]),
        lineStyle: { width: 2, type: i ? "dashed" : "solid", color: SERIES[i] }, itemStyle: { color: SERIES[i] } })),
    }));
  }

  function echartsGlobal(el) {
    const t = theme();
    const shown = T.iv.find((p) => p.bias_mV === 50);
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      grid: { left: 64, right: 14, top: 12, bottom: 44 }, tooltip: { trigger: "item" },
      xAxis: ecAxis(t, "bias (mV)", { type: "value" }), yAxis: ecAxis(t, "current (pA)", { type: "value", nameGap: 46 }),
      series: [{ type: "line", data: T.iv.map((p) => [p.bias_mV, p.current_nA * 1e3]), symbolSize: 8, lineStyle: { color: SERIES[0], width: 2 }, itemStyle: { color: SERIES[0] } },
        { type: "scatter", data: [[shown.bias_mV, shown.current_nA * 1e3]], symbol: "emptyCircle", symbolSize: 15, itemStyle: { color: t.accent, borderWidth: 2.5 } }],
    }));
  }

  function echartsRevolution(el, o) {
    const t = theme();
    const key = o.quantity || "potential";
    const m = T.revolved[key];
    const div = m.unit === "mV";
    const range = rangeOf(T.maps[key], div);
    const data = [];
    for (const angle of [0, 1.5 * Math.PI]) for (let j = 0; j < m.z.length; j++) for (let i = 0; i < m.r.length; i++) {
      const v = m.v[j][i]; if (v === null) continue;
      data.push([m.r[i] * Math.cos(angle), m.r[i] * Math.sin(angle), m.z[j], v]);
    }
    const chart = echarts.init(el);
    chart.setOption(Object.assign(ecTheme(t), {
      visualMap: { min: range[0], max: range[1], dimension: 3, inRange: { color: ecColours(div) }, right: 4, top: "middle", textStyle: { color: t.ink }, calculable: true, precision: 1 },
      xAxis3D: { name: "x", type: "value" }, yAxis3D: { name: "y", type: "value" }, zAxis3D: { name: "z (nm)", type: "value" },
      grid3D: { axisLine: { lineStyle: { color: t.muted } }, axisLabel: { textStyle: { color: t.ink } }, viewControl: { alpha: 15, beta: 40 }, boxDepth: 80, boxWidth: 80, boxHeight: 160 },
      series: [{ type: "scatter3D", data, symbolSize: 3.2 }],
    }));
  }

  // The library's difference of the two runs (post/fields.py:field_difference), the second less the first.
  function difference() { return T.difference; }

  // The quantities a board lists, in the order the Quantities node would keep them.
  const SHOWN = ["current", "conductance", "transport number", "currents (Na+)", "currents (Cl-)", "bias"];
  function shownQuantities() {
    return SHOWN.map((name) => T.quantities.find((row) => row.quantity === name)).filter(Boolean);
  }

  // A map's opening range, as its surface's settings show it.
  function rangeText(key) {
    const [lo, hi] = symmetric(quantity(key || "potential"));
    return `${lo.toFixed(1).replace("-", "−")} … ${hi.toFixed(1)}`;
  }
  // The probes' table, the same on every board that shows it.
  function probeTable(head, body) {
    const sp = T.species.map((s) => s.replace("_mol_m3", "").replace("c_", ""));
    head.innerHTML = `<tr><th>Probe</th><th>r (nm)</th><th>z (nm)</th><th>φ (mV)</th>${sp.map((s) => `<th>${s} (mM)</th>`).join("")}</tr>`;
    T.probes.forEach((p, i) => body.insertAdjacentHTML("beforeend",
      `<tr><td>P${i + 1}</td><td class="v">${p.r_nm.toFixed(2)}</td><td class="v">${p.z_nm.toFixed(2)}</td><td class="v">${(p.potential * 1e3).toFixed(2)}</td>${T.species.map((s) => `<td class="v">${p[s].toFixed(1)}</td>`).join("")}</tr>`));
  }
  function quantityTable(body) {
    for (const row of shownQuantities()) body.insertAdjacentHTML("beforeend", `<tr><td>${row.quantity}</td><td class="v">${row.value}</td><td>${row.unit}</td></tr>`);
  }
  document.addEventListener("DOMContentLoaded", () => {
    for (const el of document.querySelectorAll("[data-range]")) el.firstChild.textContent = rangeText(el.dataset.range);
    for (const el of document.querySelectorAll("[data-probes]")) probeTable(el.querySelector("thead"), el.querySelector("tbody"));
    for (const el of document.querySelectorAll("[data-quantities]")) quantityTable(el.querySelector("tbody"));
  });

  window.draw = { difference, shownQuantities, rangeText, plotlyMap, plotlyCut, plotlyGlobal, plotlyPoint, plotlyRevolution,
    echartsMap, echartsCut, echartsGlobal, echartsRevolution };
})();
