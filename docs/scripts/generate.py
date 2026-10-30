"""Write the generated pages of the documentation site into ``docs/_generated/``.

Run before every build, and never committed (WP16 D4, D5)::

    uv run docs/scripts/generate.py && uv run mkdocs build --strict

Six kinds of file, all derived:

- **The model.** ``SPECIFICATION.md``, the ``specification/`` bundle and the ``knowledge/``
  bundle, copied verbatim. The model is documented by rendering its normative records,
  never by restating their equations (``SPECIFICATION.md`` section 8.1): restated
  summaries of this model drift and get copied wrong.
- **The examples.** Each ``examples/NN-slug/README.md``, so the site shows the exact
  text whose tagged commands VER-46 executes.
- **The release notes.** ``CHANGELOG.md``, copied verbatim, as the versions it records are the
  git tags themselves (``SPECIFICATION.md`` section 2.7, Versioning).
- **The references.** The case-file, field-document, command-line, exit-code and API pages, rendered
  from the live objects by :mod:`nanopnp.cli.reference`.
- **The case schema.** ``reference/case.schema.json``, the case document's JSON Schema (VER-76).
- **The modularity measurements.** The numbers the modularity report quotes, measured
  on this tree by :func:`nanopnp.validation.modularity.render_measurements` (WP35 D1).

Only links are touched in the copies. A relative link to another copied page is
pointed at its copy, and one to any other repository file is pointed at the file on
GitHub, so that the strict build proves every link resolves. This is a separate step
rather than an MkDocs hook so that the configuration stays readable by Zensical
(``knowledge/07-software-stack/13-documentation-tooling-mkdocs-material.md``).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from pathlib import Path

from nanopnp.cli.reference import (
    render_api_reference,
    render_case_reference,
    render_cli_reference,
    render_exit_codes,
    render_field_reference,
)
from nanopnp.io.case_paths import case_json_schema
from nanopnp.validation.modularity import render_measurements
from nanopnp.validation.okf import navigation, splice_navigation

logger = logging.getLogger("generate")

ROOT = Path(__file__).resolve().parents[2]
"""The repository root."""

OUTPUT = ROOT / "docs" / "_generated"
"""Where every generated page goes; gitignored."""

REPOSITORY = "https://github.com/willemsk/nanopnp/blob/main"
"""Where a link to a repository file that is not on the site is pointed."""

LINK = re.compile(r"(!?\[[^\]]*\])\(([^)\s]+)\)")
"""An inline Markdown link or image, capturing its text and its target."""

CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
"""A fenced block or an inline code span, whose text is shown verbatim, never a link."""


def _copies() -> dict[Path, Path]:
    """Return ``{source: destination}`` for every page copied verbatim."""
    pages = {
        ROOT / "SPECIFICATION.md": OUTPUT / "model" / "specification.md",
        ROOT / "CHANGELOG.md": OUTPUT / "project" / "changelog.md",
    }
    bundle = ROOT / "knowledge"
    for source in sorted(bundle.rglob("*.md")):
        pages[source] = OUTPUT / "model" / "knowledge" / source.relative_to(bundle)
    specification = ROOT / "specification"
    for source in sorted(specification.rglob("*.md")):
        pages[source] = OUTPUT / "model" / "specification" / source.relative_to(specification)
    # model/specification.md is already served at model/specification/, and MkDocs would let
    # the bundle's index overwrite it there without a warning.
    pages[specification / "index.md"] = OUTPUT / "model" / "specification" / "contents.md"
    for source in sorted((ROOT / "examples").glob("*/README.md")):
        pages[source] = OUTPUT / "examples" / f"{source.parent.name}.md"
    return pages


def _relative(target: Path, start: Path) -> str:
    """Return ``target`` relative to the directory ``start``, POSIX-style."""
    parts_target = target.parts
    parts_start = start.parts
    common = 0
    while (
        common < min(len(parts_target), len(parts_start))
        and parts_target[common] == parts_start[common]
    ):
        common += 1
    up = [".."] * (len(parts_start) - common)
    return "/".join([*up, *parts_target[common:]]) or "."


def rewrite_links(text: str, source: Path, destination: Path, pages: dict[Path, Path]) -> str:
    """Point each relative link of a copied page at the copy or at GitHub."""

    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            return match.group(0)
        path, _, anchor = target.partition("#")
        resolved = (source.parent / path).resolve()
        suffix = f"#{anchor}" if anchor else ""
        if resolved in pages:
            return f"{label}({_relative(pages[resolved], destination.parent)}{suffix})"
        if not resolved.exists():
            raise SystemExit(f"{source.relative_to(ROOT)}: broken link {target!r}")
        return f"{label}({REPOSITORY}/{resolved.relative_to(ROOT).as_posix()}{suffix})"

    # Code is masked first: ``a[i](x)`` in a code span is not a link, and rewriting
    # it would alter a verbatim page or fail the build as a broken link. Masking
    # rather than splitting keeps a link whose label is code, [`x`](y), whole.
    spans: list[str] = []

    def mask(match: re.Match[str]) -> str:
        spans.append(match.group(0))
        return f"\0{len(spans) - 1}\0"

    masked = LINK.sub(replace, CODE.sub(mask, text))
    return re.sub(r"\0(\d+)\0", lambda match: spans[int(match.group(1))], masked)


def _correction_files() -> str:
    """Return every shipped correction parameter file, verbatim, as one page."""
    lines = [
        "# Shipped correction parameter files",
        "",
        "Each file under `data/corrections/`, verbatim. They are the fitted parameters of the",
        "ePNP-NS corrections, with the provenance of every coefficient in its comments; see",
        "[Correction data files](../../reference/corrections.md) for how a case selects one.",
        "",
    ]
    for path in sorted((ROOT / "data" / "corrections").glob("*.yaml")):
        lines += [f"## `{path.stem}`", "", "```yaml", path.read_text(encoding="utf-8").rstrip()]
        lines += ["```", ""]
    return "\n".join(lines)


def main() -> int:
    """Regenerate ``docs/_generated/`` from scratch."""
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    pages = _copies()
    for source, destination in pages.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text(encoding="utf-8")
        destination.write_text(rewrite_links(text, source, destination, pages), encoding="utf-8")
    rendered = {
        "reference/correction-files.md": _correction_files(),
        "reference/case-file.md": render_case_reference(),
        "reference/field-document.md": render_field_reference(),
        "reference/cli.md": render_cli_reference(),
        "reference/exit-codes.md": render_exit_codes(),
        "reference/api.md": render_api_reference(),
        "project/modularity-measurements.md": render_measurements(),
    }
    for name, text in rendered.items():
        path = OUTPUT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    schema = OUTPUT / "reference" / "case.schema.json"
    schema.write_text(json.dumps(case_json_schema(), indent=2) + "\n", encoding="utf-8")
    config = ROOT / "mkdocs.yml"
    current = config.read_text(encoding="utf-8")
    knowledge = "_generated/model/knowledge"
    nav = navigation(
        ROOT / "knowledge",
        knowledge,
        "Knowledge base",
        [f"{knowledge}/index.md"],
        [f"Log: {knowledge}/log.md"],
    )
    spliced = splice_navigation(current, nav, "knowledge")
    specification = "_generated/model/specification"
    opening = [f"{specification}.md", f"{specification}/contents.md"]
    nav = navigation(ROOT / "specification", specification, "Specification", opening)
    spliced = splice_navigation(spliced, nav, "specification")
    if spliced != current:
        config.write_text(spliced, encoding="utf-8")
    logger.info("wrote %d pages to %s", len(pages) + len(rendered) + 1, OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
