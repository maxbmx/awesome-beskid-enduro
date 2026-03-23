#!/usr/bin/env python3
"""Scan routes/*.gpx, write routes-manifest.json and embed the same data in index.html."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

GPX_NS = "http://www.topografix.com/GPX/1/1"


def _el(parent: ET.Element, tag: str) -> ET.Element | None:
    return parent.find(f"{{{GPX_NS}}}{tag}")


def collect_track_elevations(path: Path) -> list[float]:
    """All <ele> values from trk/trkseg/trkpt in document order."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError:
        return []
    out: list[float] = []
    for trk in root.findall(f".//{{{GPX_NS}}}trk"):
        for trkseg in trk.findall(f"{{{GPX_NS}}}trkseg"):
            for trkpt in trkseg.findall(f"{{{GPX_NS}}}trkpt"):
                ele = trkpt.find(f"{{{GPX_NS}}}ele")
                if ele is not None and ele.text and ele.text.strip():
                    try:
                        out.append(float(ele.text.strip()))
                    except ValueError:
                        pass
    return out


def smooth_moving_average(values: list[float], window: int = 5) -> list[float]:
    """Simple centered moving average; short tracks are returned unchanged."""
    if len(values) < 3 or window < 3:
        return values
    half = window // 2
    out: list[float] = []
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        chunk = values[lo:hi]
        out.append(sum(chunk) / len(chunk))
    return out


def _smoothed_series(elevations: list[float], smooth_window: int) -> list[float]:
    if len(elevations) < 2:
        return elevations
    return (
        smooth_moving_average(elevations, smooth_window)
        if len(elevations) >= smooth_window
        else elevations
    )


def cumulative_elevation_gain_m(
    elevations: list[float],
    *,
    smooth_window: int = 5,
) -> float | None:
    """
    Total ascent: sum of positive height differences on a lightly smoothed profile.
    Pure downhill segments get ~0 here (expected).
    """
    if len(elevations) < 2:
        return None
    series = _smoothed_series(elevations, smooth_window)
    total = 0.0
    for i in range(1, len(series)):
        diff = series[i] - series[i - 1]
        if diff > 0:
            total += diff
    return round(total, 1)


def cumulative_elevation_loss_m(
    elevations: list[float],
    *,
    smooth_window: int = 5,
) -> float | None:
    """Total descent: sum of drops on the same smoothed profile (useful for DH-only traces)."""
    if len(elevations) < 2:
        return None
    series = _smoothed_series(elevations, smooth_window)
    total = 0.0
    for i in range(1, len(series)):
        diff = series[i] - series[i - 1]
        if diff < 0:
            total += -diff
    return round(total, 1)


def read_gpx_info(path: Path) -> tuple[str | None, str | None]:
    """Return (iso_datetime_or_none, display_name_or_none)."""
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError:
        return None, None

    date = None
    meta = _el(root, "metadata")
    if meta is not None:
        t = _el(meta, "time")
        if t is not None and t.text and t.text.strip():
            date = t.text.strip()
        n = _el(meta, "name")
        if n is not None and n.text and n.text.strip():
            name = n.text.strip()
            return date, name

    trk = _el(root, "trk")
    if trk is not None:
        n = _el(trk, "name")
        if n is not None and n.text and n.text.strip():
            return date, n.text.strip()

    return date, None


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    routes_dir = root / "routes"
    out_path = root / "routes-manifest.json"
    index_path = root / "index.html"

    entries: list[dict] = []
    for gpx in sorted(routes_dir.glob("*.gpx")):
        date, name = read_gpx_info(gpx)
        elevs = collect_track_elevations(gpx)
        eg = cumulative_elevation_gain_m(elevs)
        el = cumulative_elevation_loss_m(elevs)
        row: dict = {
            "file": gpx.name,
            "date": date,
            "name": name,
        }
        if eg is not None:
            row["elevation_gain_m"] = eg
        if el is not None:
            row["elevation_loss_m"] = el
        entries.append(row)

    def sort_key(e: dict) -> tuple:
        d = e.get("date") or ""
        return (d, e["file"])

    entries.sort(key=sort_key, reverse=True)

    payload = json.dumps(entries, ensure_ascii=False, indent=2)
    out_path.write_text(payload + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} routes to {out_path}")

    html = index_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(<script\s+type="application/json"\s+id="routes-data"\s*>)[\s\S]*?(</script>)',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    if not m:
        print(f"WARNING: could not find <script type=\"application/json\" id=\"routes-data\"> in {index_path}")
    else:
        html = pattern.sub(r"\1\n" + payload + r"\n\2", html, count=1)
        index_path.write_text(html, encoding="utf-8")
        print(f"Embedded manifest in {index_path}")


if __name__ == "__main__":
    main()
