#!/usr/bin/env python3
"""
Copy equirectangular pairs from SphericalDreamer ICML qualitative experiment assets
into this site's static tree.

Source layout (under ASSETS):
  <scene>/<method>/eqr_x0.png, eqr_x1.png
or for layerpano3d / luciddreamer:
  <scene>/<method>/spherical/x=<float>/  (per-view folder)
  In each x= folder, pick the forward equirect: prefer *azi=0.00* with "-ng" in the
  filename if present, else azi=0.00.png.

Resolution order per (scene, method): experiments, then qualitative_images, then
qualitative_new_ld_lp3d (last wins so refreshed LD/LP3D renders override older trees).

Destination:
  <DEST>/static/images/qualitative_experiments/<scene>/<method>/eqr_x0.png
  <DEST>/static/images/qualitative_experiments/<scene>/<method>/eqr_x1.png
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

# Methods that use spherical/x=<...>/azi=... layout instead of flat eqr_x*.png
SPHERICAL_LAYOUT_METHODS = frozenset({"layerpano3d", "luciddreamer"})

SOURCE_BASE_NAMES = (
    "experiments",
    "qualitative_images",
    "qualitative_new_ld_lp3d",
)


def _parse_x_dir(name: str) -> float | None:
    if not name.startswith("x="):
        return None
    try:
        return float(name.split("=", 1)[1])
    except ValueError:
        return None


def list_spherical_x_dirs(spherical_root: Path) -> list[Path]:
    dirs: list[tuple[float, Path]] = []
    for p in spherical_root.iterdir():
        if not p.is_dir():
            continue
        xv = _parse_x_dir(p.name)
        if xv is not None:
            dirs.append((xv, p))
    dirs.sort(key=lambda t: t[0])
    return [p for _, p in dirs]


def pick_azi_zero_image(x_dir: Path) -> Path:
    """Equirect with azimuth 0; prefer azi=0.00...-ng if multiple conventions exist."""
    pngs = sorted(x_dir.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"No PNG in {x_dir}")

    azi0 = [p for p in pngs if "azi=0.00" in p.name]
    if not azi0:
        raise FileNotFoundError(f"No azi=0.00* PNG in {x_dir} (have: {[p.name for p in pngs]})")

    with_ng = [p for p in azi0 if "-ng" in p.name]
    if with_ng:
        return with_ng[0]

    exact = [p for p in azi0 if p.name == "azi=0.00.png"]
    if exact:
        return exact[0]

    return azi0[0]


def resolve_pair(method_dir: Path, method: str) -> tuple[Path, Path] | None:
    m = method.lower()
    if m in SPHERICAL_LAYOUT_METHODS:
        sph = method_dir / "spherical"
        if not sph.is_dir():
            return None
        x_dirs = list_spherical_x_dirs(sph)
        if len(x_dirs) < 2:
            return None
        try:
            p0 = pick_azi_zero_image(x_dirs[0])
            p1 = pick_azi_zero_image(x_dirs[1])
        except FileNotFoundError:
            return None
        return (p0, p1)

    p0 = method_dir / "eqr_x0.png"
    p1 = method_dir / "eqr_x1.png"
    if p0.is_file() and p1.is_file():
        return (p0, p1)
    return None


def discover_scene_method_pairs(assets: Path) -> dict[tuple[str, str], tuple[Path, Path]]:
    """Later bases in SOURCE_BASE_NAMES override earlier entries (see module docstring)."""
    out: dict[tuple[str, str], tuple[Path, Path]] = {}
    for base_name in SOURCE_BASE_NAMES:
        base = assets / base_name
        if not base.is_dir():
            continue
        for scene_dir in sorted(base.iterdir()):
            if not scene_dir.is_dir() or scene_dir.name.startswith("."):
                continue
            scene = scene_dir.name
            for method_dir in sorted(scene_dir.iterdir()):
                if not method_dir.is_dir() or method_dir.name.startswith("."):
                    continue
                method = method_dir.name
                pair = resolve_pair(method_dir, method)
                if pair is not None:
                    out[(scene, method)] = pair
    return out


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    default_assets = Path(
        "/Users/a.schnepf/Documents/my_projects/SphericalDreamer - ICML/"
        "figures/qualitative_experiments/assets"
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--assets",
        type=Path,
        default=default_assets,
        help="Path to qualitative_experiments/assets",
    )
    ap.add_argument(
        "--dest",
        type=Path,
        default=repo_root,
        help="Repository root (images go under static/images/qualitative_experiments/)",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned copies only",
    )
    args = ap.parse_args()

    assets: Path = args.assets.expanduser().resolve()
    dest_root: Path = args.dest.expanduser().resolve()
    out_base = dest_root / "static" / "images" / "qualitative_experiments"

    if not assets.is_dir():
        print(f"ERROR: assets directory not found: {assets}", file=sys.stderr)
        return 1

    pairs = discover_scene_method_pairs(assets)
    if not pairs:
        print(f"No (scene, method) pairs resolved under {assets}", file=sys.stderr)
        return 1

    for (scene, method) in sorted(pairs.keys()):
        src0, src1 = pairs[(scene, method)]
        ddir = out_base / scene / method
        d0 = ddir / "eqr_x0.png"
        d1 = ddir / "eqr_x1.png"
        print(f"{scene}/{method}")
        print(f"  <- {src0}")
        print(f"  <- {src1}")
        if args.dry_run:
            continue
        ddir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src0, d0)
        shutil.copy2(src1, d1)

    print(f"\nDone. {len(pairs)} scene/method pairs -> {out_base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
