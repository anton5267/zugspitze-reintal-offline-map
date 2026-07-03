# Zugspitze Reintal Offline Map

Offline-capable interactive map for the Zugspitze Reintal route with the Partnachalm / Hoher Weg detour, curated POI, water, emergency points, and descent options.

Open the published map from GitHub Pages:

https://anton5267.github.io/zugspitze-reintal-offline-map/

Notes:

- The HTML map is self-contained and works without internet.
- The satellite layer is optional and needs internet.
- GPX/KML files are included for import into Organic Maps, Mapy.cz, Garmin, or another navigator.
- Closed or technical descent routes are marked as "НЕ планувати" in the map.
- `print.html` is an A4 emergency sheet with QR, SOS, key coordinates, decision points, and official pre-departure links.
- The interactive map includes GPS locate, a pre-departure checklist, and a Sonnalpin decision panel.
- Best iPhone mode: open GitHub Pages in Safari, use Share -> Add to Home Screen, then cache the web app from the `Офлайн` tab.
- ZIP/file mode is mainly a backup for GPX, `print.html`, or desktop browsers. iPhone Files may open HTML as a preview where JS/GPS does not work.

Main files:

- `index.html` - GitHub Pages entry point.
- `zugspitze_reintal_editable_map.html` - same standalone map file.
- `zugspitze_reintal_corrected_route.gpx` - main corrected route.
- `zugspitze_descent_options.gpx` - descent options.
- `zugspitze_descent_options.kml` - descent options for KML tools.
- `print.html` - printable emergency sheet.
- `zugspitze_offline_pack.zip` - offline pack with map, print sheet, GPX/KML, and local instructions.
- `manifest.webmanifest` / `service-worker.js` - PWA offline cache for GitHub Pages / iPhone Home Screen.
- `build_zugspitze_editable_map.py` - generator.
