import { useCallback, useEffect, useRef, useState } from 'react';
import { createMol, Mol } from './mol';

interface Extent { r_low: number; r_high: number; z_low: number; z_high: number; width: number; height: number }
interface Residue { key: string; name: string; q_e: number }
type Marker = [number, number, number];

const MAP_WIDTH = 330;

function bumpDrawn() {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    document.body.dataset.drawn = String((Number(document.body.dataset.drawn) || 0) + 1);
  }));
}

function StudyScreen() {
  const molEl = useRef<HTMLDivElement>(null);
  const mol = useRef<Mol | null>(null);
  const linked = useRef(true);
  const [isLinked, setLinked] = useState(true);
  const [residues, setResidues] = useState<Residue[]>([]);
  const [extent, setExtent] = useState<Extent | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [markers, setMarkers] = useState<Marker[]>([]);

  useEffect(() => {
    fetch('/api/residues').then((r) => r.json()).then(setResidues);
    fetch('/api/map/extent').then((r) => r.json()).then(setExtent);
  }, []);

  const pick = useCallback(async (key: string, moveMol: boolean) => {
    const body = await (await fetch(`/api/residue/${key}`)).json();
    if (moveMol) mol.current?.show(key);
    setSelected(key);
    setMarkers(body.markers);
  }, []);

  useEffect(() => {
    let dead = false;
    createMol(molEl.current!, (key) => { if (linked.current) void pick(key, false); }).then((m) => {
      if (dead) { m.viewer.dispose(); return; }
      mol.current = m;
      document.body.dataset.screenReady = '1';
    });
    return () => { dead = true; mol.current?.viewer.dispose(); mol.current = null; };
  }, [pick]);

  useEffect(() => { if (selected) bumpDrawn(); }, [markers]);

  const onMap = async (event: React.MouseEvent<HTMLDivElement>) => {
    if (!linked.current || !extent) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * extent.width;
    const y = ((event.clientY - box.top) / box.height) * extent.height;
    const r = extent.r_low + (x / extent.width) * (extent.r_high - extent.r_low);
    const z = extent.z_high - (y / extent.height) * (extent.z_high - extent.z_low);
    const found = (await (await fetch(`/api/point?r_nm=${r}&z_nm=${z}`)).json()).residues;
    if (found.length) await pick(found[0].key, true);
  };

  const toggle = () => { linked.current = !linked.current; setLinked(linked.current); };

  return (
    <div className="study">
      <div className="col">
        <div id="mol" ref={molEl} data-control="molecule" />
        <div className="strip" data-control="strip">
          {residues.map((item) => (
            <button
              key={item.key}
              data-control="strip-item"
              data-residue={item.key}
              className={item.key === selected ? 'on' : ''}
              onClick={() => void pick(item.key, true)}
            >
              {item.name}{item.key}
            </button>
          ))}
        </div>
      </div>
      <div className="col">
        <div className="bar">
          <span className="chip" data-control="link-chip">{isLinked ? 'Linked' : 'Unlinked'}</span>
          <button data-control="unlink" onClick={toggle}>{isLinked ? 'Unlink' : 'Link'}</button>
          <span>{selected ? `Residue ${selected}` : ''}</span>
        </div>
        <div className="map" data-control="map" style={{ width: MAP_WIDTH }} onClick={(e) => void onMap(e)}>
          <img src="/api/map" draggable={false} alt="Charge density map" />
          {extent && (
            <svg viewBox={`0 0 ${extent.width} ${extent.height}`} preserveAspectRatio="none">
              {markers.map(([r, z, q], i) => {
                const cx = ((r - extent.r_low) / (extent.r_high - extent.r_low)) * extent.width;
                const cy = ((extent.z_high - z) / (extent.z_high - extent.z_low)) * extent.height;
                return (
                  <g key={i}>
                    <circle cx={cx} cy={cy} r={5} fill="none" stroke="#000" strokeWidth={3} />
                    <circle cx={cx} cy={cy} r={5} fill="none" stroke={q > 0 ? '#b4231a' : '#1d4ed8'} strokeWidth={1.5} />
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}

export function App() {
  const [tab, setTab] = useState<'study' | 'sketcher'>('study');
  return (
    <div>
      <div role="tablist" data-control="tabs" className="tabs">
        <button role="tab" aria-selected={tab === 'study'} data-control="tab-study" onClick={() => setTab('study')}>Charge on the mesh</button>
        <button role="tab" aria-selected={tab === 'sketcher'} data-control="tab-sketcher" onClick={() => setTab('sketcher')}>Sketcher</button>
      </div>
      <div hidden={tab !== 'study'}><StudyScreen /></div>
      {tab === 'sketcher' && (
        <div className="panel">
          <p data-control="banner">The sketcher arrives in a later phase.</p>
          <canvas data-control="sketcher-canvas" width={400} height={200} style={{ border: '1px solid var(--control-edge)' }} />
        </div>
      )}
    </div>
  );
}
