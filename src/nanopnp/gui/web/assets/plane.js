// The workbench's (r, z) view: one canvas per window, beside Mol*, built once and kept, which draws
// the layers the server writes (gui/web/plane.py). Equal scale, r to the right and z up; a drag pans,
// the wheel zooms about the pointer, and a pick or an edit goes back to the server by emitEvent. A
// drawing of the plot frame is a graph instead: each axis scaled alone to its extent, not panned.
(() => {
  const MARGIN = { left: 56, right: 12, top: 10, bottom: 40 };
  const ROLES = {
    contour: ['--accent', 2, []], pore: ['--canvas-plot-ink', 1.5, []],
    membrane: ['--muted', 1.5, []], exclusion: ['--changed', 1.5, [5, 3]],
    reservoir: ['--muted', 1, [6, 4]], probe: ['--warn', 1.5, [4, 3]], lumen: ['--ok', 1.5, []],
    original: ['--muted', 1.5, [3, 3]], picked: ['--accent', 3, []], domain: ['--canvas-plot-ink', 1, []],
    boundary: ['--canvas-plot-ink', 2.5, []],
  };
  // A plot: its ticks per axis, its curves' width, its rules' dash, its bands' fill, the legend's gap.
  const PLOT_TICKS = 5, CURVE_W = 2, RULE_DASH = [6, 4], BAND_ALPHA = 0.15, KEY_GAP = 12;
  // The narrowest plot the legend stands beside; a narrower one takes it inside, top right.
  const PLOT_MIN_W = 200;
  // The solids a drawing fills lightly under their outline, so a slab reads as one.
  const FILLED = ['membrane', 'pore', 'exclusion'];
  const PICK_PX = 8;
  // The key's rows: a line or a swatch, a colour bar, and the bar's width, in px.
  const KEY_ROW = 18, KEY_BAR = 46, KEY_BAR_W = 120;
  const EDGES_FROM_PX = 7;
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  // What is not picked is drawn in a grey that recedes on either theme's canvas.
  const receding = () => {
    const hex = (token('--canvas-plot') || '#ffffff').replace('#', '');
    const light = hex.length >= 6 && parseInt(hex.slice(0, 2), 16) > 128;
    return light ? '#d8d8d8' : '#4a4d55';
  };
  const frames = () => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));

  const view = {
    // How many times the canvas was built in this window: the frame builds it once (VER-78 m).
    builds: 0,
    host: null, canvas: null, notes: null, fitButton: null, drawing: null, frame: undefined,
    images: new Map(), paths: new WeakMap(), picked: null,
    // The latest drawing asked for: an earlier request that answers later is dropped.
    asked: 0,
    // The mesh the canvas holds, its hash with its vertices, triangles and materials, which a
    // drawing of the same mesh leaves out; and its paths by colouring and focus.
    meshHeld: null, meshPaths: new Map(),
    // The view: the point at the plot's centre, in nm, and the pixels per nm.
    centre: [0, 0], scale: 1, fitted: false, drag: null,

    build() {
      this.builds += 1;
      this.host = document.getElementById('plane');
      this.canvas = document.createElement('canvas');
      this.canvas.tabIndex = 0;
      this.canvas.setAttribute('role', 'img');
      this.notes = document.createElement('div');
      this.notes.className = 'plane-notes';
      this.notes.setAttribute('role', 'status');
      const fit = document.createElement('button');
      fit.type = 'button';
      fit.className = 'plane-fit';
      fit.textContent = 'Fit';
      fit.title = 'Fit the drawing to the view';
      fit.dataset.control = 'plane-fit';
      fit.addEventListener('click', () => { if (this.drawing) { this.fit(this.drawing.extent_nm); this.draw(); } });
      this.fitButton = fit;
      this.host.append(this.canvas, this.notes, fit);
      new ResizeObserver(() => this.resized()).observe(this.host);
      // The theme sets the root's attributes, and the canvas draws in its tokens.
      new MutationObserver(() => this.draw()).observe(document.documentElement, {
        attributes: true, attributeFilter: ['data-theme', 'style', 'class'],
      });
      this.canvas.addEventListener('pointerdown', (e) => this.down(e));
      this.canvas.addEventListener('pointermove', (e) => this.move(e));
      this.canvas.addEventListener('pointerup', (e) => this.up(e));
      this.canvas.addEventListener('wheel', (e) => this.wheel(e), { passive: false });
      this.canvas.addEventListener('dblclick', (e) => this.insert(e));
      this.canvas.addEventListener('keydown', (e) => this.key(e));
    },

    // Show a drawing the server writes, building the canvas the first time; null shows the note.
    async show(url, note) {
      document.body.dataset.screenReady = '0';
      if (this.canvas === null) this.build();
      const asked = ++this.asked;
      let drawing = null;
      try {
        if (url) {
          drawing = await this.fetchDrawing(url, true);
          // A mesh left out that the canvas no longer holds is asked for whole.
          if (drawing.layers.some((l) => l.kind === 'mesh' && !l.vertices_nm && !this.holds(l))) {
            drawing = await this.fetchDrawing(url, false);
          }
          for (const layer of drawing.layers) if (layer.kind === 'mesh') this.holdMesh(layer);
        }
      } catch (error) {
        console.error(`the (r, z) drawing ${url} was refused: ${error}`);
      }
      drawing = drawing || {
        frame: null, axes: ['r (nm)', 'z (nm)'], extent_nm: [-1, 10, -10, 10], layers: [],
        notes: note ? [note] : [],
      };
      await Promise.all(drawing.layers.filter((l) => l.kind === 'image').map((l) => this.image(l.url)));
      if (asked !== this.asked) return;
      // The view keeps its pan and zoom unless the frame changes, or the drawing first has
      // something to frame.
      const framed = Boolean(this.drawing && this.drawing.framed);
      if (drawing.frame !== this.frame || (!framed && drawing.framed)) this.fitted = false;
      this.frame = drawing.frame;
      this.drawing = drawing;
      this.picked = null;
      this.notes.textContent = drawing.notes.join(' ');
      this.notes.hidden = drawing.notes.length === 0;
      // A plot is always fitted to its extent: there is nothing to fit back to.
      this.fitButton.hidden = drawing.frame === 'plot';
      const named = drawing.frame === 'plot'
        ? `Plot of ${drawing.axes[1]} against ${drawing.axes[0]}`
        : `(r, z) view, ${drawing.axes.join(' against ')}`;
      this.canvas.setAttribute('aria-label', `${named}`
        + `: ${drawing.layers.map((l) => l.id).join(', ') || 'nothing drawn'}`);
      // The host may have been shown in this same update: its size settles a frame later.
      await frames();
      this.resized();
      await frames();
      if (asked === this.asked) document.body.dataset.screenReady = '1';
    },

    async image(url) {
      if (this.images.has(url)) return;
      const picture = new Image();
      picture.src = url;
      try {
        await picture.decode();
        this.images.set(url, picture);
      } catch (error) {
        console.error(`the picture ${url} was refused: ${error}`);
      }
    },

    resized() {
      if (this.canvas === null) return;
      const { width, height } = this.host.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      const ratio = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(width * ratio);
      this.canvas.height = Math.round(height * ratio);
      this.canvas.style.width = `${width}px`;
      this.canvas.style.height = `${height}px`;
      if (!this.fitted && this.drawing) this.fit(this.drawing.extent_nm);
      this.draw();
    },

    plot() {
      const ratio = window.devicePixelRatio || 1;
      const width = this.canvas.width / ratio, height = this.canvas.height / ratio;
      return {
        x: MARGIN.left, y: MARGIN.top,
        w: Math.max(width - MARGIN.left - MARGIN.right, 1),
        h: Math.max(height - MARGIN.top - MARGIN.bottom, 1),
      };
    },

    fit([r0, r1, z0, z1]) {
      const area = this.plot();
      this.scale = Math.min(area.w / Math.max(r1 - r0, 1e-9), area.h / Math.max(z1 - z0, 1e-9));
      this.centre = [(r0 + r1) / 2, (z0 + z1) / 2];
      this.fitted = true;
    },

    toScreen(r, z) {
      const area = this.plot();
      return [area.x + area.w / 2 + (r - this.centre[0]) * this.scale,
        area.y + area.h / 2 - (z - this.centre[1]) * this.scale];
    },

    toData(x, y) {
      const area = this.plot();
      return [this.centre[0] + (x - area.x - area.w / 2) / this.scale,
        this.centre[1] - (y - area.y - area.h / 2) / this.scale];
    },

    async fetchDrawing(url, naming) {
      const held = naming && this.meshHeld ? this.meshHeld.mesh : '';
      const asked = held ? `${url}${url.includes('?') ? '&' : '?'}held=${encodeURIComponent(held)}` : url;
      const response = await fetch(asked, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
      return response.json();
    },

    holds(layer) {
      return this.meshHeld !== null && this.meshHeld.mesh === layer.mesh;
    },

    // Keep a mesh sent whole, or fill one left out from the mesh held.
    holdMesh(layer) {
      if (layer.vertices_nm) {
        if (!this.holds(layer)) this.meshPaths.clear();
        const { mesh, vertices_nm, triangles, material } = layer;
        this.meshHeld = { mesh, vertices_nm, triangles, material };
      } else {
        const { vertices_nm, triangles, material } = this.meshHeld;
        Object.assign(layer, { vertices_nm, triangles, material });
      }
    },

    // A layer's outline or triangles as paths in nm, built once per layer; a mesh's once per
    // colouring and focus, so a pick or a histogram's bar redraws without building them again.
    pathsOf(layer) {
      let found = this.paths.get(layer);
      if (found) return found;
      const keyed = layer.kind === 'mesh' ? `${layer.mesh} ${layer.colour} ${layer.focus ?? ''}` : '';
      found = (keyed && this.meshPaths.get(keyed)) || this.buildPaths(layer);
      if (keyed) this.meshPaths.set(keyed, found);
      this.paths.set(layer, found);
      return found;
    },

    buildPaths(layer) {
      if (layer.kind === 'mesh') {
        const v = layer.vertices_nm, t = layer.triangles, byColour = new Map();
        let edges = 0;
        for (let k = 0; k < t.length; k += 3) {
          // A picked domain keeps its colours; the rest is one key the draw greys.
          const faded = layer.focus !== undefined && layer.material[k / 3] !== layer.focus;
          const colour = faded ? 'dim' : this.colourOf(layer, layer.values[k / 3]);
          if (!byColour.has(colour)) byColour.set(colour, new Path2D());
          const path = byColour.get(colour);
          const [a, b, c] = [t[k] * 2, t[k + 1] * 2, t[k + 2] * 2];
          path.moveTo(v[a], v[a + 1]); path.lineTo(v[b], v[b + 1]); path.lineTo(v[c], v[c + 1]);
          path.closePath();
          edges += Math.hypot(v[b] - v[a], v[b + 1] - v[a + 1]);
        }
        return { byColour, edge_nm: t.length ? edges / (t.length / 3) : 0 };
      }
      const path = new Path2D();
      if (layer.kind === 'domain') {
        for (const ring of layer.rings) {
          for (let k = 0; k < ring.length; k += 2) {
            if (k === 0) path.moveTo(ring[0], ring[1]); else path.lineTo(ring[k], ring[k + 1]);
          }
          path.closePath();
        }
        return { path };
      }
      const p = layer.points_nm;
      // A line of segments holds each segment's two ends in turn, not one chain of points.
      for (let k = 0; k < p.length; k += layer.segments ? 4 : 2) {
        if (layer.segments) {
          path.moveTo(p[k], p[k + 1]);
          path.lineTo(p[k + 2], p[k + 3]);
        } else if (k === 0) path.moveTo(p[0], p[1]); else path.lineTo(p[k], p[k + 1]);
      }
      if (layer.kind === 'polygon') path.closePath();
      return { path };
    },

    colourOf(layer, value) {
      const palette = layer.palette;
      if (layer.categorical) return palette[value] || '#cccccc';
      const [low, high] = layer.scale;
      const share = Math.min(Math.max((value - low) / ((high - low) || 1), 0), 1);
      return palette[Math.round(share * (palette.length - 1))];
    },

    draw() {
      if (this.canvas === null || this.drawing === null || this.canvas.width === 0) return;
      const ctx = this.canvas.getContext('2d');
      const ratio = window.devicePixelRatio || 1;
      const area = this.plot();
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      ctx.fillStyle = token('--canvas-plot') || '#ffffff';
      ctx.fillRect(0, 0, this.canvas.width / ratio, this.canvas.height / ratio);
      this.boxes = [];
      if (this.drawing.frame === 'plot') {
        this.drawPlot(ctx, area);
        return;
      }
      ctx.save();
      ctx.beginPath();
      ctx.rect(area.x, area.y, area.w, area.h);
      ctx.clip();
      const layers = this.drawing.layers;
      for (const layer of layers) if (layer.kind !== 'label' && !layer.hidden) this.layer(ctx, layer, ratio);
      for (const layer of layers) {
        if (layer.kind !== 'domain' || !layer.picked) continue;
        this.inData(ctx, ratio, () => {
          ctx.strokeStyle = token('--accent') || '#5b3fd6';
          ctx.lineWidth = 3 / this.scale;
          ctx.setLineDash([]);
          ctx.stroke(this.pathsOf(layer).path);
        });
      }
      this.highlight(ctx);
      ctx.restore();
      this.axes(ctx, area);
      // The key is laid out first, so that a label at the top right moves below it.
      this.key = this.keyLayout(ctx, area);
      for (const layer of layers) if (layer.kind === 'label') this.label(ctx, layer, area);
      this.legend(ctx);
    },

    // Data in nm drawn under the view's transform: a pixel is 1 / scale nm.
    inData(ctx, ratio, paint) {
      const [ox, oy] = this.toScreen(0, 0);
      ctx.save();
      ctx.setTransform(ratio * this.scale, 0, 0, -ratio * this.scale, ratio * ox, ratio * oy);
      paint();
      ctx.restore();
    },

    layer(ctx, layer, ratio) {
      if (layer.kind === 'image') {
        const picture = this.images.get(layer.url);
        if (!picture) return;
        const [x0, x1, z0, z1] = layer.extent_nm;
        const [left, top] = this.toScreen(x0, z1);
        const [right, bottom] = this.toScreen(x1, z0);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(picture, left, top, right - left, bottom - top);
        return;
      }
      const drawn = this.pathsOf(layer);
      if (layer.kind === 'mesh') {
        const edges = drawn.edge_nm * this.scale >= EDGES_FROM_PX;
        this.inData(ctx, ratio, () => {
          for (const [colour, path] of drawn.byColour) {
            ctx.fillStyle = colour === 'dim' ? receding() : colour;
            ctx.fill(path);
            if (edges) {
              ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)';
              ctx.lineWidth = 0.5 / this.scale;
              ctx.stroke(path);
            }
          }
          if (layer.outlined && layer.outlined.length) {
            // A histogram's bar: every other element recedes under a wash of the canvas's colour,
            // and the bar's own are filled again in their colours, edged as the mesh is: the
            // accent is kept for what is picked, and a bar holds most of a mesh.
            const v = layer.vertices_nm, t = layer.triangles, band = new Path2D();
            const [r0, z0] = this.toData(0, this.canvas.height);
            const [r1, z1] = this.toData(this.canvas.width, 0);
            ctx.globalAlpha = 0.7;
            ctx.fillStyle = token('--canvas-plot') || '#ffffff';
            ctx.fillRect(r0, z0, r1 - r0, z1 - z0);
            ctx.globalAlpha = 1;
            for (const index of layer.outlined) {
              const [a, b, c] = [t[3 * index] * 2, t[3 * index + 1] * 2, t[3 * index + 2] * 2];
              const one = new Path2D();
              for (const target of [one, band]) {
                target.moveTo(v[a], v[a + 1]); target.lineTo(v[b], v[b + 1]); target.lineTo(v[c], v[c + 1]);
                target.closePath();
              }
              ctx.fillStyle = this.colourOf(layer, layer.values[index]);
              ctx.fill(one);
            }
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)';
            ctx.lineWidth = 0.5 / this.scale;
            ctx.stroke(band);
          }
        });
        return;
      }
      const [colour, width, dash] = this.lineStyle(layer);
      if (layer.kind === 'domain') {
        this.inData(ctx, ratio, () => {
          if (layer.filled) {
            ctx.globalAlpha = layer.picked ? 0.9 : 0.55;
            ctx.fillStyle = layer.fill;
            ctx.fill(drawn.path, 'evenodd');
            ctx.globalAlpha = 1;
          }
          ctx.lineJoin = 'round';
          ctx.setLineDash([]);
          if (!layer.filled) {
            ctx.strokeStyle = token('--canvas-plot') || '#ffffff';
            ctx.lineWidth = (width + 3) / this.scale;
            ctx.stroke(drawn.path);
          }
          ctx.strokeStyle = colour;
          ctx.lineWidth = width / this.scale;
          ctx.stroke(drawn.path);
        });
        return;
      }
      this.inData(ctx, ratio, () => {
        const meshed = this.drawing.layers.some((l) => l.kind === 'mesh');
        const pictured = meshed || this.drawing.layers.some((l) => l.kind === 'image');
        if (layer.kind === 'polygon' && FILLED.includes(layer.role) && !meshed) {
          ctx.globalAlpha = 0.22;
          ctx.fillStyle = colour;
          ctx.fill(drawn.path);
          ctx.globalAlpha = 1;
        }
        ctx.lineJoin = 'round';
        // Segments drawn each alone meet as one line where their round ends overlap.
        if (layer.segments) ctx.lineCap = 'round';
        // Over a picture or a mesh a line takes a halo in the canvas's colour, so it reads on any.
        if (pictured) {
          ctx.strokeStyle = token('--canvas-plot') || '#ffffff';
          ctx.lineWidth = (width + 3) / this.scale;
          ctx.setLineDash([]);
          ctx.stroke(drawn.path);
        }
        ctx.strokeStyle = colour;
        ctx.lineWidth = width / this.scale;
        ctx.setLineDash(dash.map((d) => d / this.scale));
        ctx.stroke(drawn.path);
      });
      if (layer.role === 'contour') this.vertices(ctx, layer);
    },

    // A line's colour, width and dash: its role's, unless it names its own colour; a plot's curve
    // is a solid line in its colour, and its rule a dashed one in the canvas's ink.
    lineStyle(layer) {
      const ink = token('--canvas-plot-ink') || '#16181d';
      if (layer.kind === 'rule') return [ink, 1.5, RULE_DASH];
      if (layer.kind === 'line' && !layer.role) return [layer.colour || ink, CURVE_W, []];
      const [colour, width, dash] = ROLES[layer.role] || ['--canvas-plot-ink', 1.5, []];
      return [layer.colour || token(colour) || ink, width, dash];
    },

    // A plot: its extent fills the plot area, each axis scaled alone; the bands first, then the
    // rules, then the curves over both.
    drawPlot(ctx, area) {
      this.key = this.keyLayout(ctx, area);
      if (this.key && area.w - this.key.width - KEY_GAP >= PLOT_MIN_W) {
        // The legend stands beside the plot, where it hides no curve.
        area.w -= this.key.width + KEY_GAP;
        this.key.x = area.x + area.w + KEY_GAP;
        this.key.top = area.y;
      }
      const [x0, x1, y0, y1] = this.drawing.extent_nm;
      const sx = area.w / ((x1 - x0) || 1), sy = area.h / ((y1 - y0) || 1);
      const at = (x, y) => [area.x + (x - x0) * sx, area.y + area.h - (y - y0) * sy];
      const layers = this.drawing.layers;
      ctx.save();
      ctx.beginPath();
      // A curve along the frame's top or bottom is drawn whole, not halved by the clip.
      ctx.rect(area.x, area.y - CURVE_W, area.w, area.h + 2 * CURVE_W);
      ctx.clip();
      ctx.fillStyle = token('--canvas-plot-ink') || '#16181d';
      ctx.globalAlpha = BAND_ALPHA;
      for (const layer of layers) {
        if (layer.kind !== 'band') continue;
        const [left] = at(layer.x[0], y0), [right] = at(layer.x[1], y0);
        ctx.fillRect(left, area.y, right - left, area.h);
      }
      ctx.globalAlpha = 1;
      ctx.lineJoin = 'round';
      for (const kind of ['rule', 'line']) {
        for (const layer of layers) {
          if (layer.kind !== kind) continue;
          const [colour, width, dash] = this.lineStyle(layer);
          ctx.strokeStyle = colour;
          ctx.lineWidth = width;
          ctx.setLineDash(dash);
          ctx.beginPath();
          if (kind === 'rule') {
            const [x] = at(layer.x, y0);
            ctx.moveTo(x, area.y);
            ctx.lineTo(x, area.y + area.h);
          } else {
            const p = layer.points_nm;
            for (let k = 0; k < p.length; k += 2) {
              const [x, y] = at(p[k], p[k + 1]);
              if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
            }
          }
          ctx.stroke();
        }
      }
      ctx.restore();
      const ticks = (low, high, place) => Array.from({ length: PLOT_TICKS }, (_, k) => {
        const value = low + (k * (high - low)) / (PLOT_TICKS - 1);
        return [place(value), Number(value.toPrecision(6)).toString().replace('-', '−')];
      });
      this.frameAxes(ctx, area, ticks(x0, x1, (x) => at(x, y0)[0]), ticks(y0, y1, (y) => at(x0, y)[1]));
      this.legend(ctx);
    },

    // An outline's vertices, once they stand apart on the screen.
    vertices(ctx, layer) {
      const p = layer.points_nm;
      if (p.length < 4) return;
      const apart = Math.hypot(p[2] - p[0], p[3] - p[1]) * this.scale;
      // An edit always shows its handles, smaller where they crowd; a built outline only once
      // they stand apart.
      if (apart < 6 && !layer.editable) return;
      const size = apart < 6 ? 3 : 5;
      ctx.fillStyle = token('--accent') || '#5b3fd6';
      for (let k = 0; k < p.length; k += 2) {
        const [x, y] = this.toScreen(p[k], p[k + 1]);
        ctx.fillRect(x - size / 2, y - size / 2, size, size);
      }
    },

    highlight(ctx) {
      const picked = this.picked;
      if (!picked) return;
      const layer = this.drawing.layers.find((l) => l.id === picked.layer);
      // A domain picked is drawn by the server's next drawing.
      if (!layer || layer.kind === 'domain') return;
      ctx.strokeStyle = token('--accent') || '#5b3fd6';
      ctx.lineWidth = 2;
      ctx.setLineDash([]);
      if (layer.kind === 'mesh') {
        const v = layer.vertices_nm, t = layer.triangles, k = picked.index * 3;
        ctx.beginPath();
        for (let j = 0; j < 3; j += 1) {
          const [x, y] = this.toScreen(v[t[k + j] * 2], v[t[k + j] * 2 + 1]);
          if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
      } else {
        const p = layer.points_nm;
        const [x, y] = this.toScreen(p[picked.index * 2], p[picked.index * 2 + 1]);
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.stroke();
      }
    },

    step(span) {
      const rough = span / 6, power = 10 ** Math.floor(Math.log10(rough));
      return [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) || power * 10;
    },

    axes(ctx, area) {
      const [r0, z0] = this.toData(area.x, area.y + area.h);
      const [r1, z1] = this.toData(area.x + area.w, area.y);
      const rStep = this.step(r1 - r0), zStep = this.step(z1 - z0);
      const shown = (value, step) => (Math.abs(value) < step / 1e6 ? 0 : value)
        .toFixed(Math.max(0, -Math.floor(Math.log10(step)))).replace('-', '−');
      const rTicks = [], zTicks = [];
      for (let r = Math.ceil(r0 / rStep) * rStep; r <= r1; r += rStep) {
        rTicks.push([this.toScreen(r, 0)[0], shown(r, rStep)]);
      }
      for (let z = Math.ceil(z0 / zStep) * zStep; z <= z1; z += zStep) {
        zTicks.push([this.toScreen(0, z)[1], shown(z, zStep)]);
      }
      this.frameAxes(ctx, area, rTicks, zTicks);
    },

    // The plot area's frame, each axis's ticks as [pixel, text], and the axes' titles.
    frameAxes(ctx, area, xTicks, yTicks) {
      const ink = token('--canvas-plot-ink') || '#16181d';
      ctx.strokeStyle = ink;
      ctx.fillStyle = ink;
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.strokeRect(area.x + 0.5, area.y + 0.5, area.w - 1, area.h - 1);
      ctx.font = `12px ${token('--font-num') || 'monospace'}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      for (const [x, text] of xTicks) {
        ctx.beginPath(); ctx.moveTo(x, area.y + area.h); ctx.lineTo(x, area.y + area.h + 4); ctx.stroke();
        ctx.fillText(text, x, area.y + area.h + 6);
      }
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      for (const [y, text] of yTicks) {
        ctx.beginPath(); ctx.moveTo(area.x - 4, y); ctx.lineTo(area.x, y); ctx.stroke();
        ctx.fillText(text, area.x - 6, y);
      }
      ctx.font = `12px ${token('--font-ui') || 'sans-serif'}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(this.drawing.axes[0], area.x + area.w / 2, area.y + area.h + MARGIN.bottom - 2);
      ctx.save();
      ctx.translate(14, area.y + area.h / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.textBaseline = 'middle';
      ctx.fillText(this.drawing.axes[1], 0, 0);
      ctx.restore();
    },

    // A value's label: its name in the interface's face and its number in the numbers' (WB-21).
    label(ctx, layer, area) {
      let [x, y] = this.toScreen(layer.anchor_nm[0], layer.anchor_nm[1]);
      const name = `${layer.name} `;
      const number = `${layer.value} ${layer.unit}`.replace('-', '−');
      const ui = `12px ${token('--font-ui') || 'sans-serif'}`;
      const num = `12px ${token('--font-num') || 'monospace'}`;
      ctx.font = ui;
      const named = ctx.measureText(name).width;
      ctx.font = num;
      const width = named + ctx.measureText(number).width + 10;
      x = Math.min(Math.max(x, area.x + 2), area.x + area.w - width - 2);
      y = Math.min(Math.max(y, area.y + 12), area.y + area.h - 12);
      const key = this.key;
      if (key && x < key.x + key.width && x + width > key.x && y - 10.5 < key.top + key.height
        && y + 10.5 > key.top) {
        y = key.top + key.height + 16;
      }
      ctx.fillStyle = token('--panel') || '#ffffff';
      ctx.strokeStyle = token('--control-edge') || '#7c8290';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.rect(x + 0.5, y - 10.5, width, 21);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = token('--ink') || '#16181d';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.font = ui;
      ctx.fillText(name, x + 5, y);
      ctx.font = num;
      ctx.fillText(number, x + 5 + named, y);
      this.boxes.push({ x, y: y - 10.5, w: width, h: 21, layer });
    },

    // A value typed on the drawing: its label opens a field in place, and Enter sends it.
    typeValue(box) {
      const field = document.createElement('input');
      field.type = 'number';
      field.step = 'any';
      field.value = box.layer.value;
      field.className = 'plane-field';
      field.setAttribute('aria-label', `${box.layer.name}, in ${box.layer.unit}`);
      Object.assign(field.style, { left: `${box.x}px`, top: `${box.y}px`, width: `${Math.max(box.w, 120)}px` });
      this.host.append(field);
      field.focus();
      field.select();
      let closed = false;
      const done = (send) => {
        // Removing the field blurs it, which would close it a second time.
        if (closed) return;
        closed = true;
        const value = Number(field.value);
        field.remove();
        if (send && field.value !== '' && Number.isFinite(value) && value !== box.layer.value) {
          this.emit('plane_value', { path: box.layer.path, value });
        }
        this.canvas.focus();
      };
      field.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') done(true);
        if (e.key === 'Escape') done(false);
      });
      field.addEventListener('blur', () => done(false));
    },

    // The key: what each colour and line of the drawing stands for, on a panel at the top right.
    keyLayout(ctx, area) {
      const entries = [];
      const titles = new Set();
      for (const layer of this.drawing.layers) {
        if (layer.hidden) continue;
        if (layer.kind === 'image' && layer.bar) {
          entries.push({ kind: 'bar', ...layer.bar });
        } else if (layer.kind === 'mesh' && layer.categorical) {
          layer.legend.forEach((name, index) => entries.push({
            // The material's name as the tree and Region write it.
            kind: 'swatch', text: name.charAt(0).toUpperCase() + name.slice(1),
            colour: layer.focus !== undefined && layer.focus !== index ? receding() : layer.palette[index],
          }));
        } else if (layer.kind === 'mesh') {
          entries.push({ kind: 'bar', quantity: layer.colour.toUpperCase(), unit: 'no unit',
            low: layer.scale[0], high: layer.scale[1], palette: layer.palette });
        } else if (layer.kind === 'domain' && layer.filled) {
          entries.push({
            kind: 'swatch', text: layer.title, colour: layer.fill, alpha: layer.picked ? 0.9 : 0.55,
          });
        } else if (layer.kind === 'band') {
          entries.push({
            kind: 'swatch', text: layer.title, colour: token('--canvas-plot-ink') || '#16181d',
            alpha: BAND_ALPHA,
          });
        } else if (layer.title && layer.kind !== 'domain' && !titles.has(layer.title)) {
          titles.add(layer.title);
          entries.push({ kind: 'line', text: layer.title, style: this.lineStyle(layer) });
        }
      }
      if (!entries.length) return null;
      ctx.font = `12px ${token('--font-ui') || 'sans-serif'}`;
      let width = 0, height = 8;
      for (const entry of entries) {
        if (entry.kind === 'bar') {
          width = Math.max(width, KEY_BAR_W + 8, ctx.measureText(entry.quantity).width + 8,
            ctx.measureText(entry.unit).width + 8);
          height += KEY_BAR;
        } else {
          width = Math.max(width, ctx.measureText(entry.text).width + 32);
          height += KEY_ROW;
        }
      }
      width += 8;
      return { entries, width, height, x: area.x + area.w - width - 6, top: area.y + 6 };
    },

    legend(ctx) {
      if (!this.key) return;
      const { entries, width, height, x, top } = this.key;
      const ui = token('--font-ui') || 'sans-serif';
      // The key stands on the panel's colour, so it reads over any picture or element.
      ctx.fillStyle = token('--panel') || '#ffffff';
      ctx.strokeStyle = token('--control-edge') || '#7c8290';
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.fillRect(x, top, width, height);
      ctx.strokeRect(x + 0.5, top + 0.5, width - 1, height - 1);
      const text = token('--ink') || '#16181d';
      const edge = token('--colourbar-outline') || token('--canvas-plot-ink') || '#16181d';
      const shown = (value) => Number(value.toPrecision(3)).toString().replace('-', '−');
      let y = top + 4;
      ctx.textBaseline = 'middle';
      for (const entry of entries) {
        ctx.textAlign = 'left';
        if (entry.kind === 'bar') {
          ctx.fillStyle = text;
          ctx.font = `12px ${ui}`;
          ctx.fillText(entry.quantity, x + 6, y + 7);
          const steps = entry.palette.length;
          for (let k = 0; k < steps; k += 1) {
            ctx.fillStyle = entry.palette[k];
            ctx.fillRect(x + 6 + (k * KEY_BAR_W) / steps, y + 15, KEY_BAR_W / steps + 0.5, 9);
          }
          ctx.strokeStyle = edge;
          ctx.strokeRect(x + 6.5, y + 15.5, KEY_BAR_W, 9);
          ctx.fillStyle = text;
          ctx.font = `12px ${token('--font-num') || 'monospace'}`;
          ctx.fillText(shown(entry.low), x + 6, y + 31);
          ctx.textAlign = 'right';
          ctx.fillText(shown(entry.high), x + 6 + KEY_BAR_W, y + 31);
          ctx.textAlign = 'left';
          ctx.font = `12px ${ui}`;
          ctx.fillText(entry.unit, x + 6, y + 41);
          y += KEY_BAR;
          continue;
        }
        ctx.font = `12px ${ui}`;
        if (entry.kind === 'swatch') {
          // A domain's swatch is laid over the canvas's colour as its fill is, so they match.
          if (entry.alpha !== undefined) {
            ctx.fillStyle = token('--canvas-plot') || '#ffffff';
            ctx.fillRect(x + 6, y + 3, 12, 12);
            ctx.globalAlpha = entry.alpha;
          }
          ctx.fillStyle = entry.colour;
          ctx.fillRect(x + 6, y + 3, 12, 12);
          ctx.globalAlpha = 1;
          ctx.strokeStyle = edge;
          ctx.strokeRect(x + 6.5, y + 3.5, 12, 12);
        } else {
          const [colour, lineWidth, dash] = entry.style;
          ctx.strokeStyle = colour;
          ctx.lineWidth = lineWidth;
          ctx.setLineDash(dash);
          ctx.beginPath();
          ctx.moveTo(x + 4, y + 9);
          ctx.lineTo(x + 22, y + 9);
          ctx.stroke();
          ctx.setLineDash([]);
        }
        ctx.fillStyle = text;
        ctx.fillText(entry.text, x + 28, y + 9);
        y += KEY_ROW;
      }
    },

    // Which domain a point in nm falls in, the smallest first: the server sends them so.
    domainAt(r, z) {
      this.probe = this.probe || document.createElement('canvas').getContext('2d');
      for (const layer of this.drawing.layers) {
        if (layer.kind !== 'domain') continue;
        if (this.probe.isPointInPath(this.pathsOf(layer).path, r, z, 'evenodd')) {
          return { layer: layer.id, index: 0 };
        }
      }
      return null;
    },

    // -- picks and edits ----------------------------------------------------------

    nearestVertex(x, y) {
      let best = null;
      for (const layer of this.drawing.layers) {
        if (layer.role !== 'contour') continue;
        const p = layer.points_nm;
        for (let k = 0; k < p.length; k += 2) {
          const [vx, vy] = this.toScreen(p[k], p[k + 1]);
          const d = Math.hypot(vx - x, vy - y);
          if (d <= PICK_PX && (!best || d < best.d)) best = { layer: layer.id, index: k / 2, d };
        }
      }
      return best;
    },

    triangleAt(r, z) {
      const mesh = this.drawing.layers.find((l) => l.kind === 'mesh');
      if (!mesh) return null;
      const v = mesh.vertices_nm, t = mesh.triangles;
      for (let k = 0; k < t.length; k += 3) {
        const [ax, ay, bx, by, cx, cy] = [v[t[k] * 2], v[t[k] * 2 + 1], v[t[k + 1] * 2],
          v[t[k + 1] * 2 + 1], v[t[k + 2] * 2], v[t[k + 2] * 2 + 1]];
        const d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
        const s = ((by - cy) * (r - cx) + (cx - bx) * (z - cy)) / d;
        const u = ((cy - ay) * (r - cx) + (ax - cx) * (z - cy)) / d;
        if (s >= 0 && u >= 0 && s + u <= 1) return { layer: mesh.id, index: k / 3 };
      }
      return null;
    },

    emit(name, args) {
      if (typeof emitEvent === 'function') emitEvent(name, args);
    },

    point(event) {
      const box = this.canvas.getBoundingClientRect();
      return [event.clientX - box.left, event.clientY - box.top];
    },

    // A plot is neither panned nor zoomed, and holds nothing to pick.
    plotted() {
      return Boolean(this.drawing && this.drawing.frame === 'plot');
    },

    down(event) {
      if (this.plotted()) return;
      this.canvas.setPointerCapture(event.pointerId);
      this.drag = { start: this.point(event), centre: [...this.centre], moved: false };
    },

    move(event) {
      if (!this.drag) return;
      const [x, y] = this.point(event);
      const [dx, dy] = [x - this.drag.start[0], y - this.drag.start[1]];
      if (!this.drag.moved && Math.hypot(dx, dy) < 3) return;
      this.drag.moved = true;
      this.centre = [this.drag.centre[0] - dx / this.scale, this.drag.centre[1] + dy / this.scale];
      this.draw();
    },

    up(event) {
      const drag = this.drag;
      this.drag = null;
      if (!drag || drag.moved || !this.drawing) return;
      const [x, y] = this.point(event);
      const box = (this.boxes || []).find((b) => x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h);
      if (box) {
        this.typeValue(box);
        return;
      }
      const at = this.toData(x, y);
      const picked = this.nearestVertex(x, y) || this.triangleAt(...at) || this.domainAt(...at);
      this.picked = picked ? { layer: picked.layer, index: picked.index } : null;
      this.draw();
      if (this.picked) this.emit('plane_pick', this.picked);
    },

    wheel(event) {
      // Over a plot the wheel scrolls the page.
      if (this.plotted()) return;
      event.preventDefault();
      const [x, y] = this.point(event);
      const [r, z] = this.toData(x, y);
      this.scale *= Math.exp(-event.deltaY * 0.0015);
      const [r2, z2] = this.toData(x, y);
      this.centre = [this.centre[0] + r - r2, this.centre[1] + z - z2];
      this.draw();
    },

    insert(event) {
      if (!this.drawing) return;
      const [x, y] = this.point(event);
      for (const layer of this.drawing.layers) {
        if (layer.role !== 'contour' || !layer.editable) continue;
        const p = layer.points_nm, n = p.length / 2;
        for (let k = 0; k < n; k += 1) {
          const [ax, ay] = this.toScreen(p[2 * k], p[2 * k + 1]);
          const [bx, by] = this.toScreen(p[(2 * k + 2) % p.length], p[(2 * k + 3) % p.length]);
          const length = Math.hypot(bx - ax, by - ay) || 1;
          const along = ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / (length * length);
          const off = Math.abs((x - ax) * (by - ay) - (y - ay) * (bx - ax)) / length;
          if (along > 0 && along < 1 && off <= PICK_PX) {
            this.emit('plane_insert', { layer: layer.id, edge: k });
            return;
          }
        }
      }
    },

    key(event) {
      const picked = this.picked;
      if (!picked || !['Delete', 'Backspace'].includes(event.key)) return;
      const layer = this.drawing.layers.find((l) => l.id === picked.layer);
      if (!layer || !layer.editable) return;
      event.preventDefault();
      this.emit('plane_delete', { layer: layer.id, index: picked.index });
    },
  };

  window.nano.canvas = view;
  window.nano.plane = (url, note) => view.show(url, note);
})();
