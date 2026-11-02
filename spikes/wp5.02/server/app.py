"""One FastAPI app both candidates share: the fixture and the link, nothing else."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from .link import OUT, Link

app = FastAPI()
_link: Link | None = None


def link() -> Link:
    global _link
    if _link is None:
        _link = Link()
    return _link


def structure_path() -> Path:
    return OUT / "2wcd-prepared.pdb"


def map_path() -> Path:
    return OUT / "map.png"


def residue(key: str) -> dict[str, object]:
    try:
        markers = link().residue_markers(key)
    except KeyError:
        raise HTTPException(404, f"no charged residue {key!r}") from None
    return {"key": key, "markers": markers}


def point(r_nm: float, z_nm: float) -> dict[str, object]:
    return {"residues": link().residues_at(r_nm, z_nm)}


@app.get("/api/structure")
def get_structure() -> FileResponse:
    return FileResponse(structure_path(), media_type="chemical/x-pdb")


@app.get("/api/map")
def get_map() -> FileResponse:
    return FileResponse(map_path(), media_type="image/png")


@app.get("/api/map/extent")
def get_extent() -> JSONResponse:
    return JSONResponse(link().extent)


@app.get("/api/residues")
def get_residues() -> JSONResponse:
    return JSONResponse(link().residues())


@app.get("/api/residue/{key}")
def get_residue(key: str) -> JSONResponse:
    return JSONResponse(residue(key))


@app.get("/api/point")
def get_point(r_nm: float, z_nm: float) -> JSONResponse:
    return JSONResponse(point(r_nm, z_nm))
