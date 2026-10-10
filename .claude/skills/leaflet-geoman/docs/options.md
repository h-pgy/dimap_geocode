# Leaflet-Geoman Options Documentation

## Overview

The Options section of Leaflet-Geoman documentation covers configuration settings for drawing and editing map layers. Settings can be applied individually to layers or globally across all layers.

## Setting Options

Options can be configured at two levels:

**Per-layer basis:**
```javascript
layer.pm.enable({ snappable: false });
```

**Global configuration:**
```javascript
map.pm.setGlobalOptions({ snappable: false });
```

## Available Options

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| snappingOrder | Array | `['Marker','CircleMarker','Circle','Line','Polygon','Rectangle']` | Prioritizes snapping behavior sequence |
| layerGroup | Object | `map` | Routes created layers to a layergroup instead of directly to map |
| panes | Object | `{ vertexPane: 'markerPane', layerPane: 'overlayPane', markerPane: 'markerPane' }` | Specifies which [Leaflet panes](https://leafletjs.com/reference.html#map-pane) contain layers and helper vertices |
| cutAsCircle | Boolean | `false` | Enables circular cutting shapes |
| exitModeOnEscape | Boolean | `false` | Pressing Escape key deactivates active modes |
| finishOnEnter | Boolean | `false` | Pressing Enter completes Line (2+ vertices) and Polygon (3+ vertices) drawings |

## Events

| Event | Parameters | Description |
|-------|-----------|-------------|
| pm:globaloptionschanged | `e` | Triggered when global options are modified |

---

**Note:** These options supplement the Draw and Edit Mode options documented elsewhere in the guide.
