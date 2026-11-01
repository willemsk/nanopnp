# Phase 5 plan: the record

The text that amendments replaced in [the Phase 5 plan](phase-5-workbench.md), copied verbatim, one
dated section per amendment (§8.2.16 R4). Read it on demand; the plan states what holds now.

---

## 24 October 2026: WP5.01 gains the design round and the GUI development tools (§8.2.17 S21 to S23)

While WP5.01 was planned, the author ruled that it also holds an interactive design round on the
workbench's organisation and its look and feel (S21), and builds the workflow for developing the GUI
(S22); its plan may exceed the word caps (S23). Replaced text follows.

The *Design decisions* rows:

| The GUI | A tabbed workbench for P1 to P3, tools linked to live views | The author's brief (S2, S6) |
| Working loop | Artifact mockups; a live local loop | Both see and control it (S9) |

The scope of WP5.01 — Discovery and the design and requirements document (F5; S2 to S7, S11, S12):

Prose and Artifact pages only (S1). It publishes today's Qt shell, rendered offscreen, for the
author's keep, kill or change per screen; draws the author's three to five jobs as clickable
mockups; and writes `docs/design/workbench.md`: tabs, tools, the four live views, the project
folder, the guided QR-10 route, a glossary, and the three later tools with S3's room for equations.
Each settled requirement enters the specification tagged v0.6 or for its tool phase (F5). VER-43,
VER-44, VER-55, VER-60, ADR-004's packaging NOTE, CON-09's PySide6 clause, RSK-13, P3 and QR-10 are
restated for the browser shell (M3, S2, S12), each beside its clause and replacing it only at
`v0.6.0` (S17). It proposes a ruling on each inherited row.

---

## 24 October 2026: the author's areas supplied (§8.2.17 S24)

The author named the workbench's areas and made the design document public. Replaced text in
*What the author supplies*:

| Three to five concrete jobs | WP5.01's start | WP5.01 drafts from P1 to P3 and asks |

## 1 November 2026: the library packages ordered (§8.2.28 AD1 to AD5)

The first `/np-plan amend 5` planned WP5.03 to WP5.06 after the spike and placed REV-170 and REV-121; the shell packages wait for a second amendment after WP5.02. The replaced text read:

The status paragraph:

> **Status: in progress; WP5.01 delivered (awaiting `/np-ship`), WP5.02 after `v0.5.0`.** Written 24 October 2026, during Phase 4 (§8.2.17); WP5.01 amended
> the same day (S21 to S23; [the record](phase-5-record.md)). Planned:
> WP5.01, beside Phase 4 (S1), and WP5.02, after `v0.5.0`. The shell packages from WP5.03 and their
> estimate wait for `/np-plan amend 5` (S14); the close is last. Release: **v0.6** (`v0.6.0`).

The In brief:

> ## In brief
>
> **What changes.** The program gains a workbench in the web browser, combining molecular viewers
> and continuum modelling suites. Each step of the work gets a tab, its tools linked both ways to live
> pictures. This phase designs the whole workbench, then builds its frame over what the program
> already does, plus a tool that changes a residue's charge. A physics builder, a 3D side-chain
> mutator and a pore-shape drawing tool follow in phases of their own. Design can start now; building
> waits for the current phase's release.
>
> **Cost.** The two design packages take about two to four weeks. The amendment after them prices
> the rest.
>
> **What could go wrong.** The scope could pull effort from validation, so each new tool is its own
> phase, ordered against validation later. The technology could fit poorly, so one hard screen is
> built two ways and both are measured.
>
> **Your call.** Who is the lab colleague who will try the workbench unaided at the end?
> *Recommendation:* name them during the design study, so the final test can be scheduled.

The shell's entry:

> ### WP5.03 onward — The shell (provisional)
>
> The workbench's frame, its four suites over today's capabilities and the four live views, the charge-level
> mutator, the project folder, `nanopnp gui`, then Qt's removal and documentation increment 5. Before
> the mutator, a library package moves protonation before the density, the protonated density the
> validated default (REV-135; §8.2.19 U2). The amendment also runs the sweep's design round (REV-139,
> U4) and orders REV-136's capabilities (U3). The mutator lands library first: a `charge/` function that sets a residue's charge state, with a Tier 1
> test that the projected charge changes by that residue's alone, before its shell control (§8.1;
> RSK-15). They wait on WP5.01's requirements and WP5.02's framework ruling; `/np-plan amend 5` plans
> them from WP5.03.
