# Zugspitze Reintal Offline Map

Offline-capable interactive map for the Zugspitze Reintal route with the Partnachalm / Hoher Weg detour, curated POI, water, emergency points, and descent options.

Open the published map from GitHub Pages:

https://anton5267.github.io/zugspitze-reintal-offline-map/

Notes:

- The HTML map is self-contained and works without internet.
- The satellite layer is optional and needs internet.
- GPX/KML files are included for import into Organic Maps, Mapy.cz, Garmin, or another navigator.
- Closed or technical descent routes are marked as "НЕ планувати" in the map.

Main files:

- `index.html` - GitHub Pages entry point.
- `zugspitze_reintal_editable_map.html` - same standalone map file.
- `zugspitze_reintal_corrected_route.gpx` - main corrected route.
- `zugspitze_descent_options.gpx` - descent options.
- `zugspitze_descent_options.kml` - descent options for KML tools.
- `build_zugspitze_editable_map.py` - generator.
