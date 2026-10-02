# Licences of the nanopnp desktop bundle

**This bundle is distributed under the GNU General Public License, version 2 or later
(GPL-2+).** The nanopnp library itself is BSD-3-Clause and remains so; the bundle's licence is
GPL-2+ because its default linear solver, SuiteSparse UMFPACK, is GPL-2+ and is linked into the
NGSolve wheel the bundle carries. `SPECIFICATION.md` CON-11 requires this to be stated here, and
§6.6 records the measurement behind defaulting to UMFPACK: scipy's BSD-licensed SuperLU was
OOM-killed on the reference-sized factorisation, so a SuperLU-default bundle could not run the
published case. SuperLU remains selectable at run time (`numerics.linear.solver: superlu`); a
bundle configured that way is still distributed under GPL-2+, because UMFPACK ships inside it
regardless of which solver a case selects. Gmsh, carried as the optional mesher backend
(`SPECIFICATION.md` §8.2.2 B8), is GPL-2+ as well and changes nothing about that.

| Component | Licence | What it is here |
|---|---|---|
| nanopnp | BSD-3-Clause | This application and the library it drives |
| NGSolve, Netgen | LGPL-2.1 | Finite-element backend and mesher, dynamically linked |
| Open CASCADE Technology (`netgen-occt`) | LGPL-2.1 with the OCCT exception | Netgen's CAD kernel, dynamically linked; its licence text travels in `netgen_occt-*.dist-info/` |
| OpenBLAS (`ngsolve-openblas`) | BSD-3-Clause | NGSolve's dense linear algebra, dynamically linked. A Linux bundle also carries the `libgfortran` it links, under GPL-3 with the GCC Runtime Library Exception |
| SuiteSparse UMFPACK | **GPL-2+** | Default direct linear solver, built into the NGSolve wheel |
| PySide6, Qt 6 (including Qt WebEngine) | LGPL-3 | Desktop shell and the embedded field viewer, dynamically linked |
| `webgui` 0.2.39 (npm), bundling three.js r152 and dat.gui 0.7 | LGPL-2.1-or-later; MIT; Apache-2.0 | The field viewer's renderer, shipped unmodified as `nanopnp/gui/assets/webgui/webgui.js` beside its three licence texts and a `NOTICE.md` naming its source |
| NumPy, SciPy, pydantic, PyYAML, meshio, h5py, SymPy | BSD-3-Clause / MIT / Apache-2.0 | Numerics, configuration and file formats |
| MDAnalysis, with GridDataFormats | LGPL-3.0-or-later | Stage 1's structure and trajectory reader, and the OpenDX grid reader, dynamically loaded |
| gemmi | MPL-2.0 | Stage 1's mmCIF and PDB reader, unmodified |
| scikit-image | BSD-3-Clause | Stage 4's contour extraction (`find_contours`) |
| Shapely | BSD-3-Clause | Stage 4's polygon checks |
| GEOS (inside the Shapely wheel) | LGPL-2.1 | Shapely's geometry engine, dynamically linked |
| Gmsh | **GPL-2+** | The optional mesher backend (`numerics.mesh.backend: gmsh`); never imported on the default path (CON-10). Its library sits at the bundle root and its licence text in `gmsh-licence/` |
| The geometry payloads' pure-Python dependencies (NetworkX, imageio, tifffile, Pillow, lazy_loader, mmtf-python, mda-xdrlib, tqdm, threadpoolctl) | BSD / MIT / Apache-2.0 / PSF / MPL-2.0 | Imported by the readers above; unmodified |
| PDB2PQR 3.7.1, with its `pdb2pqr/dat/` force-field files | BSD-3-Clause | Stage 7's protonation, partial charges and radii, unmodified, with its `dat/` tree beside it. Its notice and licence are below |
| PROPKA 3.5.1, with `propka.cfg` | LGPL-2.1 | The pKa calculation PDB2PQR titrates with, unmodified; collected as source files, with its parameter file beside them |
| PDB2PQR's pure-Python dependencies (requests, urllib3, idna, charset-normalizer, certifi, mmcif-pdbx) | Apache-2.0 / MIT / BSD-3-Clause / MPL-2.0 / CC0-1.0 | Imported by PDB2PQR; unmodified. nanopnp never lets it reach the network: it is always given a file |
| PDB2PQR 3.7.1 `CHARMM.DAT` (radius column only) | BSD-3-Clause | The stage-2 density map's van der Waals radii, transcribed as data into `nanopnp/data/radii/pdb2pqr_charmm.yaml`; its notice and licence are below |

## Your rights under the LGPL components

NGSolve, Netgen, Open CASCADE, PySide6, Qt, `webgui`, MDAnalysis, GridDataFormats, PROPKA and GEOS
are used under their LGPL options, which give you the right to replace them with your own versions.
The bundle is built **one-dir** rather than one-file precisely so that you can: every shared library
is an ordinary file in the bundle directory and may be replaced in place. Nothing in the bundle is
statically linked against an LGPL component. The renderer is likewise an ordinary file,
`_internal/nanopnp/gui/assets/webgui/webgui.js`, and the viewer loads whatever build is at that path.

The LGPL components written in Python are collected as **source files**, not into the bundle's
compressed module archive: PROPKA as `_internal/propka/*.py`, MDAnalysis as `_internal/MDAnalysis/`
(its compiled extensions beside its `.py` files), and GridDataFormats as `_internal/gridData/`. A
module inside the archive could not be replaced without rebuilding it; a source file can be
replaced in place, and the bundle imports whatever is at that path.

## PDB2PQR, and its radius table

The bundle carries PDB2PQR 3.7.1 itself, with its force-field files, and
`data/radii/pdb2pqr_charmm.yaml` carries the atomic radii of its `pdb2pqr/dat/CHARMM.DAT`, which the
density map of `SPECIFICATION.md` §5.3.1 uses by an author ruling. Both are redistributed under
PDB2PQR's licence, reproduced here verbatim from the 3.7.1 distribution:

> Copyright (c) 2002-2024, Jens Erik Nielsen; Nathan A. Baker; Battelle Memorial Institute, Developed at the Pacific Northwest National Laboratory, operated by Battelle Memorial Institute, Pacific Northwest Division for the U.S. Department Energy.; Paul Czodrowski & Gerhard Klebe, University of Marburg.
>
> All rights reserved.
>
> Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
>
> * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
>
> * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
>
> * Neither the names of University College Dublin, Battelle Memorial Institute, Pacific Northwest National Laboratory, US Department of Energy, or University of Marburg nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## Source

nanopnp's source, including the build recipe for this bundle
(`packaging/nanopnp-probe.spec`), is at <https://github.com/willemsk/nanopnp>. The upstream sources
of every component above are available from their own projects; NGSolve at
<https://ngsolve.org>, SuiteSparse at <https://people.engr.tamu.edu/davis/suitesparse.html>, and
Qt for Python at <https://doc.qt.io/qtforpython>.
The corresponding source of `webgui` is the npm tarball
<https://registry.npmjs.org/webgui/-/webgui-0.2.39.tgz>, kept verbatim in nanopnp's repository as
`third_party/webgui-0.2.39.tgz`.

## What this bundle is

The current bundle is the **packaging probe** of `SPECIFICATION.md` §8.2 criterion 4 as amended by
§8.2.1 A4: a trivial application that imports PySide6, Qt WebEngine, NGSolve, Netgen and
`ngsolve.webgui` in one process, and exercises the geometry pipeline's compiled payloads once each —
MDAnalysis and gemmi read a three-atom structure, scikit-image extracts a contour, Shapely checks a
polygon through GEOS, Gmsh meshes a unit square, and PDB2PQR with PROPKA protonates a nine-residue
fragment of 2WCD (shipped as `nanopnp/data/structures/2wcd-a-18-26.pdb`, from the CC0 PDB entry)
at pH 2 and pH 8 — so that RSK-13, desktop packaging defeated by
a binary dependency, is detected on every push rather than once. It is not the desktop shell, and it solves
nothing. The licence obligations above are stated with the first bundle rather than with the first
useful one, because a licence statement cannot be retrofitted to something already distributed.
