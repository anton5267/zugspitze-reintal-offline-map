# Zugspitze Reintal Offline Map

Offline-capable interactive map for the Zugspitze Reintal route with the Partnachalm / Hoher Weg detour, curated POI, water, emergency points, and descent options.

Open the published map from GitHub Pages:

https://anton5267.github.io/zugspitze-reintal-offline-map/

Notes:

- The HTML map is self-contained and works without internet.
- The satellite layer is optional and needs internet.
- `zugspitze_organic_maps_import.kmz` is the main one-file import for Organic Maps; GPX/KML files are included as backups for Mapy.cz, Garmin, or another navigator.
- Closed or technical descent routes are marked as "НЕ планувати" in the map.
- `print.html` is an A4 emergency sheet with QR, SOS, key coordinates, decision points, and official pre-departure links.
- The interactive map includes GPS locate, a pre-departure checklist, and a Sonnalpin decision panel.
- Best iPhone mode: open GitHub Pages in Safari, use Share -> Add to Home Screen, then launch the Home Screen icon. It opens standalone like an app, without the Safari browser frame.
- ZIP/file mode is mainly a backup for GPX, `print.html`, or desktop browsers. iPhone Files may open HTML as a preview where JS/GPS does not work.
- This public repository is a cleaned release package: generated development inputs, OSM caches, and local test artifacts are intentionally not included.

Main files:

- `index.html` - GitHub Pages entry point.
- `zugspitze_reintal_corrected_route.gpx` - main corrected route.
- `zugspitze_descent_options.gpx` - descent options.
- `zugspitze_descent_options.kml` - descent options for KML tools.
- `zugspitze_organic_maps_import.kmz` - one-file Organic Maps import with route, descents, POI, water, huts, SOS, transport, and risks.
- `ORGANIC_MAPS_IMPORT.txt` - short iPhone/Organic Maps import instructions.
- `print.html` - printable emergency sheet.
- `zugspitze_offline_pack.zip` - offline pack with map, print sheet, GPX/KML, and local instructions.
- `manifest.webmanifest` / `service-worker.js` - PWA offline cache for GitHub Pages / iPhone Home Screen.
