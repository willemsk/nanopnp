"""The workbench's screen registry: each screen's path and the controls it declares."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from nanopnp.io.project import Suite as SuiteId

__all__ = [
    "FRAME_CONTROLS",
    "GROUPS",
    "SCREENS",
    "STAGE_RUNNING",
    "SUITES",
    "TOOL_SUITES",
    "VIEWS",
    "Screen",
    "Suite",
    "Tool",
    "field_control",
    "screen",
    "tool_controls",
    "tool_for",
]

STAGE_RUNNING = {
    "structure": "Building the ensemble…",
    "protonation": "Protonating…",
    "density": "Smearing the density…",
    "symmetry": "Reducing to (r, z)…",
    "contour": "Tracing the contour…",
    "region": "Assembling the region…",
    "mesh": "Meshing…",
}
"""What a stage's build says while it runs, by stage: the Build button's and the view's words."""


@dataclass(frozen=True)
class Screen:
    """One screen: its design identifier, its path and its ``data-control`` names.

    Parameters
    ----------
    id
        The identifier the design documents and mockups use.
    controls
        Every ``data-control`` the screen carries in every state, visible once the screen is ready.
    """

    id: str
    path: str
    controls: tuple[str, ...]


@dataclass(frozen=True)
class Tool:
    """One tool of a suite: its identifier, its title and the case values it sets.

    Parameters
    ----------
    id
        The last part of the tool's path, ``/<suite>/<id>``; empty for a tool with no page yet.
    fields
        The dotted case paths the tool's pane sets, in the order it lists them.
    parts
        The case paths the tool sets through a list of parts, each opened one at a time.
    """

    id: str
    title: str
    fields: tuple[str, ...] = ()
    parts: tuple[str, ...] = ()


def _later(*titles: str) -> tuple[Tool, ...]:
    return tuple(Tool("", title) for title in titles)


@dataclass(frozen=True)
class Suite:
    """One suite of the frame: what it builds and its tools (docs/design/workbench.md).

    Parameters
    ----------
    group
        The identifier in ``GROUPS`` of the group the suite belongs to.
    icon
        The Material Symbols name of the suite's icon.
    """

    id: SuiteId
    title: str
    builds: str
    tools: tuple[Tool, ...]
    group: str
    icon: str


GROUPS: dict[str, str] = {"build": "Build", "use": "Use"}
"""The groups the suites fall into, by identifier, with the title each shows."""


SUITES: tuple[Suite, ...] = (
    Suite(
        "molecular",
        "Molecular",
        "a molecular model",
        (
            Tool(
                "prepare",
                "Prepare structure",
                (
                    "structure.source.path",
                    "structure.source.chains",
                    "structure.symmetry.point_group",
                    "structure.symmetry.axis",
                ),
            ),
            Tool(
                "ensemble",
                "Ensemble",
                (
                    "structure.ensemble.trajectory",
                    "structure.ensemble.frames.count",
                    "structure.ensemble.frames.last_ns",
                ),
            ),
            Tool(
                "protonation",
                "Protonation",
                ("charge.ph", "charge.forcefield", "charge.titration"),
            ),
            Tool("edit", "Charge edit", ("charge.edits",)),
            Tool("view", "View"),
        ),
        "build",
        "sym_o_hub",
    ),
    Suite(
        "continuum",
        "Continuum",
        "a continuum model",
        (
            Tool(
                "geometry",
                "Pore geometry",
                (
                    "geometry.density.grid_spacing_nm",
                    "geometry.density.sharpness",
                    "geometry.density.atoms",
                    "geometry.contour.isolevel",
                    "geometry.contour.smoothing",
                    "geometry.contour.simplify_tol_nm",
                ),
            ),
            Tool(
                "region",
                "Region",
                (
                    "geometry.membrane.thickness_nm",
                    "geometry.membrane.centre_z_nm",
                    "geometry.reservoir.radius_nm",
                    "charge.exclusion_offset_nm",
                ),
            ),
            Tool(
                "mesh",
                "Mesh",
                ("numerics.mesh.backend", "numerics.mesh.size_scale"),
                (
                    "numerics.mesh.maxh_nm",
                    "numerics.mesh.sizes.protein_nm",
                    "numerics.mesh.sizes.electrolyte_nm",
                    "numerics.mesh.sizes.arc_nm",
                    "numerics.mesh.sizes.axis_in_pore_nm",
                    "numerics.mesh.wall_h_nm",
                ),
            ),
        ),
        "build",
        "sym_o_grid_on",
    ),
    Suite(
        "physics",
        "Physics",
        "a physics model",
        _later("Equations", "Electrolyte", "Conditions", "Exposed values"),
        "build",
        "sym_o_function",
    ),
    Suite(
        "study",
        "Study",
        "a study",
        (
            *_later("Overview", "Study setup", "Sweep"),
            Tool("charge", "Charge on the mesh"),
            *_later("Runs"),
        ),
        "use",
        "sym_o_science",
    ),
    Suite(
        "analysis",
        "Analysis",
        "results and comparisons",
        _later("Results explorer", "Comparison"),
        "use",
        "sym_o_monitoring",
    ),
)

FRAME_CONTROLS: tuple[str, ...] = (
    "menu-file",
    "menu-view",
    "menu-help",
    "changed-count",
    "palette-open",
    *(f"suite-{suite.id}" for suite in SUITES),
    "rail",
    "rail-fold",
    "queue-status",
    "panel-toggle",
    "problems-count",
)
"""The controls of the frame, which every screen carries in every state."""

TOOL_SUITES: tuple[Suite, ...] = tuple(suite for suite in SUITES if suite.tools[0].id)
"""The suites whose tools have pages: each opens its last tool used, beside its view."""

VIEWS: dict[SuiteId, Literal["molecule", "plane"]] = {
    "molecular": "molecule",
    "continuum": "plane",
}
"""The ``data-control`` of each tool suite's view: the 3D molecule, or the (r, z) plane."""


def tool_controls(suite: Suite, tool: Tool) -> tuple[str, ...]:
    """Return the controls a tool's page carries in every state.

    Every tool's page has its suite's view, its pane, its status and its suite's tool list; a
    tool that sets values filters to the modified ones and has a field per value, and a tool
    that sets parts has their list.
    """
    own = ("tool-modified",) if tool.fields or tool.parts else ()
    return (
        VIEWS[suite.id],
        "tool-pane",
        "tool-status",
        *(f"tool-link-{entry.id}" for entry in suite.tools),
        *own,
        *(field_control(path) for path in tool.fields),
        *(("tool-parts",) if tool.parts else ()),
    )


def field_control(path: str) -> str:
    """Return the ``data-control`` name of the field that sets a dotted case path."""
    return "field-" + path.replace(".", "-")


def tool_for(suite: SuiteId, path: str) -> Tool | None:
    """Return the tool of a suite whose pane sets a case path, or None where none does."""
    for entry in SUITES:
        if entry.id != suite:
            continue
        for tool in entry.tools:
            if any(
                path == held or path.startswith(f"{held}.") for held in (*tool.fields, *tool.parts)
            ):
                return tool
    return None


SCREENS: tuple[Screen, ...] = (
    # A tool suite's path opens its last tool, its first in a fresh window.
    *(
        Screen(
            suite.id,
            f"/{suite.id}",
            (
                *FRAME_CONTROLS,
                *(
                    tool_controls(suite, suite.tools[0])
                    if suite in TOOL_SUITES
                    else ("suite-body",)
                ),
            ),
        )
        for suite in SUITES
    ),
    *(
        Screen(
            f"{suite.id[0]}-{tool.id}",
            f"/{suite.id}/{tool.id}",
            (*FRAME_CONTROLS, *tool_controls(suite, tool)),
        )
        for suite in TOOL_SUITES
        for tool in suite.tools
    ),
    Screen("changes", "/study?panel=changes", (*FRAME_CONTROLS, "changes-list")),
    Screen("problems", "/study?panel=problems", (*FRAME_CONTROLS, "problems-list")),
    Screen(
        "settings",
        "/settings",
        (
            *FRAME_CONTROLS,
            "settings-sections",
            "settings-search",
            "settings-scope",
            "settings-modified",
            "settings-theme",
            "settings-density",
            "settings-spacing",
            "settings-viewer_background",
            "theme-colours",
            "theme-duplicate",
            "settings-keys",
            "store-usage",
        ),
    ),
    Screen(
        "palette", "/molecular?palette=suite", (*FRAME_CONTROLS, "palette-input", "palette-item")
    ),
    Screen(
        "st-charge",
        "/study/charge",
        (*FRAME_CONTROLS, "molecule", "strip", "map", "link-chip", "unlink", "status"),
    ),
)


def screen(identifier: str) -> Screen:
    """Return the screen with this identifier."""
    for entry in SCREENS:
        if entry.id == identifier:
            return entry
    raise KeyError(f"no screen {identifier!r}; the screens are {', '.join(s.id for s in SCREENS)}")
