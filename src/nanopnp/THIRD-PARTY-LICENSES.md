# Licences of a nanopnp installation

**An installation that runs a case is used under the GNU General Public License, version 2 or later
(GPL-2+).** The nanopnp library itself is BSD-3-Clause and remains so. The installation's
obligations are GPL-2+ because its default linear solver, SuiteSparse UMFPACK, is GPL-2+ and is
linked into the NGSolve wheel that `uv sync` installs (`SPECIFICATION.md` CON-11). §6.6 records why
UMFPACK is the default: scipy's BSD-licensed SuperLU was OOM-killed on the reference-sized
factorisation. SuperLU stays selectable (`numerics.linear.solver: superlu`, in Study setup's *More
values*); an installation configured that way still carries UMFPACK, so its obligations do not
change. Gmsh, the optional mesher backend (`SPECIFICATION.md` §8.2.2 B8), is GPL-2+ as well and
changes nothing about that. `nanopnp --env` states the obligation and this file's path.

nanopnp installs its dependencies from their own wheels and redistributes none of them, apart from
the four front-end libraries and the radius table named below. Each wheel carries its own licence
text in its `*.dist-info/` directory.

| Component | Licence | What it is here |
|---|---|---|
| nanopnp | BSD-3-Clause | The library, the command line and the workbench |
| NGSolve, Netgen | LGPL-2.1 | Finite-element backend and mesher, dynamically linked |
| Open CASCADE Technology (`netgen-occt`) | LGPL-2.1 with the OCCT exception | Netgen's CAD kernel, dynamically linked |
| OpenBLAS (`ngsolve-openblas`) | BSD-3-Clause | NGSolve's dense linear algebra, dynamically linked. On Linux it links `libgfortran`, under GPL-3 with the GCC Runtime Library Exception |
| SuiteSparse UMFPACK | **GPL-2+** | The default direct linear solver, built into the NGSolve wheel |
| NumPy, SciPy, pydantic, PyYAML, meshio, h5py, SymPy, Pint | BSD-3-Clause / MIT / Apache-2.0 | Numerics, configuration and file formats |
| MDAnalysis, with GridDataFormats | LGPL-3.0-or-later | Stage 1's structure and trajectory reader, and the OpenDX grid reader, dynamically loaded (the `structure` extra) |
| gemmi | MPL-2.0 | Stage 1's mmCIF and PDB reader, unmodified |
| scikit-image | BSD-3-Clause | Stage 4's contour extraction (`find_contours`) |
| Shapely | BSD-3-Clause | Stage 4's polygon checks |
| GEOS (inside the Shapely wheel) | LGPL-2.1 | Shapely's geometry engine, dynamically linked |
| Gmsh | **GPL-2+** | The optional mesher backend (`numerics.mesh.backend: gmsh`, the `gmsh` extra); never imported on the default path (CON-10) |
| PDB2PQR 3.8.0, with its `pdb2pqr/dat/` force-field files | BSD-3-Clause | Stage 7's protonation, partial charges and radii, unmodified. Its notice and licence are below |
| PROPKA 3.5.1 | LGPL-2.1 | The pKa calculation PDB2PQR titrates with, unmodified |
| PDB2PQR 3.8.0 `CHARMM.DAT` (radius column only) | BSD-3-Clause | The stage-2 density map's van der Waals radii, transcribed as data into `nanopnp/data/radii/pdb2pqr_charmm.yaml`; its notice and licence are below |
| NiceGUI | MIT | The workbench's browser shell (the `gui` extra) |
| FastAPI, with Starlette and uvicorn | MIT / BSD-3-Clause | The workbench's local server (the `gui` extra) |
| Matplotlib | PSF-based (Matplotlib licence) | The workbench's colour maps and the figures of `nanopnp.plot` |
| `webgui` 0.2.39 (npm), bundling three.js r152 and dat.gui 0.7 | LGPL-2.1-or-later; MIT; Apache-2.0 | The field viewer's renderer, redistributed unmodified as `nanopnp/gui/assets/webgui/webgui.js` beside its three licence texts and a `NOTICE.md` naming its source |
| Mol* (`molstar` 5.13.1, npm) | MIT | The molecule viewer, redistributed unmodified in `nanopnp/gui/web/assets/molstar/` with its licence and `NOTICE.md` |
| uPlot 1.6.32 (npm) | MIT | The workbench's charts, redistributed unmodified in `nanopnp/gui/web/assets/uplot/` with its licence and `NOTICE.md` |
| KaTeX 0.19.1 (npm) | MIT | The Physics suite's equations, redistributed unmodified in `nanopnp/gui/web/assets/katex/` with its licence and `NOTICE.md` |

## Your rights under the LGPL components

NGSolve, Netgen, Open CASCADE, `webgui`, MDAnalysis, GridDataFormats, PROPKA and GEOS are used under
their LGPL options, which give you the right to replace them with your own versions. Each is an
ordinary installed package or file and may be replaced in place: nothing in nanopnp is statically
linked against an LGPL component. The renderer is the file `nanopnp/gui/assets/webgui/webgui.js`,
and the workbench serves whatever build is at that path; `nanopnp gui --selftest` compares it with
the shipped one and says so if it differs.

## PDB2PQR, and its radius table

`data/radii/pdb2pqr_charmm.yaml` carries the atomic radii of PDB2PQR 3.8.0's
`pdb2pqr/dat/CHARMM.DAT`, which the density map of `SPECIFICATION.md` §5.3.1 uses by an author
ruling. It is redistributed under PDB2PQR's licence, reproduced here verbatim from the 3.8.0
distribution:

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

nanopnp's source is at <https://github.com/willemsk/nanopnp>. The upstream sources of every
component above are available from their own projects; NGSolve at <https://ngsolve.org> and
SuiteSparse at <https://people.engr.tamu.edu/davis/suitesparse.html>. The corresponding source of
`webgui` is the npm tarball <https://registry.npmjs.org/webgui/-/webgui-0.2.39.tgz>, kept verbatim
in nanopnp's repository as `third_party/webgui-0.2.39.tgz`.

## Checking an installation

`nanopnp gui --selftest` exercises each compiled payload above once, in its own process: NGSolve and
Netgen mesh a unit square, a workbench server serves the renderer, MDAnalysis and gemmi read a
three-atom structure, scikit-image extracts a contour, Shapely checks a polygon through GEOS, Gmsh
meshes a unit square where it is installed, and PDB2PQR with PROPKA protonate a nine-residue fragment
of 2WCD at pH 2 and pH 8. It prints one line a payload and exits 0, or names the payload that failed
(RSK-13).
