// The Continuum suite's (r, z) view: one canvas per window, beside Mol*, built once and kept, which
// draws the layers the server writes (gui/web/plane.py). Equal scale, r to the right and z up; a drag
// pans, the wheel zooms about the pointer, and a pick or an edit goes back to the server by emitEvent.
(() => {
  const MARGIN = { left: 56, right: 12, top: 10, bottom: 40 };
  const ROLES = {
    contour: ['--accent', 2, []], pore: ['--canvas-plot-ink', 1.5, []],
    membrane: ['--muted', 1.5, []], exclusion: ['--changed', 1.5, [5, 3]],
    reservoir: ['--muted', 1, [6, 4]], probe: ['--warn', 1.5, [4, 3]], lumen: ['--ok', 1.5, []],
  };
  // The solids a drawing fills lightly under their outline, so a slab reads as one.
  const FILLED = ['membrane', 'pore', 'exclusion'];
  const PICK_PX = 8;
  const EDGES_FROM_PX = 7;
  const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const frames = () => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));

  const view = {
    // How many times the canvas was built in this window: the frame builds it once (VER-78 m).
    builds: 0,
    host: null, canvas: null, notes: null, drawing: null, frame: undefined,
    images: new Map(), paths: new WeakMap(), picked: null,
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
      this.host.append(this.canvas, this.notes);
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
      let drawing = null;
      try {
        if (url) {
          const response = await fetch(url, { credentials: 'same-origin', cache: 'no-store' });
          if (!response.ok) throw new Error(`${response.status} ${await response.text()}`);
          drawing = await response.json();
        }
      } catch (error) {
        console.error(`the (r, z) drawing ${url} was refused: ${error}`);
      }
      drawing = drawing || {
        frame: null, axes: ['r (nm)', 'z (nm)'], extent_nm: [-1, 10, -10, 10], layers: [],
        notes: note ? [note] : [],
      };
      await Promise.all(drawing.layers.filter((l) => l.kind === 'image').map((l) => this.image(l.url)));
      if (drawing.frame !== this.frame) this.fitted = false;
      this.frame = drawing.frame;
      this.drawing = drawing;
      this.picked = null;
      this.notes.textContent = drawing.notes.join(' ');
      this.notes.hidden = drawing.notes.length === 0;
      this.canvas.setAttribute('aria-label', `(r, z) view, ${drawing.axes.join(' against ')}`
        + `: ${drawing.layers.map((l) => l.id).join(', ') || 'nothing drawn'}`);
      // The host may have been shown in this same update: its size settles a frame later.
      await frames();
      this.resized();
      await frames();
      document.body.dataset.screenReady = '1';
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

    // A layer's outline or triangles as paths in nm, built once per layer.
    pathsOf(layer) {
      let found = this.paths.get(layer);
      if (found) return found;
      if (layer.kind === 'mesh') {
        const v = layer.vertices_nm, t = layer.triangles, byColour = new Map();
        let edges = 0;
        for (let k = 0; k < t.length; k += 3) {
          const colour = this.colourOf(layer, layer.values[k / 3]);
          if (!byColour.has(colour)) byColour.set(colour, new Path2D());
          const path = byColour.get(colour);
          const [a, b, c] = [t[k] * 2, t[k + 1] * 2, t[k + 2] * 2];
          path.moveTo(v[a], v[a + 1]); path.lineTo(v[b], v[b + 1]); path.lineTo(v[c], v[c + 1]);
          path.closePath();
          edges += Math.hypot(v[b] - v[a], v[b + 1] - v[a + 1]);
        }
        found = { byColour, edge_nm: t.length ? edges / (t.length / 3) : 0 };
      } else {
        const p = layer.points_nm, path = new Path2D();
        for (let k = 0; k < p.length; k += 2) {
          if (k === 0) path.moveTo(p[0], p[1]); else path.lineTo(p[k], p[k + 1]);
        }
        if (layer.kind === 'polygon') path.closePath();
        found = { path };
      }
      this.paths.set(layer, found);
      return found;
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
      ctx.save();
      ctx.beginPath();
      ctx.rect(area.x, area.y, area.w, area.h);
      ctx.clip();
      const layers = this.drawing.layers;
      for (const layer of layers) if (layer.kind !== 'label') this.layer(ctx, layer, ratio);
      this.highlight(ctx);
      ctx.restore();
      this.axes(ctx, area);
      for (const layer of layers) if (layer.kind === 'label') this.label(ctx, layer, area);
      this.legend(ctx, area);
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
            ctx.fillStyle = colour;
            ctx.fill(path);
            if (edges) {
              ctx.strokeStyle = 'rgba(0, 0, 0, 0.35)';
              ctx.lineWidth = 0.5 / this.scale;
              ctx.stroke(path);
            }
          }
        });
        return;
      }
      const [colour, width, dash] = ROLES[layer.role] || ['--canvas-plot-ink', 1.5, []];
      this.inData(ctx, ratio, () => {
        if (layer.kind === 'polygon' && FILLED.includes(layer.role)) {
          ctx.globalAlpha = 0.22;
          ctx.fillStyle = token(colour) || '#4f5563';
          ctx.fill(drawn.path);
          ctx.globalAlpha = 1;
        }
        ctx.strokeStyle = token(colour) || '#16181d';
        ctx.lineWidth = width / this.scale;
        ctx.setLineDash(dash.map((d) => d / this.scale));
        ctx.lineJoin = 'round';
        ctx.stroke(drawn.path);
      });
      if (layer.role === 'contour') this.vertices(ctx, layer);
    },

    // An outline's vertices, once they stand apart on the screen.
    vertices(ctx, layer) {
      const p = layer.points_nm;
      if (p.length < 4) return;
      const apart = Math.hypot(p[2] - p[0], p[3] - p[1]) * this.scale;
      if (apart < 6) return;
      ctx.fillStyle = token('--accent') || '#5b3fd6';
      for (let k = 0; k < p.length; k += 2) {
        const [x, y] = this.toScreen(p[k], p[k + 1]);
        ctx.fillRect(x - 2.5, y - 2.5, 5, 5);
      }
    },

    highlight(ctx) {
      const picked = this.picked;
      if (!picked) return;
      const layer = this.drawing.layers.find((l) => l.id === picked.layer);
      if (!layer) return;
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
      const ink = token('--canvas-plot-ink') || '#16181d';
      const font = token('--font-num') || 'monospace';
      ctx.strokeStyle = ink;
      ctx.fillStyle = ink;
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.strokeRect(area.x + 0.5, area.y + 0.5, area.w - 1, area.h - 1);
      ctx.font = `11px ${font}`;
      const [r0, z0] = this.toData(area.x, area.y + area.h);
      const [r1, z1] = this.toData(area.x + area.w, area.y);
      const rStep = this.step(r1 - r0), zStep = this.step(z1 - z0);
      const shown = (value, step) => (Math.abs(value) < step / 1e6 ? 0 : value)
        .toFixed(Math.max(0, -Math.floor(Math.log10(step)))).replace('-', '−');
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      for (let r = Math.ceil(r0 / rStep) * rStep; r <= r1; r += rStep) {
        const [x] = this.toScreen(r, 0);
        ctx.beginPath(); ctx.moveTo(x, area.y + area.h); ctx.lineTo(x, area.y + area.h + 4); ctx.stroke();
        ctx.fillText(shown(r, rStep), x, area.y + area.h + 6);
      }
      ctx.textAlign = 'right';
      ctx.textBaseline = 'middle';
      for (let z = Math.ceil(z0 / zStep) * zStep; z <= z1; z += zStep) {
        const [, y] = this.toScreen(0, z);
        ctx.beginPath(); ctx.moveTo(area.x - 4, y); ctx.lineTo(area.x, y); ctx.stroke();
        ctx.fillText(shown(z, zStep), area.x - 6, y);
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

    label(ctx, layer, area) {
      let [x, y] = this.toScreen(layer.anchor_nm[0], layer.anchor_nm[1]);
      const text = `${layer.name} ${layer.value} ${layer.unit}`.replace('-', '−');
      ctx.font = `12px ${token('--font-num') || 'monospace'}`;
      const width = ctx.measureText(text).width + 10;
      x = Math.min(Math.max(x, area.x + 2), area.x + area.w - width - 2);
      y = Math.min(Math.max(y, area.y + 12), area.y + area.h - 12);
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
      ctx.fillText(text, x + 5, y);
    },

    legend(ctx, area) {
      const mesh = this.drawing.layers.find((l) => l.kind === 'mesh');
      if (!mesh) return;
      const ink = token('--canvas-plot-ink') || '#16181d';
      ctx.font = `12px ${token('--font-ui') || 'sans-serif'}`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      const x = area.x + area.w - 150;
      let y = area.y + 14;
      ctx.lineWidth = 1;
      ctx.strokeStyle = token('--colourbar-outline') || ink;
      if (mesh.categorical) {
        mesh.legend.forEach((name, index) => {
          ctx.fillStyle = mesh.palette[index];
          ctx.fillRect(x, y - 6, 12, 12);
          ctx.strokeRect(x + 0.5, y - 5.5, 12, 12);
          ctx.fillStyle = ink;
          ctx.fillText(name, x + 18, y);
          y += 18;
        });
        return;
      }
      const steps = mesh.palette.length;
      for (let k = 0; k < steps; k += 1) {
        ctx.fillStyle = mesh.palette[k];
        ctx.fillRect(x + (k * 120) / steps, y - 6, 120 / steps + 0.5, 12);
      }
      ctx.strokeRect(x + 0.5, y - 5.5, 120, 12);
      ctx.fillStyle = ink;
      ctx.fillText(`${mesh.colour.toUpperCase()} ${mesh.scale[0]} to ${mesh.scale[1]}`, x, y + 18);
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

    down(event) {
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
      const picked = this.nearestVertex(x, y) || this.triangleAt(...this.toData(x, y));
      this.picked = picked ? { layer: picked.layer, index: picked.index } : null;
      this.draw();
      if (this.picked) this.emit('plane_pick', this.picked);
    },

    wheel(event) {
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
