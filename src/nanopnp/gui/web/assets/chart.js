// The workbench's charts: plots of y against x that the vendored uPlot draws, from what the server
// writes (gui/web/chart.py). Each panel is one uPlot, the panels one above the other. A logarithmic
// axis leaves out a sample it cannot place, and the chart's note counts it (VER-44). A band is
// shaded behind the curves and named inside, a rule dashed over them; both are keyed under the
// chart. A drag zooms the x axis and a double click returns it to the range the chart opens on.
(() => {
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const SUPERSCRIPT = { '-': '⁻', 0: '⁰', 1: '¹', 2: '²', 3: '³', 4: '⁴',
    5: '⁵', 6: '⁶', 7: '⁷', 8: '⁸', 9: '⁹' };
  // A band's fill over the plot's ink, its label's size and gap, and a sample's mark, in CSS px.
  const BAND_ALPHA = 0.12, LABEL_PX = 11, LABEL_GAP = 4, MARK_PX = 5, CURVE_W = 2;
  // The least height a panel's plot keeps, in CSS px.
  const PANEL_MIN_H = 120;

  // A number in three figures; one far from unity as a power of ten, its minus signs U+2212.
  const figures = (value) => {
    if (value === null || value === undefined || !Number.isFinite(value)) return '—';
    const far = value !== 0 && (Math.abs(value) >= 1e4 || Math.abs(value) < 1e-3);
    if (!far) return Number(value.toPrecision(3)).toString().replace('-', '−');
    const [mantissa, exponent] = value.toExponential(2).split('e');
    const power = String(Number(exponent)).split('').map((c) => SUPERSCRIPT[c]).join('');
    const kept = Number(mantissa) === 1 ? '' : `${Number(mantissa)} × `;
    return `${kept}10${power}`.replace('-', '−');
  };

  // Whether an axis of this scale places the value: finite, and positive if logarithmic.
  const placeable = (value, scale) => value !== null && value !== undefined
    && Number.isFinite(value) && (scale !== 'log' || value > 0);

  const sqrtScale = {
    distr: 100,
    fwd: (v) => Math.sign(v) * Math.sqrt(Math.abs(v)),
    bwd: (v) => Math.sign(v) * v * v,
  };

  const scaleOf = (axis) => {
    const base = axis.scale === 'log' ? { distr: 3, log: 10 }
      : axis.scale === 'sqrt' ? { ...sqrtScale } : { distr: 1 };
    // An x scale is a number, not uPlot's default of a time.
    return { ...base, auto: true, time: false };
  };

  // Five ticks evenly apart on a square-root axis, each in two figures.
  const sqrtTicks = (low, high) => {
    const a = sqrtScale.fwd(low), b = sqrtScale.fwd(high), ticks = [];
    for (let k = 0; k <= 5; k += 1) {
      const value = sqrtScale.bwd(a + ((b - a) * k) / 5);
      const rounded = value === 0 ? 0 : Number(value.toPrecision(2));
      if (!ticks.includes(rounded)) ticks.push(rounded);
    }
    return ticks;
  };

  // A panel's series on one shared x: each series' samples where it has them, a gap where its own
  // sample is null, and nothing (undefined) where only another series has a sample. An x that a
  // logarithmic axis cannot place is left out, its samples counted.
  const joined = (panel, series) => {
    let omitted = 0;
    const xs = new Set();
    for (const s of series) {
      s.x.forEach((x, k) => {
        const y = s.y[k];
        if (y !== null && Number.isFinite(x) && !(placeable(x, panel.x.scale) && placeable(y, panel.y.scale))) {
          omitted += 1;
        }
        if (placeable(x, panel.x.scale)) xs.add(x);
      });
    }
    const x = [...xs].sort((p, q) => p - q);
    const at = new Map(x.map((value, k) => [value, k]));
    const columns = series.map((s) => {
      const column = new Array(x.length).fill(undefined);
      s.x.forEach((value, k) => {
        if (!at.has(value)) return;
        const y = s.y[k];
        column[at.get(value)] = placeable(y, panel.y.scale) ? y : null;
      });
      return column;
    });
    return { data: [x, ...columns], omitted };
  };

  // The x range a panel opens on: its own, else the extent of its samples.
  const opening = (panel, data) => {
    if (panel.x.range) return panel.x.range;
    const x = data[0];
    return x.length ? [x[0], x[x.length - 1] > x[0] ? x[x.length - 1] : x[0] + 1] : [0, 1];
  };

  // A band shaded behind the curves, and its name and note inside it at the top: across where the
  // band is wide enough, else its number, else nothing (the table names it).
  const drawBands = (bands, u) => {
    const ctx = u.ctx, ratio = uPlot.pxRatio, { left, top, width, height } = u.bbox;
    const ink = token('--canvas-plot-ink') || '#16181d';
    ctx.save();
    ctx.beginPath();
    ctx.rect(left, top, width, height);
    ctx.clip();
    ctx.fillStyle = ink;
    for (const band of bands) {
      if (!band.shaded) continue;
      const x0 = u.valToPos(band.x[0], 'x', true), x1 = u.valToPos(band.x[1], 'x', true);
      ctx.globalAlpha = BAND_ALPHA;
      ctx.fillRect(Math.min(x0, x1), top, Math.abs(x1 - x0), height);
    }
    ctx.globalAlpha = 1;
    ctx.font = `${LABEL_PX * ratio}px ${token('--font-ui') || 'sans-serif'}`;
    ctx.textBaseline = 'top';
    const gap = LABEL_GAP * ratio, line = (LABEL_PX + 2) * ratio;
    for (const band of bands) {
      if (!band.label) continue;
      const x0 = u.valToPos(band.x[0], 'x', true), x1 = u.valToPos(band.x[1], 'x', true);
      const span = Math.abs(x1 - x0), start = Math.min(x0, x1);
      const lines = [band.label, ...(band.note ? [band.note] : [])];
      const widest = Math.max(...lines.map((text) => ctx.measureText(text).width));
      ctx.save();
      ctx.beginPath();
      ctx.rect(start, top, span, height);
      ctx.clip();
      if (span >= widest + 2 * gap) {
        lines.forEach((text, k) => ctx.fillText(text, start + gap, top + gap + k * line));
      } else if (band.short && !band.note) {
        // A narrow band that holds its curves is named by its number, which the rung table reads.
        if (span >= ctx.measureText(band.short).width + gap) ctx.fillText(band.short, start + gap / 2, top + gap);
      } else if (span >= line) {
        // A narrow silent band says which silence it is up its left edge, ending at its top.
        ctx.translate(start + gap / 2, top + gap);
        ctx.rotate(-Math.PI / 2);
        ctx.textAlign = 'right';
        lines.forEach((text, k) => ctx.fillText(text, 0, k * line));
      }
      ctx.restore();
    }
    ctx.restore();
  };

  // A rule: a dashed line across the plot in the plot's ink.
  const drawRules = (rules, u) => {
    const ctx = u.ctx, ratio = uPlot.pxRatio, { top, height } = u.bbox;
    ctx.save();
    ctx.strokeStyle = token('--canvas-plot-ink') || '#16181d';
    ctx.lineWidth = 1.5 * ratio;
    ctx.setLineDash([6 * ratio, 4 * ratio]);
    for (const rule of rules) {
      const x = u.valToPos(rule.x, 'x', true);
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, top + height);
      ctx.stroke();
    }
    ctx.restore();
  };

  const axisOf = (axis, ink, grid, font) => ({
    label: axis.label,
    stroke: ink,
    font,
    labelFont: font,
    grid: { stroke: grid, width: 1 },
    ticks: { stroke: grid, width: 1 },
    // A split the axis thins out is null: it is ticked but not labelled.
    values: (u, splits) => splits.map((v) => (v === null || v === undefined ? '' : figures(v))),
    // uPlot thins a custom scale's labels as it does a logarithmic one's; only a logarithmic axis
    // keeps its labels to the decades.
    ...(axis.scale === 'log' ? {} : { filter: (u, splits) => splits }),
    ...(axis.ticks.length || axis.scale === 'sqrt' ? {
      splits: (u, index, low, high) => {
        const given = axis.ticks.length ? axis.ticks : sqrtTicks(low, high);
        const slack = (high - low) * 1e-9;
        return given.filter((value) => value >= low - slack && value <= high + slack);
      },
    } : {}),
  });

  // One panel: its uPlot, under the host's slot for it.
  const makePlot = (state, index, slot, width, height) => {
    const spec = state.spec, panel = spec.panels[index];
    const series = spec.series.filter((s) => s.panel === index);
    const bands = spec.bands.filter((b) => b.panel === index);
    const rules = spec.rules.filter((r) => r.panel === index);
    const { data, omitted } = joined(panel, series);
    const ink = token('--canvas-plot-ink') || '#16181d';
    const grid = token('--line') || '#d9dce3';
    const font = `12px ${token('--font-ui') || 'sans-serif'}`;
    const yRange = panel.y.range;
    const opts = {
      width, height,
      scales: {
        x: scaleOf(panel.x),
        y: { ...scaleOf(panel.y), ...(yRange ? { auto: false, range: () => [yRange[0], yRange[1]] } : {}) },
      },
      axes: [axisOf(panel.x, ink, grid, font), axisOf(panel.y, ink, grid, font)],
      series: [
        { label: panel.x.label, value: (u, v) => figures(v) },
        ...series.map((s) => ({
          label: s.label,
          stroke: s.colour,
          width: CURVE_W,
          dash: s.dash.length ? s.dash : undefined,
          spanGaps: false,
          points: { show: s.marks, size: MARK_PX, fill: s.colour, stroke: s.colour },
          value: (u, v) => figures(v),
        })),
      ],
      legend: {
        show: series.length > 0,
        live: true,
        // A swatch is a line sample with the series' dash, so a dashed curve is told apart.
        markers: { dash: (u, k) => (u.series[k].dash && u.series[k].dash.length ? 'dashed' : 'solid') },
      },
      cursor: {
        drag: { x: true, y: false },
        bind: { dblclick: (u) => () => { state.reset(index); return null; } },
      },
      hooks: {
        drawClear: [(u) => drawBands(bands, u)],
        draw: [(u) => drawRules(rules, u)],
      },
    };
    const plot = new uPlot(opts, data, slot);
    // A click on a sample asks about it: its panel, its x and the series it belongs to.
    plot.over.addEventListener('click', () => {
      const at = plot.cursor.idx;
      if (at === null || at === undefined || typeof emitEvent !== 'function') return;
      const near = plot.series.findIndex((s, k) => k > 0 && data[k][at] !== null && data[k][at] !== undefined);
      if (near < 1) return;
      emitEvent('chart_pick', { host: state.hostId, panel: index, x: data[0][at], series: series[near - 1].id });
    });
    const [low, high] = opening(panel, data);
    plot.setScale('x', { min: low, max: high });
    return { plot, omitted, x: [low, high] };
  };

  // The key of the bands and rules a chart names; the curves are in each panel's legend.
  const keyRows = (spec) => [
    ...spec.bands.filter((b) => b.title).map((b) => ({ kind: 'band', text: b.title })),
    ...spec.rules.map((r) => ({ kind: 'rule', text: r.title })),
  ];

  const makeChart = (hostId) => ({
    hostId, host: null, slots: null, key: null, notes: null, spec: null, panels: [],
    omitted: 0, observer: null,

    build() {
      this.host = document.getElementById(this.hostId);
      this.host.classList.add('chart');
      this.slots = document.createElement('div');
      this.slots.className = 'chart-panels';
      this.key = document.createElement('ul');
      this.key.className = 'chart-key';
      this.notes = document.createElement('div');
      this.notes.className = 'chart-notes';
      this.notes.setAttribute('role', 'status');
      this.host.append(this.slots, this.key, this.notes);
      this.observer = new ResizeObserver(() => this.resized());
      this.observer.observe(this.host);
    },

    show(spec) {
      if (!this.host || !this.host.isConnected) this.build();
      this.host.dataset.chartReady = '0';
      this.spec = spec;
      this.draw();
      this.host.setAttribute('aria-label', spec.label || 'A chart');
      this.host.dataset.chartReady = '1';
    },

    draw() {
      for (const panel of this.panels) panel.plot.destroy();
      this.panels = [];
      const spec = this.spec;
      this.key.replaceChildren(...keyRows(spec).map((row) => {
        const item = document.createElement('li');
        const swatch = document.createElement('span');
        swatch.className = `chart-swatch chart-swatch-${row.kind}`;
        item.append(swatch, document.createTextNode(row.text));
        return item;
      }));
      this.key.hidden = this.key.childElementCount === 0;
      const slots = spec.panels.map((_, index) => {
        const slot = document.createElement('div');
        slot.className = 'chart-panel';
        slot.dataset.panel = String(index);
        return slot;
      });
      this.slots.replaceChildren(...slots);
      this.omitted = 0;
      // The notes first, so that the panels' share of the height is known before they draw.
      const counted = (count) => (count
        ? [`${count} sample(s) omitted: not positive, which a logarithmic axis cannot place.`] : []);
      spec.panels.forEach((_, index) => {
        this.omitted += joined(spec.panels[index], spec.series.filter((s) => s.panel === index)).omitted;
      });
      const notes = [...spec.notes, ...counted(this.omitted)];
      this.notes.textContent = notes.join(' ');
      this.notes.hidden = notes.length === 0;
      slots.forEach((slot, index) => {
        const [width, height] = this.slotSize(slot);
        this.panels.push(makePlot(this, index, slot, width, height));
      });
      this.fit();
    },

    slotSize(slot) {
      return [Math.max(slot.clientWidth, 160), Math.max(slot.clientHeight, PANEL_MIN_H)];
    },

    // Each panel's plot fills its slot, less its legend; a legend wraps to the plot's width, so
    // the fit is taken twice.
    fit() {
      for (let pass = 0; pass < 2; pass += 1) {
        this.panels.forEach((panel, index) => {
          const slot = this.slots.children[index];
          if (!slot) return;
          const [width, height] = this.slotSize(slot);
          const legend = panel.plot.root.querySelector('.u-legend');
          const legendH = legend && legend.style.display !== 'none' ? legend.offsetHeight : 0;
          panel.plot.setSize({ width, height: Math.max(height - legendH, PANEL_MIN_H) });
        });
      }
    },

    resized() {
      if (this.spec && this.host.isConnected) this.fit();
    },

    reset(index) {
      const panel = this.panels[index];
      if (panel) panel.plot.setScale('x', { min: panel.x[0], max: panel.x[1] });
    },
  });

  const charts = new Map();
  window.nano.charts = charts;
  // Draw a chart on a host, made once per host; a host built again takes a new chart. Marks the
  // screen ready when the chart is the screen's view.
  window.nano.chart = (hostId, spec, marks) => {
    for (const [id, chart] of charts) if (chart.host && !chart.host.isConnected) charts.delete(id);
    if (!document.getElementById(hostId)) return null;
    let chart = charts.get(hostId);
    if (!chart) {
      chart = makeChart(hostId);
      charts.set(hostId, chart);
    }
    chart.show(spec);
    if (marks) {
      requestAnimationFrame(() => requestAnimationFrame(() => { document.body.dataset.screenReady = '1'; }));
    }
    return chart.omitted;
  };
  // A change of theme draws every chart again in the new tokens.
  new MutationObserver(() => {
    for (const chart of charts.values()) if (chart.spec && chart.host && chart.host.isConnected) chart.draw();
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'style', 'class'] });
})();
