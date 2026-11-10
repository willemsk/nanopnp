// The Mol* glue of the charge screen: the one part of the workbench that cannot be Python.
// Selection only: no camera move, because software GL fills a zoomed cartoon at 2 fps.
window.nano = {
  viewer: null,
  // How many times Mol* was built in this window: the frame builds it once and keeps it (VER-78 m).
  builds: 0,
  // Build Mol* the first time the frame shows it; after that, show and redraw the one built.
  async ensure(structureUrl) {
    if (this.viewer === null) {
      await this.init(structureUrl);
      return;
    }
    await this.reveal();
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
  // Ready means Mol* has built and drawn once; a click before that is lost.
  async init(structureUrl) {
    const { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement } = molstar.lib.structure;
    this.lib = { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement };
    this.builds += 1;
    this.viewer = await molstar.Viewer.create('mol', {
      layoutIsExpanded: false, layoutShowControls: false, layoutShowRemoteState: false,
      layoutShowSequence: false, layoutShowLog: false, layoutShowLeftPanel: false,
      viewportShowExpand: false, viewportShowSelectionMode: false, viewportShowAnimation: false,
    });
    if (structureUrl) await this.viewer.loadStructureFromUrl(structureUrl, 'pdb', false);
    this.viewer.plugin.behaviors.interaction.click.subscribe((e) => {
      const { loci } = e.current;
      if (!StructureElement.Loci.is(loci) || StructureElement.Loci.isEmpty(loci)) return;
      emitEvent('mol_pick', { key: this.key(StructureElement.Loci.getFirstLocation(loci)) });
    });
    const plugin = this.viewer.plugin;
    const once = (stream, test) => new Promise((done) => {
      let sub = null, fired = false;
      sub = stream.subscribe((v) => {
        if (fired || !test(v)) return;
        fired = true; done(); setTimeout(() => sub && sub.unsubscribe(), 0);
      });
    });
    await once(plugin.behaviors.state.isBusy, (busy) => !busy);
    plugin.canvas3d.setProps({ postprocessing: { occlusion: { name: 'off', params: {} }, outline: { name: 'off', params: {} }, shadow: { name: 'off', params: {} } } });
    this.background();
    const drawn = once(plugin.canvas3d.didDraw, () => true);
    plugin.canvas3d.requestDraw(true);
    await drawn;
    document.body.dataset.screenReady = '1';
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
