#!/usr/bin/env python3
"""
Detect dominant colors in images and export results.

Outputs:
- outputs/colors_report.csv
- outputs/palettes/<image_stem>_palette.png

Usage examples:
  python detect_colors.py --input ./images --output ./outputs --k 8
  python detect_colors.py --input ./images --output ./outputs --k 10 --max-pixels 250000
"""
from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image


SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def load_image_rgb(path: Path) -> np.ndarray:
    # Convert to RGB and return as uint8 array HxWx3
    with Image.open(path) as im:
        im = im.convert("RGB")
        return np.array(im, dtype=np.uint8)


def downsample_pixels(pixels: np.ndarray, max_pixels: int, seed: int = 0) -> np.ndarray:
    """
    pixels: Nx3 uint8
    """
    n = pixels.shape[0]
    if n <= max_pixels:
        return pixels
    rng = np.random.default_rng(seed)
    idx = rng.choice(n, size=max_pixels, replace=False)
    return pixels[idx]


def kmeans_dominant_colors(pixels: np.ndarray, k: int, iters: int = 25, seed: int = 0):
    """
    Simple k-means implementation (no external dependencies).
    pixels: Nx3 uint8
    Returns:
      centers: kx3 float32
      counts: k int64 (# pixels assigned)
    """
    x = pixels.astype(np.float32)
    rng = np.random.default_rng(seed)

    # Initialize centers by sampling unique pixels if possible
    if x.shape[0] >= k:
        init_idx = rng.choice(x.shape[0], size=k, replace=False)
        centers = x[init_idx].copy()
    else:
        # Fallback: pad with random choices
        init_idx = rng.choice(x.shape[0], size=k, replace=True)
        centers = x[init_idx].copy()

    for _ in range(iters):
        # Assign step
        # distances: Nxk
        d = np.sum((x[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels = np.argmin(d, axis=1)

        # Update step
        new_centers = centers.copy()
        for i in range(k):
            mask = labels == i
            if np.any(mask):
                new_centers[i] = x[mask].mean(axis=0)
            else:
                # Re-seed empty cluster
                new_centers[i] = x[rng.integers(0, x.shape[0])]

        # Convergence check
        if np.allclose(new_centers, centers, atol=0.5):
            centers = new_centers
            break
        centers = new_centers

    # Final counts
    d = np.sum((x[:, None, :] - centers[None, :, :]) ** 2, axis=2)
    labels = np.argmin(d, axis=1)
    counts = np.bincount(labels, minlength=k)

    return centers, counts


def make_palette_image(colors: List[Tuple[int, int, int]], percents: List[float], width: int = 900, height: int = 140):
    """
    Creates a palette strip image with proportional blocks.
    """
    palette = Image.new("RGB", (width, height), (255, 255, 255))
    x0 = 0
    for (r, g, b), p in zip(colors, percents):
        w = max(1, int(round(width * p)))
        block = Image.new("RGB", (w, height), (r, g, b))
        palette.paste(block, (x0, 0))
        x0 += w

    # If rounding caused leftover space, fill it with last color
    if x0 < width and colors:
        block = Image.new("RGB", (width - x0, height), colors[-1])
        palette.paste(block, (x0, 0))

    return palette


@dataclass
class ColorResult:
    image_name: str
    image_path: str
    width: int
    height: int
    k: int
    colors_rgb: List[Tuple[int, int, int]]
    colors_hex: List[str]
    percents: List[float]


def process_image(path: Path, k: int, max_pixels: int, seed: int) -> ColorResult:
    arr = load_image_rgb(path)  # HxWx3
    h, w, _ = arr.shape
    pixels = arr.reshape(-1, 3)

    sampled = downsample_pixels(pixels, max_pixels=max_pixels, seed=seed)

    centers, counts = kmeans_dominant_colors(sampled, k=k, iters=30, seed=seed)

    # Sort by count descending
    order = np.argsort(counts)[::-1]
    counts = counts[order]
    centers = centers[order]

    total = counts.sum()
    percents = (counts / total).astype(float)

    colors_rgb = []
    for c in centers:
        r, g, b = [int(np.clip(round(v), 0, 255)) for v in c.tolist()]
        colors_rgb.append((r, g, b))

    colors_hex = [rgb_to_hex(c) for c in colors_rgb]

    return ColorResult(
        image_name=path.name,
        image_path=str(path),
        width=w,
        height=h,
        k=k,
        colors_rgb=colors_rgb,
        colors_hex=colors_hex,
        percents=percents.tolist(),
    )


def write_csv(results: List[ColorResult], out_csv: Path) -> None:
    """
    Each row is an image-color entry (long format).
    """
    ensure_dir(out_csv.parent)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_name", "image_path", "width", "height",
            "rank", "hex", "r", "g", "b", "percent"
        ])
        for res in results:
            for i, (hexv, (r, g, b), p) in enumerate(zip(res.colors_hex, res.colors_rgb, res.percents), start=1):
                writer.writerow([
                    res.image_name, res.image_path, res.width, res.height,
                    i, hexv, r, g, b, round(p * 100.0, 4)
                ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Folder containing images")
    ap.add_argument("--output", required=True, help="Output folder")
    ap.add_argument("--k", type=int, default=8, help="Number of dominant colors per image")
    ap.add_argument("--max-pixels", type=int, default=250000, help="Max pixels sampled per image for speed")
    ap.add_argument("--seed", type=int, default=0, help="Random seed for sampling/k-means init")
    args = ap.parse_args()

    in_dir = Path(args.input).expanduser().resolve()
    out_dir = Path(args.output).expanduser().resolve()
    ensure_dir(out_dir)

    palette_dir = out_dir / "palettes"
    ensure_dir(palette_dir)

    image_paths = []
    for p in sorted(in_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            image_paths.append(p)

    if not image_paths:
        raise SystemExit(f"No images found in {in_dir} with extensions: {sorted(SUPPORTED_EXTS)}")

    results: List[ColorResult] = []
    for p in image_paths:
        try:
            res = process_image(p, k=args.k, max_pixels=args.max_pixels, seed=args.seed)
            results.append(res)

            # Save palette image
            pal = make_palette_image(res.colors_rgb, res.percents)
            pal_out = palette_dir / f"{p.stem}_palette.png"
            pal.save(pal_out)

            print(f"Processed: {p.name} -> {pal_out.name}")
        except Exception as e:
            print(f"Failed: {p} ({e})")

    # Save CSV
    out_csv = out_dir / "colors_report.csv"
    write_csv(results, out_csv)
    print(f"\nDone. Wrote: {out_csv}")
    print(f"Palettes in: {palette_dir}")


if __name__ == "__main__":
    main()