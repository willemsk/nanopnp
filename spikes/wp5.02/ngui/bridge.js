// Mol* glue for the NiceGUI candidate: the part of the page that cannot be Python.
window.nano = {
  viewer: null,
  structure() {
    const s = this.viewer.plugin.managers.structure.hierarchy.current.structures[0];
    return s && s.cell.obj && s.cell.obj.data;
  },
  drawn() {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      document.body.dataset.drawn = String((Number(document.body.dataset.drawn) || 0) + 1);
    }));
  },
  async init() {
    const { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement } = molstar.lib.structure;
    this.lib = { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement };
    this.viewer = await molstar.Viewer.create('mol', {
      layoutIsExpanded: false, layoutShowControls: false, layoutShowRemoteState: false,
      layoutShowSequence: false, layoutShowLog: false, layoutShowLeftPanel: false,
      viewportShowExpand: false, viewportShowSelectionMode: false, viewportShowAnimation: false,
    });
    await this.viewer.loadStructureFromUrl('/api/structure', 'pdb', false);
    this.viewer.plugin.behaviors.interaction.click.subscribe((e) => {
      const { loci } = e.current;
      if (!StructureElement.Loci.is(loci) || StructureElement.Loci.isEmpty(loci)) return;
      const loc = StructureElement.Loci.getFirstLocation(loci);
      emitEvent('mol_pick', { key: String(StructureProperties.residue.auth_seq_id(loc)) });
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
    const drawn = once(plugin.canvas3d.didDraw, () => true);
    plugin.canvas3d.requestDraw(true);
    await drawn;
    document.body.dataset.screenReady = '1';
  },
  show(key) {
    const { Queries, QueryContext, StructureSelection, StructureProperties } = this.lib;
    const structure = this.structure();
    if (!structure) return;
    const query = Queries.generators.atoms({
      residueTest: (ctx) => String(StructureProperties.residue.auth_seq_id(ctx.element)) === key,
    });
    const loci = StructureSelection.toLociWithSourceUnits(query(new QueryContext(structure)));
    const plugin = this.viewer.plugin;
    plugin.managers.structure.selection.fromLoci('set', loci);
    // No camera move: software GL fills a zoomed cartoon at 2 fps, a GPU does not care.
    this.drawn();
  },
};
