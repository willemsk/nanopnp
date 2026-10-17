"""VER-68: the knowledge base is a conformant bundle (section 8.2.7 G3, G12)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from nanopnp.validation import okf

HEADER = """---
type: {kind}
title: Thing
description: A thing.
{extra}---
"""

BODY = "## 1. Thing\n\n### 1.1 Detail\n\nText.\n"


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "01-a").mkdir(parents=True)
    (root / "index.md").write_text(
        '---\nokf_version: "0.2"\n---\n\n# Notes\n\n* [A](01-a/index.md) - the first\n',
        encoding="utf-8",
    )
    (root / "log.md").write_text(
        "# Log\n\n## 2026-10-14\n* **Creation**: made.\n", encoding="utf-8"
    )
    (root / "pending.yaml").write_text("{}\n", encoding="utf-8")
    (root / "01-a" / "index.md").write_text("# A\n\n* [Thing](01-thing.md) - a thing\n", "utf-8")
    _concept(tmp_path, "01-thing.md", BODY)
    tests = tmp_path / "tests" / "tier1"
    tests.mkdir(parents=True)
    (tests / "test_x.py").write_text(
        "def test_one():\n    pass\n\n\nclass TestC:\n    def test_two(self):\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text(
        '[[package]]\nname = "ngsolve"\nversion = "6.2.2504"\n', encoding="utf-8"
    )
    return tmp_path


def _concept(
    repository: Path, name: str, body: str, kind: str = "Physics", extra: str = ""
) -> Path:
    path = repository / "knowledge" / "01-a" / name
    path.write_text(HEADER.format(kind=kind, extra=extra) + body, encoding="utf-8")
    return path


def _check(repository: Path, ceiling: int = 0, files: tuple[Path, ...] = ()) -> list[str]:
    root = repository / "knowledge"
    found = okf.check_bundle(root, repository / "tests", repository / "uv.lock", ceiling, files)
    return [str(f) for f in found]


def _file(repository: Path, name: str, text: str) -> Path:
    path = repository / name
    path.write_text(text, encoding="utf-8")
    return path


def test_ver68_a_valid_bundle_has_no_finding(repository: Path) -> None:
    assert _check(repository) == []


def test_ver68_concept_without_type_or_frontmatter_is_refused(repository: Path) -> None:
    (repository / "knowledge/01-a/02-bare.md").write_text("## 2. Bare\n", encoding="utf-8")
    (repository / "knowledge/01-a/03-empty.md").write_text("---\ntype: ''\n---\n", "utf-8")
    (repository / "knowledge/01-a/index.md").write_text(
        "# A\n\n* [T](01-thing.md)\n* [B](02-bare.md)\n* [E](03-empty.md)\n", "utf-8"
    )
    found = _check(repository)
    assert any("02-bare.md:1: no frontmatter" in f for f in found)
    assert any("03-empty.md:1: type is missing" in f for f in found)


def test_ver68_type_outside_the_list_is_refused(repository: Path) -> None:
    _concept(repository, "01-thing.md", BODY, kind="Gossip")
    assert any("type 'Gossip' is outside" in f for f in _check(repository))


def test_ver68_undeclared_okf_version_is_refused(repository: Path) -> None:
    (repository / "knowledge/index.md").write_text("# Notes\n\n* [A](01-a/index.md)\n", "utf-8")
    assert any("index.md:1: okf_version must be declared" in f for f in _check(repository))
    (repository / "knowledge/index.md").write_text(
        '---\nokf_version: "0.1"\n---\n\n* [A](01-a/index.md)\n', "utf-8"
    )
    assert any("okf_version must be '0.2'" in f for f in _check(repository))


def test_ver68_root_index_missing_a_directory_is_refused(repository: Path) -> None:
    (repository / "knowledge/02-b").mkdir()
    found = _check(repository)
    assert any("does not list the directory 02-b" in f for f in found)


def test_ver68_root_index_may_link_a_directory_itself(repository: Path) -> None:
    (repository / "knowledge/index.md").write_text(
        '---\nokf_version: "0.2"\n---\n\n* [A](01-a/)\n', encoding="utf-8"
    )
    assert _check(repository) == []


def test_ver68_directory_index_missing_a_concept_is_refused(repository: Path) -> None:
    _concept(repository, "02-other.md", BODY)
    found = _check(repository)
    assert any("01-a/index.md:1: does not list 02-other.md" in f for f in found)


def test_ver68_log_out_of_form_is_refused(repository: Path) -> None:
    log = repository / "knowledge/log.md"
    log.write_text("# Log\n\n## 2026-10-12\n* old\n\n## 2026-10-14\n* new\n", "utf-8")
    assert any("newest first" in f for f in _check(repository))
    log.write_text("# Log\n\n## yesterday\n* x\n", "utf-8")
    assert any("log.md:3: a log heading must be an ISO date" in f for f in _check(repository))
    log.write_text("# Log\n\n## 2026-10-14\n\n## 2026-10-12\n* x\n", "utf-8")
    assert any("log.md:3: a log date holds no entry" in f for f in _check(repository))
    log.unlink()
    assert any("log.md is missing" in f for f in _check(repository))


def test_ver68_model_identifier_in_generated_by_is_refused(repository: Path) -> None:
    _concept(repository, "01-thing.md", BODY, extra="generated: {by: claude-opus-5, at: x}\n")
    assert any("generated.by names a model" in f for f in _check(repository))
    _concept(repository, "01-thing.md", BODY, extra="generated: {by: claude-code/0.5.0, at: x}\n")
    assert _check(repository) == []


def test_ver68_citation_to_missing_concept_or_heading_is_refused(repository: Path) -> None:
    good = _file(
        repository,
        "good.md",
        "See `knowledge/01-a/01-thing.md#11-detail`, `knowledge/` and "
        "[x](../knowledge/01-a/index.md).\n",
    )
    assert _check(repository, files=(good,)) == []
    bad = _file(
        repository,
        "bad.md",
        "A `knowledge/01-a/09-gone.md` and `knowledge/01-a/01-thing.md#nowhere`.\n",
    )
    found = _check(repository, files=(bad,))
    assert any("bad.md:1: 'knowledge/01-a/09-gone.md' reaches no concept" in f for f in found)
    assert any("reaches no heading" in f for f in found)


def test_ver68_legacy_section_form_is_refused(repository: Path) -> None:
    legacy = _file(
        repository,
        "legacy.md",
        "See `knowledge/06` §2.2, knowledge/04 section 3, `knowledge/01-a/index.md` section 1.\n",
    )
    found = _check(repository, files=(legacy,))
    assert sum("legacy section form" in f for f in found) == 3


def test_ver68_placeholder_in_a_code_span_passes(repository: Path) -> None:
    code = _file(repository, "code.md", "The form is `knowledge/0N §x`.\n")
    assert _check(repository, files=(code,)) == []
    prose = _file(repository, "prose.md", "The form is knowledge/0N here.\n")
    assert any("reaches no concept" in f for f in _check(repository, files=(prose,)))


def test_ver68_explicit_ids_and_repeats_give_anchors(repository: Path) -> None:
    body = "## 1. Thing\n\n### 1.1 Detail **[tested]** {#11-detail}\n\n### Repeat\n\n### Repeat\n"
    _concept(repository, "01-thing.md", body.replace("**[tested]** ", "**[tested: pending]** "))
    ok = _file(
        repository,
        "ok.md",
        "knowledge/01-a/01-thing.md#11-detail knowledge/01-a/01-thing.md#repeat_1\n",
    )
    pending = {"01-a/01-thing.md": {"tested_pending": 1, "verified_unsourced": 0}}
    (repository / "knowledge/pending.yaml").write_text(yaml.safe_dump(pending), "utf-8")
    assert _check(repository, ceiling=1, files=(ok,)) == []


def test_ver68_an_explicit_id_claimed_later_moves_an_earlier_slug() -> None:
    found = okf.headings("## Foo\n\n## Bar {#foo}\n\n## Baz\n")
    assert [h.anchor for h in found] == ["foo_1", "foo", "baz"]


def test_ver68_slug_matches_the_docs_build() -> None:
    markdown = pytest.importorskip("markdown.extensions.toc")
    for text in (
        "Plain heading",
        "Maxwell\u2013Hall access",
        "Gouy\u2013Chapman, 1:1",
        "Naïve  café",
        "a_b `c`",
    ):
        assert okf.slugify(text) == markdown.slugify(text, "-")


def test_ver68_tested_marker_naming_no_test_is_refused(repository: Path) -> None:
    body = BODY + "\nA claim **[tested: tests/tier1/test_x.py::test_gone]**.\n"
    _concept(repository, "01-thing.md", body, extra="verified: []\n")
    found = _check(repository)
    assert any(
        "01-thing.md:13: [tested: tests/tier1/test_x.py::test_gone] names no test" in f
        for f in found
    )


def test_ver68_bare_tested_marker_is_refused(repository: Path) -> None:
    _concept(repository, "01-thing.md", BODY + "\nA claim **[tested]**.\n")
    found = _check(repository)
    assert any("a bare [tested] marker" in f for f in found)


def test_ver68_class_test_name_resolves(repository: Path) -> None:
    body = BODY + "\nOne [tested: tests/tier1/test_x.py::TestC::test_two], two [tested: pending].\n"
    _concept(
        repository,
        "01-thing.md",
        body,
        extra="verified:\n  - {by: 'process:tests/tier1/test_x.py::TestC::test_two', at: x}\n",
    )
    pending = {"01-a/01-thing.md": {"tested_pending": 1, "verified_unsourced": 0}}
    (repository / "knowledge/pending.yaml").write_text(yaml.safe_dump(pending), "utf-8")
    assert _check(repository, ceiling=1) == []


def test_ver68_verified_set_must_equal_inline_tests_arithmetic_and_ruling(repository: Path) -> None:
    test = "tests/tier1/test_x.py::test_one"
    body = BODY + f"\nA [tested: {test}] claim and an [verified] sum.\n"
    unsourced = {"01-a/01-thing.md": {"tested_pending": 0, "verified_unsourced": 1}}
    (repository / "knowledge/pending.yaml").write_text(yaml.safe_dump(unsourced), "utf-8")
    extra = (
        f"verified:\n  - {{by: 'process:{test}', at: x}}\n  - {{by: 'process:arithmetic', at: x}}\n"
    )
    _concept(repository, "01-thing.md", body, extra=extra)
    assert _check(repository, ceiling=1) == []
    _concept(repository, "01-thing.md", body, extra=f"verified: {{by: 'process:{test}', at: x}}\n")
    assert any("verified lacks process:arithmetic" in f for f in _check(repository, ceiling=1))
    _concept(
        repository, "01-thing.md", body, extra=extra[:-1] + "\n  - {by: human:willemsk, at: x}\n"
    )
    assert any("holds human:willemsk" in f for f in _check(repository, ceiling=1))
    _concept(repository, "01-thing.md", BODY, kind="Author Ruling")
    assert any("verified lacks human:willemsk" in f for f in _check(repository))


def test_ver68_tested_with_older_than_lock_is_refused(repository: Path) -> None:
    def found(version: str, package: str = "ngsolve") -> list[str]:
        _concept(
            repository, "01-thing.md", BODY, extra=f"tested_with: {{{package}: '{version}'}}\n"
        )
        return _check(repository)

    assert found("6.2.2504") == []
    assert found("6.2.2504.0") == []
    assert found("6.2.2600") == []
    assert any("older than 6.2.2504" in f for f in found("6.2.2400"))
    assert any("netgen, absent from uv.lock" in f for f in found("1.0", "netgen"))


def test_ver68_footnote_without_source_is_refused(repository: Path) -> None:
    sources = "sources:\n  - {id: thesis, resource: https://example.org}\n"
    _concept(
        repository, "01-thing.md", BODY + "\nKnown.[^thesis]\n\n[^thesis]: Thesis.\n", extra=sources
    )
    assert _check(repository) == []
    _concept(repository, "01-thing.md", BODY + "\nKnown.[^folklore]\n", extra=sources)
    assert any("footnote [^folklore] is no source id" in f for f in _check(repository))


def test_ver68_pending_count_must_equal_the_committed_list(repository: Path) -> None:
    _concept(repository, "01-thing.md", BODY + "\nA [tested: pending] claim.\n")
    assert any("committed None, files hold" in f for f in _check(repository, ceiling=5))
    entry = {"tested_pending": 1, "verified_unsourced": 0}
    (repository / "knowledge/pending.yaml").write_text(
        yaml.safe_dump({"01-a/01-thing.md": entry}), "utf-8"
    )
    assert _check(repository, ceiling=5) == []
    entry["tested_pending"] = 2
    (repository / "knowledge/pending.yaml").write_text(
        yaml.safe_dump({"01-a/01-thing.md": entry}), "utf-8"
    )
    assert any("committed {'tested_pending': 2" in f for f in _check(repository, ceiling=5))


def test_ver68_pending_total_above_the_ceiling_is_refused(repository: Path) -> None:
    _concept(repository, "01-thing.md", BODY + "\nA [tested: pending] claim.\n")
    entry = {"tested_pending": 1, "verified_unsourced": 0}
    (repository / "knowledge/pending.yaml").write_text(
        yaml.safe_dump({"01-a/01-thing.md": entry}), "utf-8"
    )
    assert _check(repository, ceiling=1) == []
    assert any("exceed the ceiling 0" in f for f in _check(repository, ceiling=0))


def _scanned() -> list[Path]:
    # The test module quotes bad addresses on purpose; the correction file is hashed into the
    # pinned v0.5 solve key (VER-59), and the radii file's digest keys the density and protonation
    # artefacts, so a comment edit to either would move a key.
    skipped = {
        okf.REPOSITORY / "tests/tier1/test_okf_bundle.py",
        okf.REPOSITORY / "data/radii/pdb2pqr_charmm.yaml",
    }
    return [file for file in okf.tracked_files(okf.REPOSITORY) if file not in skipped]


def test_ver68_repository_citations_all_resolve() -> None:
    if not (okf.REPOSITORY / ".git").exists():
        pytest.skip("a git checkout is needed to list the tracked files")
    files = _scanned()
    found = okf.check_citations(okf.REPOSITORY / "knowledge", files, okf.REPOSITORY)
    assert not found, "\n".join(str(finding) for finding in found)


CEILING = 230


def test_ver68_the_bundle_conforms() -> None:
    if not (okf.REPOSITORY / ".git").exists():
        pytest.skip("a git checkout is needed to list the tracked files")
    files = _scanned()
    found = okf.check_bundle(
        okf.REPOSITORY / "knowledge",
        okf.REPOSITORY / "tests",
        okf.REPOSITORY / "uv.lock",
        CEILING,
        files,
    )
    assert not found, "\n".join(str(finding) for finding in found)


def test_ver68_every_heading_id_matches_the_docs_build() -> None:
    markdown = pytest.importorskip("markdown")
    root = okf.REPOSITORY / "knowledge"
    for path in sorted(root.rglob("*.md")):
        parsed = okf.parse_concept(path)
        if not isinstance(parsed, okf.Concept):
            continue
        converter = markdown.Markdown(extensions=["toc", "attr_list", "tables", "footnotes"])
        html = converter.convert(parsed.body)
        built = re.findall(r'<h[1-6] id="([^"]+)"', html)
        assert [h.anchor for h in okf.headings(parsed.body)] == built, path


def test_ver68_frontmatter_that_is_open_unparsed_or_no_mapping_is_refused(
    repository: Path,
) -> None:
    for name, text in (
        ("02-open.md", "---\ntype: Physics\n"),
        ("03-broken.md", "---\n: : [\n---\n"),
        ("04-list.md", "---\n- Physics\n---\n"),
    ):
        (repository / "knowledge/01-a" / name).write_text(text, encoding="utf-8")
    found = _check(repository)
    assert any("02-open.md:1: frontmatter block is not closed" in f for f in found)
    assert any("03-broken.md:1: frontmatter does not parse" in f for f in found)
    assert any("04-list.md:1: frontmatter is not a mapping" in f for f in found)


def test_ver68_missing_root_index_directory_index_log_or_pending_is_refused(
    repository: Path,
) -> None:
    root = repository / "knowledge"
    (root / "01-a" / "index.md").unlink()
    (root / "log.md").write_text("no title\n", encoding="utf-8")
    (root / "pending.yaml").unlink()
    found = _check(repository)
    assert any("01-a:1: has no index.md" in f for f in found)
    assert any("log.md must open with a title" in f for f in found)
    assert any("pending.yaml is missing" in f for f in found)
    (root / "index.md").unlink()
    assert any("the root index.md is missing" in f for f in _check(repository))


def test_ver68_citation_of_a_directory_or_an_index_heading_resolves(repository: Path) -> None:
    cites = _file(
        repository,
        "cites.md",
        "See `knowledge/01-a` and `knowledge/01-a/index.md#a`.\n",
    )
    assert _check(repository, files=(cites,)) == []


def test_ver68_navigation_is_read_from_the_index_pages(tmp_path: Path) -> None:
    root = tmp_path / "knowledge"
    (root / "01-a").mkdir(parents=True)
    (root / "index.md").write_text("* [Alpha *one*](01-a/index.md) - x\n* [Page](p.md) - y\n")
    (root / "01-a" / "index.md").write_text("* [1. First](f.md) - z\n")
    lines = okf.navigation(root, "g/k")
    assert lines == [
        "- Knowledge base:",
        "    - g/k/index.md",
        '    - "Alpha one":',
        "        - g/k/01-a/index.md",
        '        - "1. First": g/k/01-a/f.md',
        '    - "Page": g/k/p.md',
        "    - Log: g/k/log.md",
    ]
    config = f"nav:\n  {okf.NAV_BEGIN}\n  old\n  {okf.NAV_END}\nrest\n"
    spliced = okf.splice_navigation(config, ["- a:", "    - b"])
    assert spliced == f"nav:\n  {okf.NAV_BEGIN}\n  - a:\n      - b\n  {okf.NAV_END}\nrest\n"
    assert okf.splice_navigation(spliced, ["- a:", "    - b"]) == spliced


def test_ver68_mkdocs_navigation_equals_the_index_pages() -> None:
    config = okf.REPOSITORY / "mkdocs.yml"
    if not config.is_file():
        pytest.skip("not a source checkout")
    text = config.read_text(encoding="utf-8")
    lines = okf.navigation(okf.REPOSITORY / "knowledge", "_generated/model/knowledge")
    assert text == okf.splice_navigation(text, lines), "run uv run docs/scripts/generate.py"


def test_ver68_heading_markup_gives_the_slug_of_the_docs_build() -> None:
    markdown = pytest.importorskip("markdown")
    titles = [
        "An _emphasised_ word",
        "A __strong__ word",
        "snake_case_name stays",
        "Alpha &amp; beta",
        "Caf&eacute; and *stars*",
        "Image ![the alt](pic.png) here",
        "A [link](x.md) and `code_span`",
    ]
    body = "\n\n".join(f"## {title}" for title in titles)
    html_text = markdown.Markdown(extensions=["toc", "attr_list"]).convert(body)
    built = re.findall(r'<h2 id="([^"]+)"', html_text)
    assert [h.anchor for h in okf.headings(body)] == built
