# Trebuchet Builder

Design a small 3D-printable trebuchet, see how far it should throw, and download one print plate (3MF) plus STLs. The default kit prints on one 220 mm plate and snaps together with no hardware: just string and coins. A Quiver Design Works project, sister to [Rocket Builder](https://github.com/the-feve/rocket-builder-web).

- `geometry/trebgen/`: design maths (`params.py`), throw physics (`physics.py`), parts in build123d (`parts.py`), plate layout (`layout.py`), shopping list, assembly steps, STL/3MF/GLB/PNG export.
- `docs/design_research.md`: how other printed trebuchets do it, the fit numbers, and why the parts look the way they do.
- `server/`: FastAPI app and the page.

Status and next steps: `HANDOFF.md`. Roadmap: `TODO.md`.
