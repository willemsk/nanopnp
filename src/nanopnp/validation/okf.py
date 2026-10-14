"""Read and check the knowledge bundle under ``.knowledge/`` (VER-68; section 8.2.7 G12)."""

from __future__ import annotations

import ast
import re
import subprocess
import tomllib
import unicodedata
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

import yaml

REPOSITORY = Path(__file__).resolve().parents[3]

OKF_VERSION = "0.2"

TYPES: frozenset[str] = frozenset(
    {
        "Overview",
        "Orientation",
        "Physics",
        "Erratum",
        "Author Ruling",
        "Open Item",
        "Background",
        "Domain",
        "Pipeline",
        "Numerics",
        "Library Behaviour",
        "Benchmark",
        "Reference Settings",
        "Test Evidence",
        "Glossary",
    }
)

SOURCE_IDS: frozenset[str] = frozenset({"thesis", "paper", "esi", "comsol-report"})

MODEL_IDENTIFIER = re.compile(r"(?i)\b(claude-)?(opus|sonnet|haiku|fable)\b")

HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*$")

EXPLICIT_ID = re.compile(r"[ \t]*\{#([\w:.-]+)\}$")

FENCE = re.compile(r"^[ \t]*(```|~~~)")

CODE_SPAN = re.compile(r"(`+)(.+?)\1")

CITATION = re.compile(r"\.knowledge(?:/(?P<path>[\w./-]*[\w/-]))?(?:#(?P<anchor>[\w:.-]*\w))?")

LEGACY = re.compile(r"\.knowledge/\d\d(?:-[\w-]+\.md)?(?::[\d-]+)?`*\s*(?:§|section\b)")

PLACEHOLDER = re.compile(r"^(?:0N|NN)|[<*]")

CLAIM = re.compile(r"\[(tested|verified)(?::\s*([^\]]+?))?(?:,\s*verified)?\s*\]")

FOOTNOTE_USE = re.compile(r"\[\^([A-Za-z0-9_-]+)\](?!:)")

FOOTNOTE_DEFINITION = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:", re.MULTILINE)

LOG_DATE = re.compile(r"^## (\d{4}-\d\d-\d\d)$")

PENDING = "pending"

ARITHMETIC = "process:arithmetic"

AUTHOR = "human:willemsk"

PENDING_FILE = "pending.yaml"

LINK_TARGET = re.compile(r"\]\(([^)\s#]+)")


@dataclass(frozen=True)
class Finding:
    """One refusal, with the file and line it names."""

    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


@dataclass(frozen=True)
class Heading:
    """A heading of a Markdown body and the anchor the documentation build gives it."""

    level: int
    line: int
    text: str
    anchor: str


@dataclass(frozen=True)
class Concept:
    """A parsed concept: its path, frontmatter, body and the line the body starts on."""

    path: Path
    meta: dict[str, object]
    body: str
    first_line: int


def slugify(text: str) -> str:
    """Return the table-of-contents slug of ``text``, as the documentation build computes it."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    stripped = re.sub(r"[^\w\s-]", "", folded).strip().lower()
    return re.sub(r"[-\s]+", "-", stripped)


def _unique(anchor: str, taken: set[str]) -> str:
    while anchor in taken or not anchor:
        match = re.match(r"^(.*)_([0-9]+)$", anchor)
        anchor = f"{match.group(1)}_{int(match.group(2)) + 1}" if match else f"{anchor}_1"
    return anchor


def _plain(title: str) -> str:
    title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", title)
    return re.sub(r"[*`]", "", title)


def headings(body: str, first_line: int = 1) -> list[Heading]:
    """Return the headings of ``body`` outside code fences, each with its anchor."""
    found: list[Heading] = []
    taken: set[str] = set()
    fenced = False
    for offset, line in enumerate(body.splitlines()):
        if FENCE.match(line):
            fenced = not fenced
            continue
        match = None if fenced else HEADING.match(line)
        if match is None:
            continue
        title = match.group(2)
        explicit = EXPLICIT_ID.search(title)
        if explicit:
            title = title[: explicit.start()]
            anchor = explicit.group(1)
        else:
            anchor = _unique(slugify(_plain(title)), taken)
        taken.add(anchor)
        found.append(Heading(len(match.group(1)), first_line + offset, title, anchor))
    return found


def parse_concept(path: Path) -> Concept | str:
    """Return the parsed concept at ``path``, or the reason its frontmatter is unusable."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return "no frontmatter block"
    end = text.find("\n---\n", 3)
    if end < 0:
        return "frontmatter block is not closed"
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError as error:
        return f"frontmatter does not parse: {error}"
    if not isinstance(meta, dict):
        return "frontmatter is not a mapping"
    first_line = text.count("\n", 0, end + 5) + 1
    return Concept(path, meta, text[end + 5 :], first_line)


def _concepts(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.md")):
        if path.name not in {"index.md", "log.md"}:
            yield path


def _relative(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def _listed(index: Path) -> set[str]:
    return {Path(target).as_posix() for target in LINK_TARGET.findall(index.read_text("utf-8"))}


def check_structure(root: Path) -> list[Finding]:
    """Refuse a bundle whose files, headers, indexes or log are out of form (VER-68 1)."""
    findings: list[Finding] = []
    base = root.parent
    index = root / "index.md"
    if not index.is_file():
        return [Finding(_relative(index, base), 1, "the root index.md is missing")]
    head = parse_concept(index)
    if isinstance(head, Concept):
        declared = head.meta.get("okf_version")
        if declared != OKF_VERSION:
            findings.append(
                Finding(_relative(index, base), 1, f"okf_version must be {OKF_VERSION!r}")
            )
    else:
        findings.append(Finding(_relative(index, base), 1, f"okf_version must be declared: {head}"))
    listed = _listed(index)
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        if f"{directory.name}/index.md" not in listed and f"{directory.name}/" not in listed:
            findings.append(
                Finding(_relative(index, base), 1, f"does not list the directory {directory.name}")
            )
    for directory in sorted(path for path in root.rglob("*") if path.is_dir()):
        listing = directory / "index.md"
        names = [p.name for p in directory.glob("*.md") if p.name not in {"index.md", "log.md"}]
        if not listing.is_file():
            if names:
                findings.append(Finding(_relative(directory, base), 1, "has no index.md"))
            continue
        shown = _listed(listing)
        for name in sorted(names):
            if name not in shown:
                findings.append(Finding(_relative(listing, base), 1, f"does not list {name}"))
    for path in _concepts(root):
        parsed = parse_concept(path)
        name = _relative(path, base)
        if isinstance(parsed, str):
            findings.append(Finding(name, 1, parsed))
            continue
        kind = parsed.meta.get("type")
        if not isinstance(kind, str) or not kind:
            findings.append(Finding(name, 1, "type is missing or empty"))
        elif kind not in TYPES:
            findings.append(Finding(name, 1, f"type {kind!r} is outside the closed list"))
        findings += _check_header(parsed, name)
    findings += _check_log(root / "log.md", base)
    return findings


def _check_header(concept: Concept, name: str) -> list[Finding]:
    findings: list[Finding] = []
    generated = concept.meta.get("generated")
    by = generated.get("by") if isinstance(generated, dict) else None
    if isinstance(by, str) and MODEL_IDENTIFIER.search(by):
        findings.append(Finding(name, 1, f"generated.by names a model: {by!r}"))
    return findings


def _check_log(log: Path, base: Path) -> list[Finding]:
    name = _relative(log, base)
    if not log.is_file():
        return [Finding(name, 1, "log.md is missing")]
    lines = log.read_text(encoding="utf-8").splitlines()
    findings: list[Finding] = []
    if not lines or not lines[0].startswith("# "):
        findings.append(Finding(name, 1, "log.md must open with a title"))
    dates: list[str] = []
    for number, line in enumerate(lines, start=1):
        if line.startswith("## "):
            match = LOG_DATE.match(line)
            if match is None:
                findings.append(Finding(name, number, "a log heading must be an ISO date"))
            else:
                dates.append(match.group(1))
        elif line.startswith("* ") and not dates:
            findings.append(Finding(name, number, "an entry stands outside any date"))
    if dates != sorted(dates, reverse=True):
        findings.append(Finding(name, 1, "log dates must run newest first"))
    return findings


def _code_ranges(line: str) -> list[tuple[int, int]]:
    return [match.span() for match in CODE_SPAN.finditer(line)]


def _resolve(root: Path, path: str | None) -> Path | None:
    if path is None:
        return root / "index.md"
    target = root / path
    if target.is_file():
        return target
    if target.is_dir():
        return target / "index.md"
    return None


def _anchors(file: Path) -> set[str]:
    text = file.read_text(encoding="utf-8")
    parsed = parse_concept(file)
    if isinstance(parsed, Concept):
        return {h.anchor for h in headings(parsed.body, parsed.first_line)}
    return {h.anchor for h in headings(text)}


def check_citations(root: Path, files: Iterable[Path], base: Path) -> list[Finding]:
    """Refuse each ``.knowledge/`` address in ``files`` that reaches nothing (VER-68 2)."""
    findings: list[Finding] = []
    cache: dict[Path, set[str]] = {}
    for file in files:
        try:
            text = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        name = _relative(file, base)
        fenced = False
        for number, line in enumerate(text.splitlines(), start=1):
            if FENCE.match(line):
                fenced = not fenced
            ranges = _code_ranges(line)
            for match in CITATION.finditer(line):
                path = match.group("path")
                inside = fenced or any(a <= match.start() < b for a, b in ranges)
                if inside and path is not None and PLACEHOLDER.search(path):
                    continue
                if LEGACY.match(line, match.start()):
                    findings.append(
                        Finding(name, number, f"legacy section form {match.group(0)!r}")
                    )
                    continue
                target = _resolve(root, path)
                if target is None:
                    findings.append(Finding(name, number, f"{match.group(0)!r} reaches no concept"))
                    continue
                anchor = match.group("anchor")
                if anchor is not None:
                    if target not in cache:
                        cache[target] = _anchors(target)
                    if anchor not in cache[target]:
                        findings.append(
                            Finding(name, number, f"{match.group(0)!r} reaches no heading")
                        )
    return findings


def tracked_files(repository: Path) -> list[Path]:
    """Return the files git tracks in ``repository``, existing ones only."""
    done = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repository, capture_output=True, check=True
    )
    names = done.stdout.decode("utf-8").split("\0")
    return [repository / n for n in names if n and (repository / n).is_file()]


def test_names(tests: Path) -> set[str]:
    """Return the node ids of the test functions under ``tests``, read from their syntax trees."""
    names: set[str] = set()
    for file in sorted(tests.rglob("test_*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        rel = f"{tests.name}/{_relative(file, tests)}"
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("test"):
                    names.add(f"{rel}::{node.name}")
            elif isinstance(node, ast.ClassDef):
                methods = [i for i in node.body if isinstance(i, ast.FunctionDef)]
                names |= {
                    f"{rel}::{node.name}::{m.name}" for m in methods if m.name.startswith("test")
                }
    return names


def claims(body: str, first_line: int = 1) -> list[tuple[int, str, str | None]]:
    """Return ``(line, kind, test)`` for each ledger marker in ``body`` outside code."""
    found: list[tuple[int, str, str | None]] = []
    fenced = False
    for offset, line in enumerate(body.splitlines()):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        blank = CODE_SPAN.sub(lambda m: " " * len(m.group(0)), line)
        for match in CLAIM.finditer(blank):
            found.append((first_line + offset, match.group(1), match.group(2)))
    return found


def _tests_of(concept: Concept) -> tuple[set[str], int, int, int]:
    named: set[str] = set()
    pending = bare = verified = 0
    for _, kind, test in claims(concept.body, concept.first_line):
        if kind == "verified":
            verified += 1
        elif test is None:
            bare += 1
        elif test.strip() == PENDING:
            pending += 1
        else:
            named.add(test.strip())
    return named, pending, bare, verified


def verified_set(concept: Concept) -> set[str]:
    """Return the ``verified`` actors the concept's own claims and type require."""
    named, _, _, arithmetic = _tests_of(concept)
    expected = {f"process:{test}" for test in named}
    if arithmetic:
        expected.add(ARITHMETIC)
    if concept.meta.get("type") == "Author Ruling":
        expected.add(AUTHOR)
    return expected


def _actors(meta: dict[str, object]) -> set[str]:
    value = meta.get("verified")
    entries = [value] if isinstance(value, dict) else value if isinstance(value, list) else []
    return {str(e.get("by")) for e in entries if isinstance(e, dict)}


def pending_counts(root: Path) -> dict[str, dict[str, int]]:
    """Return per concept path the ``tested_pending`` and ``verified_unsourced`` claim counts."""
    counts: dict[str, dict[str, int]] = {}
    for path in _concepts(root):
        parsed = parse_concept(path)
        if isinstance(parsed, str):
            continue
        _, pending, _, _ = _tests_of(parsed)
        unsourced = 0
        for line, kind, _ in claims(parsed.body, parsed.first_line):
            if kind == "verified" and not _sourced(parsed.body, line - parsed.first_line):
                unsourced += 1
        if pending or unsourced:
            counts[_relative(path, root)] = {
                "tested_pending": pending,
                "verified_unsourced": unsourced,
            }
    return counts


def _sourced(body: str, offset: int) -> bool:
    lines = body.splitlines()
    return bool(FOOTNOTE_USE.search(lines[offset])) if offset < len(lines) else False


def check_ledger(root: Path, tests: Path, lock: Path | None = None) -> list[Finding]:
    """Refuse a concept whose markers, footnotes, verified set or versions disagree (VER-68 3-6)."""
    findings: list[Finding] = []
    base = root.parent
    known = test_names(tests)
    locked = _locked(lock) if lock is not None and lock.is_file() else {}
    for path in _concepts(root):
        parsed = parse_concept(path)
        if isinstance(parsed, str):
            continue
        name = _relative(path, base)
        for number, kind, test in claims(parsed.body, parsed.first_line):
            if kind == "tested" and test is None:
                findings.append(Finding(name, number, "a bare [tested] marker names no test"))
            elif kind == "tested" and test and test.strip() not in {PENDING, *known}:
                findings.append(Finding(name, number, f"[tested: {test}] names no test"))
        expected = verified_set(parsed)
        actual = _actors(parsed.meta)
        for missing in sorted(expected - actual):
            findings.append(Finding(name, 1, f"verified lacks {missing}"))
        for extra in sorted(actual - expected):
            findings.append(Finding(name, 1, f"verified holds {extra}, which no claim needs"))
        findings += _check_sources(parsed, name)
        findings += _check_tested_with(parsed, name, locked)
    return findings


def _check_sources(concept: Concept, name: str) -> list[Finding]:
    sources = concept.meta.get("sources")
    ids = (
        {s.get("id") for s in sources if isinstance(s, dict)}
        if isinstance(sources, list)
        else set()
    )
    findings: list[Finding] = []
    fenced = False
    for offset, line in enumerate(concept.body.splitlines()):
        if FENCE.match(line):
            fenced = not fenced
        if fenced:
            continue
        stripped = CODE_SPAN.sub("", line)
        labels = FOOTNOTE_USE.findall(stripped)
        defined = FOOTNOTE_DEFINITION.findall(stripped)
        for label in [*labels, *defined]:
            if label not in ids:
                findings.append(
                    Finding(
                        name, concept.first_line + offset, f"footnote [^{label}] is no source id"
                    )
                )
    return findings


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text.split("+")[0]))


def _locked(lock: Path) -> dict[str, str]:
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    return {
        str(p["name"]).lower().replace("_", "-"): str(p["version"]) for p in data.get("package", [])
    }


def _check_tested_with(concept: Concept, name: str, locked: dict[str, str]) -> list[Finding]:
    declared = concept.meta.get("tested_with")
    if not isinstance(declared, dict):
        return []
    findings: list[Finding] = []
    for package, version in declared.items():
        key = str(package).lower().replace("_", "-")
        if key not in locked:
            findings.append(Finding(name, 1, f"tested_with names {package}, absent from uv.lock"))
        elif _version(str(version)) < _version(locked[key]):
            findings.append(
                Finding(name, 1, f"tested_with {package} {version} is older than {locked[key]}")
            )
    return findings


def check_pending(root: Path, ceiling: int) -> list[Finding]:
    """Refuse a ``pending.yaml`` that differs from the files, or a total above ``ceiling`` (G3)."""
    committed_path = root / PENDING_FILE
    name = _relative(committed_path, root.parent)
    if not committed_path.is_file():
        return [Finding(name, 1, "pending.yaml is missing")]
    committed = yaml.safe_load(committed_path.read_text(encoding="utf-8")) or {}
    measured = pending_counts(root)
    findings: list[Finding] = []
    for path in sorted(set(committed) | set(measured)):
        if committed.get(path) != measured.get(path):
            findings.append(
                Finding(
                    name,
                    1,
                    f"{path}: committed {committed.get(path)}, files hold {measured.get(path)}",
                )
            )
    total = sum(sum(entry.values()) for entry in measured.values())
    if total > ceiling:
        findings.append(Finding(name, 1, f"{total} pending claims exceed the ceiling {ceiling}"))
    return findings


def check_bundle(
    root: Path, tests: Path, lock: Path | None, ceiling: int, files: Iterable[Path] = ()
) -> list[Finding]:
    """Return every VER-68 finding for the bundle at ``root`` and the citations in ``files``."""
    findings = check_structure(root)
    findings += check_ledger(root, tests, lock)
    findings += check_pending(root, ceiling)
    findings += check_citations(root, files, root.parent)
    return findings
