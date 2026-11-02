// The Mol* glue of the charge screen: the one part of the workbench that cannot be Python.
// Selection only: no camera move, because software GL fills a zoomed cartoon at 2 fps.
window.nano = {
  viewer: null,
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
