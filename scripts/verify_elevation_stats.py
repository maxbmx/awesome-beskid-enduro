#!/usr/bin/env python3
"""
Sprawdza spójność elevation_gain_m / elevation_loss_m z surowym profilem GPX
oraz reguły UI (znaczący podjazd ≥ 5 m — wtedy w karcie widać podjazd, inaczej zjazd).
Uruchom z katalogu repo: python3 scripts/verify_elevation_stats.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTES = ROOT / "routes"


def load_generator():
    spec = importlib.util.spec_from_file_location("grm", ROOT / "scripts" / "generate_routes_manifest.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = load_generator()
    issues: list[str] = []
    ui_note: list[str] = []
    MEANINGFUL = 5

    for gpx in sorted(ROUTES.glob("*.gpx")):
        e = mod.collect_track_elevations(gpx)
        if len(e) < 2:
            issues.append(f"{gpx.name}: za mało punktów z <ele>")
            continue
        g_sm = mod.cumulative_elevation_gain_m(e)
        l_sm = mod.cumulative_elevation_loss_m(e)
        raw_pos = sum(max(0.0, e[i] - e[i - 1]) for i in range(1, len(e)))
        raw_neg = sum(max(0.0, e[i - 1] - e[i]) for i in range(1, len(e)))

        if g_sm is not None and g_sm > raw_pos + 5:
            issues.append(f"{gpx.name}: gain_smoothed ({g_sm}) > raw sum climbs ({raw_pos:.1f}) + 5")
        if l_sm is not None and l_sm > raw_neg + 5:
            issues.append(f"{gpx.name}: loss_smoothed ({l_sm}) > raw sum descents ({raw_neg:.1f}) + 5")

        # Symulacja reguły z index.html (formatElevationStat)
        if g_sm is not None and l_sm is not None:
            if g_sm >= MEANINGFUL:
                shown = f"↑ {g_sm:g} m (w tooltipie także zjazd jeśli loss>gain)"
            elif l_sm > 0:
                shown = f"↓ {l_sm:g} m"
            elif g_sm > 0:
                shown = f"↑ {g_sm:g} m (mały podjazd)"
            else:
                shown = "0 m"
            if g_sm < MEANINGFUL and l_sm > 50:
                ui_note.append(f"{gpx.name}: UI pokazuje {shown} (gain={g_sm}, loss={l_sm})")

    print("=== Błędy spójności (powinno być 0) ===")
    if not issues:
        print("OK — brak.")
    else:
        for x in issues:
            print(x)
    print()
    print(f"=== Trasy z gain < {MEANINGFUL} m i dużym zjazdem (karta pokazuje ↓ — oczekiwane) ===")
    print(f"liczba: {len(ui_note)}")
    for line in ui_note[:15]:
        print(line)
    if len(ui_note) > 15:
        print(f"... i {len(ui_note) - 15} kolejnych")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
