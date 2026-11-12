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
    this.tune();
    await this.reveal();
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
  show(key) {
    const { Queries, QueryContext, StructureSelection } = this.lib;
    const structure = this.structure();
    if (!structure) { this.drawn(); return; }
    const query = Queries.generators.atoms({
      residueTest: (ctx) => this.key(ctx.element) === key,
    });
    const loci = StructureSelection.toLociWithSourceUnits(query(new QueryContext(structure)));
    this.viewer.plugin.managers.structure.selection.fromLoci('set', loci);
    this.drawn();
  },
};
