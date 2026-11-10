"""The workbench's screen registry: each screen's path and the controls it declares."""

from __future__ import annotations

from dataclasses import dataclass

from nanopnp.io.project import Suite as SuiteId

__all__ = ["FRAME_CONTROLS", "GROUPS", "SCREENS", "SUITES", "Screen", "Suite", "screen"]


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
    tools: tuple[str, ...]
    group: str
    icon: str


GROUPS: dict[str, str] = {"build": "Build", "use": "Use"}
"""The groups the suites fall into, by identifier, with the title each shows."""


SUITES: tuple[Suite, ...] = (
    Suite(
        "molecular",
        "Molecular",
        "a molecular model",
        ("Prepare structure", "Ensemble", "Protonation", "Charge edit", "View"),
        "build",
        "sym_o_hub",
    ),
    Suite(
        "continuum",
        "Continuum",
        "a continuum model",
        ("Protein geometry", "Contour", "Region", "Mesh: sizes, quality"),
        "build",
        "sym_o_grid_on",
    ),
    Suite(
        "physics",
        "Physics",
        "a physics model",
        ("Equations", "Electrolyte", "Conditions", "Exposed values"),
        "build",
        "sym_o_function",
    ),
    Suite(
        "study",
        "Study",
        "a study",
        ("Overview", "Study setup", "Sweep", "Charge on the mesh", "Runs"),
        "use",
        "sym_o_science",
    ),
    Suite(
        "analysis",
        "Analysis",
        "results and comparisons",
        ("Results explorer", "Comparison"),
        "use",
        "sym_o_monitoring",
    ),
)

FRAME_CONTROLS: tuple[str, ...] = (
    "menu-file",
    "menu-view",
    "menu-help",
    "project-name",
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

SCREENS: tuple[Screen, ...] = (
    *(Screen(suite.id, f"/{suite.id}", (*FRAME_CONTROLS, "suite-body")) for suite in SUITES),
    Screen("changes", "/study?panel=changes", (*FRAME_CONTROLS, "changes-list")),
    Screen("problems", "/study?panel=problems", (*FRAME_CONTROLS, "problems-list")),
    Screen(
        "settings",
        "/molecular?dialog=settings",
        (
            *FRAME_CONTROLS,
            "settings-theme",
            "settings-density",
            "settings-spacing",
            "settings-background",
            "theme-colours",
            "theme-duplicate",
            "settings-keys",
        ),
    ),
    Screen("palette", "/molecular?palette=1", (*FRAME_CONTROLS, "palette-input", "palette-list")),
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
