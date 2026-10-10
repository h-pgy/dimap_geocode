# Layer Groups - Leaflet-Geoman Documentation

## Overview

Leaflet-Geoman requires `L.FeatureGroup` and `L.GeoJSON` (extended versions of `L.LayerGroup`) to function correctly, as it depends on the `layeradd` and `layerremove` events.

## Available Methods

The following methods are accessible via `layergroup.pm`:

| Method | Returns | Purpose |
|--------|---------|---------|
| `enable(options)` | — | Activates edit mode for all layers in the group |
| `disable()` | — | Deactivates edit mode for all layers |
| `enabled()` | Boolean | Indicates whether at least one layer has editing enabled |
| `toggleEdit(options)` | — | Switches edit state on/off for all layers |
| `getLayers(deep=false, filterGeoman=true, filterGroupsOut=true)` | Array | Retrieves layers with optional deep nesting and filtering capabilities |
| `setOptions(options)` | — | Applies Leaflet-Geoman settings to child layers |
| `getOptions()` | Object | Returns current layer group configuration |
| `dragging()` | — | Checks if any layer within the group is currently being dragged |

## Working with L.LayerGroup

For compatibility with standard `L.LayerGroup`, add event parent functionality by extending its prototype with `layeradd` and `layerremove` event firing capabilities during layer addition and removal operations.
