// The Mol* glue of the charge screen: the one part of the workbench that cannot be Python.
// Selection only: no camera move, because software GL fills a zoomed cartoon at 2 fps.
window.nano = {
  viewer: null,
  // How many times Mol* was built in this window: the frame builds it once and keeps it (VER-78 m).
  builds: 0,
  // The build under way: a call while Mol* builds waits for it rather than building a second one.
  building: null,
  // The structure the scene now shown draws; the camera is kept while it stays the same.
  sceneKey: null,
  // The scene's address, and the residue picked in it, which a swap to one subunit keeps.
  sceneUrl: null,
  picked: null,
  // The button that swaps the study's pore, cut at its axis, for one subunit (WB-44).
  subunit: null,
  // Show a MolViewSpec scene the server writes, building Mol* the first time; null empties the view.
  async scene(url, key) {
    document.body.dataset.screenReady = '0';
    if (this.viewer === null && this.building === null) {
      this.building = this.init().finally(() => { this.building = null; });
    }
    if (this.building !== null) await this.building;
    const plugin = this.viewer.plugin;
    // A scene that cannot be fetched, or that Mol* refuses, is reported and the view still
    // settles, so the page never hangs on it.
    try {
      const text = url ? await (await fetch(url, { credentials: 'same-origin' })).text() : 'null';
      if (text.trim() === 'null') {
        if (this.sceneKey !== null) await plugin.clear();
        this.sceneKey = null;
      } else {
        // A scene that places its camera keeps it as its volumes arrive: the canvas would
        // otherwise fit itself again to their box, which is wider than the structure.
        plugin.canvas3d.setProps({ camera: { manualReset: /"kind":\s*"camera"/.test(text) } });
        await this.viewer.loadMvsData(text, 'mvsj', {
          replaceExisting: true, keepCamera: this.sceneKey === key,
          sourceUrl: new URL(url, window.location.href).href,
        });
        this.sceneKey = key;
        await this.once(plugin.behaviors.state.isBusy, (busy) => !busy);
      }
    } catch (error) {
      console.error(`the 3D scene ${url} was refused: ${error}`);
    }
    this.offer(url);
    this.tune();
    await this.reveal();
  },
  // A scene whose address carries `subunit` offers the swap; any other hides the button.
  offer(url) {
    if (this.subunit === null) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'mol-subunit';
      button.textContent = 'One subunit';
      button.title = 'Show one subunit alone, or the pore cut at its axis';
      button.dataset.control = 'mol-subunit';
      button.addEventListener('click', () => this.swap());
      document.getElementById('mol').parentElement.append(button);
      this.subunit = button;
    }
    const asked = url ? new URL(url, window.location.href).searchParams.get('subunit') : null;
    this.sceneUrl = url;
    this.subunit.style.display = asked === null ? 'none' : '';
    this.subunit.setAttribute('aria-pressed', String(asked === '1'));
  },
  async swap() {
    if (!this.sceneUrl) return;
    const next = new URL(this.sceneUrl, window.location.href);
    const alone = next.searchParams.get('subunit') !== '1';
    next.searchParams.set('subunit', alone ? '1' : '0');
    // Another key, so the scene's own camera replaces the one kept.
    const base = String(this.sceneKey).split('|')[0];
    await this.scene(next.pathname + next.search, alone ? `${base}|one` : base);
    if (this.picked !== null) this.show(this.picked);
  },
  once(stream, test) {
    return new Promise((done) => {
      let sub = null, fired = false;
      sub = stream.subscribe((v) => {
        if (fired || !test(v)) return;
        fired = true; done(); setTimeout(() => sub && sub.unsubscribe(), 0);
      });
    });
  },
  // A scene resets the canvas, so the settings of ours go back on after each.
  tune() {
    this.viewer.plugin.canvas3d.setProps({ postprocessing: { occlusion: { name: 'off', params: {} }, outline: { name: 'off', params: {} }, shadow: { name: 'off', params: {} } } });
    this.background();
  },
  async reveal() {
    const canvas = this.viewer.plugin.canvas3d;
    this.viewer.plugin.layout.events.updated.next();
    canvas.handleResize();
    const drawn = new Promise((done) => {
      const sub = canvas.didDraw.subscribe(() => { done(); setTimeout(() => sub.unsubscribe(), 0); });
    });
    canvas.requestDraw(true);
    await drawn;
    document.body.dataset.screenReady = '1';
  },
  // The 3D view's background is the --canvas-3d token, a setting of the user's (WB-30). The frame
  // calls this again after each change to the settings, since the one viewer is never rebuilt.
  background() {
    if (this.viewer === null) return;
    const token = getComputedStyle(document.documentElement).getPropertyValue('--canvas-3d').trim();
    if (!/^#[0-9a-f]{6}$/i.test(token)) return;
    const canvas = this.viewer.plugin.canvas3d;
    canvas.setProps({ renderer: { backgroundColor: parseInt(token.slice(1), 16) } });
    canvas.requestDraw(true);
  },
  structure() {
    const s = this.viewer.plugin.managers.structure.hierarchy.current.structures[0];
    return s && s.cell.obj && s.cell.obj.data;
  },
  key(loc) {
    const { StructureProperties: P } = this.lib;
    const icode = (P.residue.pdbx_PDB_ins_code(loc) || '').trim();
    return `${P.chain.auth_asym_id(loc)}:${P.residue.auth_seq_id(loc)}${icode}`;
  },
  drawn() {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.body.dataset.drawn = String((Number(document.body.dataset.drawn) || 0) + 1);
    }));
  },
  // Mol* is built empty; a scene loads the structure. A click before the first draw is lost.
  async init() {
    const { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement } = molstar.lib.structure;
    this.lib = { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement };
    this.builds += 1;
    this.viewer = await molstar.Viewer.create('mol', {
      layoutIsExpanded: false, layoutShowControls: false, layoutShowRemoteState: false,
      layoutShowSequence: false, layoutShowLog: false, layoutShowLeftPanel: false,
      viewportShowExpand: false, viewportShowSelectionMode: false, viewportShowAnimation: false,
    });
    this.viewer.plugin.behaviors.interaction.click.subscribe((e) => {
      const { loci } = e.current;
      if (!StructureElement.Loci.is(loci) || StructureElement.Loci.isEmpty(loci)) return;
      emitEvent('mol_pick', { key: this.key(StructureElement.Loci.getFirstLocation(loci)) });
    });
    await this.once(this.viewer.plugin.behaviors.state.isBusy, (busy) => !busy);
  },
  // Select a residue, or each of a list: a residue's copies under Cn are picked together.
  show(keys) {
    this.picked = keys;
    const wanted = new Set(Array.isArray(keys) ? keys : [keys]);
    const { Queries, QueryContext, StructureSelection } = this.lib;
    const structure = this.structure();
    if (!structure) { this.drawn(); return; }
    const query = Queries.generators.atoms({
      residueTest: (ctx) => wanted.has(this.key(ctx.element)),
    });
    const loci = StructureSelection.toLociWithSourceUnits(query(new QueryContext(structure)));
    this.viewer.plugin.managers.structure.selection.fromLoci('set', loci);
    this.drawn();
  },
};
