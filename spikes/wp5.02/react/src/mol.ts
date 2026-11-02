// Mol* glue: the same calls as the NiceGUI bridge, typed as far as the standalone bundle allows.
/* eslint-disable @typescript-eslint/no-explicit-any */
declare const molstar: any;

export interface Mol {
  show(key: string): void;
  viewer: any;
}

const once = (stream: any, test: (v: any) => boolean) =>
  new Promise<void>((done) => {
    let sub: any = null;
    let fired = false;
    sub = stream.subscribe((v: any) => {
      if (fired || !test(v)) return;
      fired = true;
      done();
      setTimeout(() => sub && sub.unsubscribe(), 0);
    });
  });

export async function createMol(target: HTMLElement, onPick: (key: string) => void): Promise<Mol> {
  const { StructureProperties, Queries, QueryContext, StructureSelection, StructureElement } = molstar.lib.structure;
  const viewer = await molstar.Viewer.create(target, {
    layoutIsExpanded: false, layoutShowControls: false, layoutShowRemoteState: false,
    layoutShowSequence: false, layoutShowLog: false, layoutShowLeftPanel: false,
    viewportShowExpand: false, viewportShowSelectionMode: false, viewportShowAnimation: false,
  });
  await viewer.loadStructureFromUrl('/api/structure', 'pdb', false);
  const plugin = viewer.plugin;
  plugin.behaviors.interaction.click.subscribe((e: any) => {
    const { loci } = e.current;
    if (!StructureElement.Loci.is(loci) || StructureElement.Loci.isEmpty(loci)) return;
    const loc = StructureElement.Loci.getFirstLocation(loci);
    onPick(String(StructureProperties.residue.auth_seq_id(loc)));
  });
  await once(plugin.behaviors.state.isBusy, (busy) => !busy);
  plugin.canvas3d.setProps({ postprocessing: { occlusion: { name: 'off', params: {} }, outline: { name: 'off', params: {} }, shadow: { name: 'off', params: {} } } });
  const drawn = once(plugin.canvas3d.didDraw, () => true);
  plugin.canvas3d.requestDraw(true);
  await drawn;
  return {
    viewer,
    show(key: string) {
      const structure = plugin.managers.structure.hierarchy.current.structures[0]?.cell.obj?.data;
      if (!structure) return;
      const query = Queries.generators.atoms({
        residueTest: (ctx: any) => String(StructureProperties.residue.auth_seq_id(ctx.element)) === key,
      });
      const loci = StructureSelection.toLociWithSourceUnits(query(new QueryContext(structure)));
      plugin.managers.structure.selection.fromLoci('set', loci);
    },
  };
}
