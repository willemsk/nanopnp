"""Tabulate and plot the two I-V sweeps of this example.

Run from this directory, after both ``nanopnp sweep run`` commands::

    python plot_iv.py iv-charged iv-uncharged

Reads each sweep's ``dataset.csv`` and writes ``iv.csv``: one row per member,
with its sweep, bias, current and status. Plots ``iv.png`` when matplotlib is
installed (the ``examples`` extra); the CSV is written either way. A
member that did not converge keeps its row, with an empty current, rather than
disappearing from the curve.
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

log = logging.getLogger("plot_iv")


def read_dataset(directory: Path) -> list[dict[str, str]]:
    """Return the rows of one sweep's CSV export, skipping its comment line."""
    with (directory / "dataset.csv").open(encoding="utf-8") as stream:
        return list(csv.DictReader(line for line in stream if not line.startswith("#")))


def main(directories: list[str]) -> None:
    """Write ``iv.csv`` and, if matplotlib imports, ``iv.png``."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    curves: dict[str, list[tuple[float, float]]] = {}
    with Path("iv.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["sweep", "bias_V", "current_A", "status"])
        for name in directories:
            rows = sorted(read_dataset(Path(name)), key=lambda row: float(row["bias_V"] or 0))
            for row in rows:
                writer.writerow([name, row["bias_V"], row["current_A"], row["status"]])
                if row["status"] == "ok":
                    curves.setdefault(name, []).append(
                        (float(row["bias_V"]), float(row["current_A"]))
                    )
    log.info("wrote iv.csv")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        log.info("matplotlib is not installed; iv.csv holds the numbers")
        return
    figure, axes = plt.subplots(figsize=(5, 4))
    for name, points in curves.items():
        bias, current = zip(*points, strict=True)
        axes.plot([v * 1e3 for v in bias], [i * 1e9 for i in current], "o-", label=name)
    axes.axhline(0.0, color="grey", linewidth=0.5)
    axes.axvline(0.0, color="grey", linewidth=0.5)
    axes.set_xlabel("bias (mV)")
    axes.set_ylabel("current (nA)")
    axes.legend()
    figure.savefig("iv.png", dpi=150, bbox_inches="tight")
    log.info("wrote iv.png")


if __name__ == "__main__":
    main(sys.argv[1:])
