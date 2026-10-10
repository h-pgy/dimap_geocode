# Leaflet-Geoman Utils Documentation

## Overview

The `L.PM.Utils` object provides utility methods for working with Leaflet-Geoman. These functions assist with geographic calculations, layer management, and translations.

## Available Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `calcMiddleLatLng(map, latlng1, latlng2)` | LatLng | "Returns the middle LatLng between two LatLngs" |
| `getTranslation(path)` | String | Retrieves translated text using dot-notation paths (e.g., `tooltips.placeMarker`) |
| `findLayers(map)` | Array | "Returns all layers that are available for Leaflet-Geoman" |
| `circleToPolygon(circle, sides = 60, withBearing = true)` | Polygon | Converts circular shapes to polygons with configurable sides; requires `withBearing = false` for CRS.Simple maps |
| `pxRadiusToMeterRadius(radiusInPx, map, center)` | Number | Converts pixel-based radius measurements to meter-based radius, accounting for map projection variations |
| `moveLayerTo(layer, centerLatLng)` | — | Repositions a layer's center to specified coordinates |
| `moveLayerBy(layer, deltaLatLng)` | — | Shifts a layer's center by a specified distance offset |
| `copyLayer(layer)` | — | Duplicates a layer while preserving its configuration settings |

## Notes

The documentation indicates these utilities support common geospatial operations needed when implementing drawing and editing functionality in Leaflet applications.
