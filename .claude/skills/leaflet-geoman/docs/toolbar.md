# Toolbar Documentation - Leaflet-Geoman

## Overview

The Leaflet-Geoman toolbar provides a user interface to access drawing and editing features on your map.

![Leaflet-Geoman Toolbar](https://assets.geoman.io//assets/toolbar.png)

## Basic Implementation

```javascript
map.pm.addControls({
  position: 'topleft',
  drawCircleMarker: false,
  rotateMode: false,
});
```

## Core Methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `addControls(options)` | — | Adds toolbar to map with optional configuration |
| `removeControls()` | — | Removes toolbar from map |
| `toggleControls()` | — | Toggles toolbar visibility |
| `controlsVisible()` | Boolean | Checks if toolbar is currently visible |

## Configuration Options

### Positioning

| Option | Default | Description |
|--------|---------|-------------|
| `position` | `'topleft'` | Toolbar location: `'topleft'`, `'topright'`, `'bottomleft'`, or `'bottomright'` |
| `positions` | Object | Customizes individual block positioning (`draw`, `edit`, `custom`, `options`) |

### Drawing Features

- `drawMarker` (default: `true`) — Marker drawing button
- `drawCircleMarker` (default: `true`) — CircleMarker button
- `drawPolyline` (default: `true`) — Line drawing button
- `drawRectangle` (default: `true`) — Rectangle button
- `drawPolygon` (default: `true`) — Polygon button
- `drawCircle` (default: `true`) — Circle button
- `drawText` (default: `true`) — Text layer button

### Editing & Manipulation Modes

- `editMode` (default: `true`) — Edit mode toggle
- `dragMode` (default: `true`) — Drag mode toggle
- `cutPolygon` (default: `true`) — Polygon hole cutting
- `removalMode` (default: `true`) — Layer removal
- `rotateMode` (default: `true`) — Layer rotation

### Display Controls

| Option | Default | Purpose |
|--------|---------|---------|
| `oneBlock` | `false` | Consolidate all buttons into single block |
| `drawControls` | `true` | Show draw button group |
| `editControls` | `true` | Show edit button group |
| `customControls` | `true` | Show custom button group |
| `snappingOption` | `true` | Snapping toggle button |

## Passing Options to Features

Apply options globally or for specific drawing modes:

```javascript
// Mode-specific options
map.pm.enableDraw('Polygon', { snappable: false });
map.pm.disableDraw();

// Global options (persist across mode toggles)
map.pm.setGlobalOptions({ snappable: false });
```

## Additional Resources

- **Customization**: Visit the [customization page](/docs/leaflet/customize/toolbar) for styling and UI modifications
- **Related**: See [Modes](/docs/leaflet/category/modes) documentation for detailed feature descriptions
