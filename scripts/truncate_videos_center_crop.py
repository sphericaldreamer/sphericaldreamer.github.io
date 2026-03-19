#!/usr/bin/env python3
"""
Center-crop each video to half its original height (full width unchanged).
Output mirrors the folder layout under static/videos/truncated/

Requires: ffmpeg on PATH

Usage (from repo root):
  python3 scripts/truncate_videos_center_crop.py
  python3 scripts/truncate_videos_center_crop.py --root static/videos
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def find_videos(root: Path, truncated_root: Path) -> list[Path]:
    trunc_r = truncated_root.resolve()
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv"}:
            continue
        try:
            p.resolve().relative_to(trunc_r)
            continue  # skip files already under output tree
        except ValueError:
            pass
        out.append(p)
    return sorted(out)


def output_path(video: Path, root: Path, truncated_root: Path) -> Path:
    rel = video.relative_to(root)
    return truncated_root / rel


def crop_half_height_center(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # crop=out_w:out_h:x:y — full width, half height, vertically centered (y = ih/4)
    vf = "crop=iw:ih/2:0:ih/4"
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "static" / "videos",
        help="Root folder to scan for videos (default: static/videos)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output root (default: <root>/truncated)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Error: not a directory: {root}", file=sys.stderr)
        return 1

    truncated_root = (args.out or (root / "truncated")).resolve()

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg not found. Install ffmpeg and ensure it is on PATH.", file=sys.stderr)
        return 1

    videos = find_videos(root, truncated_root)
    if not videos:
        print(f"No videos found under {root}")
        return 0

    print(f"Found {len(videos)} video(s). Output -> {truncated_root}\n")
    for src in videos:
        dst = output_path(src, root, truncated_root)
        print(f"  {src.relative_to(root)} -> {dst.relative_to(truncated_root)}")
        try:
            crop_half_height_center(src, dst)
        except subprocess.CalledProcessError as e:
            print(f"    ffmpeg failed ({e.returncode})", file=sys.stderr)
            return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
