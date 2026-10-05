"""The modularity report's measurements beyond the import relation (§8.2.7 G1; WP35 D8).

VER-61 pins the import relation. The other measurements the report quotes, stage
conformance, the public surface, sizes and the generated page that renders them all,
are checked here against a package whose answers are written down by hand, so that
a number the report cites cannot come from a reader that skips what it should count.
"""

from __future__ import annotations

from pathlib import Path

from nanopnp.validation.modularity import (
    STAGE_RUN,
    ImportEdge,
    StageConformance,
    _matrix,
    import_edges,
    render_measurements,
    sizes,
    stage_conformance,
    surface,
)

SYNTHETIC = {
    "__init__.py": 'PUBLIC = {"run_case": "nanopnp.x.s:run_case"}\n',
    "core/__init__.py": "",
    "core/stages.py": (
        "class Stage:\n"  # 1
        "    def describe(self) -> None: ...\n"  # 2
        "    def run(self, inputs, *, progress, cancel) -> None: ...\n"  # 3
        "def register(description, target) -> None:\n"  # 4
        "    pass\n"  # 5
        'register(StageDescription(name="x"), "nanopnp.x.s:XStage")\n'  # 6
    ),
    "x/__init__.py": "",
    "x/s.py": (
        "import sys\n"  # 1
        "from nanopnp.core.stages import Stage as _Base\n"  # 2
        "class XStage(_Base):\n"  # 3
        "    def key(self) -> str: ...\n"  # 4
        "if sys.platform == 'win32':\n"  # 5
        "    def guarded() -> None:\n"  # 6
        "        pass\n"  # 7
    ),
}
"""A stage inheriting ``describe`` and ``run`` through an aliased base, a ``PUBLIC``
written without an annotation, and a function defined under ``if``."""


def _write(root: Path) -> Path:
    for relative, text in SYNTHETIC.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_stage_conformance_follows_a_base_imported_under_another_name(tmp_path: Path) -> None:
    (stage,) = stage_conformance(_write(tmp_path))
    assert stage == StageConformance("x", "nanopnp.x.s:XStage", True, True, True, STAGE_RUN, "()")


def test_surface_reads_public_however_it_is_assigned(tmp_path: Path) -> None:
    shown = surface(_write(tmp_path))
    assert shown.public == ("run_case",)
    assert shown.outside == ("with_section", "register")


def test_sizes_count_a_function_defined_under_a_statement(tmp_path: Path) -> None:
    functions = sizes(_write(tmp_path)).functions
    assert ("x/s.py", "guarded", 2) in functions
    assert ("core/stages.py", "Stage.run", 1) in functions


def test_the_matrix_counts_import_statements_not_imported_modules() -> None:
    """``from nanopnp.y import n, k`` is two edges ``x -> y`` and one statement."""
    relation = {
        ("x", "y"): (
            ImportEdge("nanopnp.x.m", "nanopnp.y.k", "top", 3, "x/m.py"),
            ImportEdge("nanopnp.x.m", "nanopnp.y.n", "top", 3, "x/m.py"),
        )
    }
    assert _matrix(relation, ["x", "y"]).splitlines()[2] == "| `x` |  | 1 |"


def test_the_measurements_page_renders_every_section_of_the_live_tree() -> None:
    page = render_measurements()
    for heading in (
        "## Import relation",
        "### Strongly connected components",
        "## Stage conformance",
        "## Extension points",
        "## The backend (QR-13)",
        "## The public surface",
        "## Size",
        "## Version literals",
    ):
        assert f"\n{heading}\n" in page, heading
    assert f"\n{len(import_edges())} import edges between `nanopnp` modules" in page
