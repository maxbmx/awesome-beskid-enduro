# Awesome Beskid Enduro

Statyczna strona z listą tras rowerowych (GPX) w Beskidach: podgląd na mapie (Leaflet + OpenTopoMap), dystans, przewyższenie / zjazd, ulubione w `localStorage`, pobieranie pliku GPX.

## Wymagania

- Do **podglądu lokalnego** potrzebny jest dowolny serwer HTTP (przeglądarka blokuje `fetch` do plików GPX przy `file://`).
- Do **aktualizacji listy tras** po dodaniu lub usunięciu plików w `routes/`: **Python 3**.

## Jak dodać lub zmienić trasę

1. Umieść plik `.gpx` w katalogu [`routes/`](routes/).
2. Wygeneruj manifest i osadź go w `index.html`:

   ```bash
   python3 scripts/generate_routes_manifest.py
   ```

   Skrypt:
   - skanuje `routes/*.gpx`,
   - zapisuje [`routes-manifest.json`](routes-manifest.json),
   - wstawia te same dane do bloku `<script type="application/json" id="routes-data">` w [`index.html`](index.html) (nazwa, data z metadanych, przewyższenie / zjazd z profilu wysokości).

3. Zatwierdź zmiany w repozytorium.

## Podgląd lokalny

```bash
python3 -m http.server 8080
```

Następnie otwórz w przeglądarce: `http://127.0.0.1:8080/`.

## Opcjonalna weryfikacja wysokości

```bash
python3 scripts/verify_elevation_stats.py
```

## Zależności front-endu (lokalnie w repozytorium)

Biblioteki są w katalogu [`vendor/`](vendor/) (bez CDN): Tailwind (runtime w przeglądarce), Leaflet, leaflet-gpx, assety ikon mapy.

## Licencja

Zobacz plik [LICENSE](LICENSE).
