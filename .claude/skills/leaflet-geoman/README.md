# Leaflet-Geoman Reference Skill

Complete reference documentation for **Leaflet-Geoman** — a powerful Leaflet plugin for creating and editing geographic layers on interactive maps.

## Quick Links

| Document | File | Purpose |
|----------|------|---------|
| **Introduction** | [`docs/introduction.md`](docs/introduction.md) | Overview of Leaflet-Geoman and supported geometry types |
| **Toolbar Configuration** | [`docs/toolbar.md`](docs/toolbar.md) | Setup, methods, and comprehensive options for the toolbar UI (positioning, drawing modes, display controls) |
| **Drawing & Editing Modes** | [`docs/modes.md`](docs/modes.md) | All available modes including Draw, Edit, Drag, Cut, Rotate, and more |
| **Text Layers** | [`docs/text-layer.md`](docs/text-layer.md) | Add, edit, and style text annotations on maps; methods for focusing, getText, setText with custom styling |
| **Global Options** | [`docs/options.md`](docs/options.md) | Layer-level and map-level configuration settings like snapping, panes, and keyboard behavior |
| **Layer Groups** | [`docs/layer-groups.md`](docs/layer-groups.md) | Managing multiple layers with `L.FeatureGroup` and `L.GeoJSON`; batch operations on layer groups |
| **Utility Functions** | [`docs/utils.md`](docs/utils.md) | Helper methods for geometry calculations and conversions |
| **Keyboard Shortcuts** | [`docs/keyboard.md`](docs/keyboard.md) | Keyboard event handling, modifier key detection, and options for Escape/Enter key behaviors |
| **Lazy Loading** | [`docs/lazy-loading.md`](docs/lazy-loading.md) | Defer Geoman initialization for improved page load performance using dynamic imports |

---

## How to Use This Skill

1. **Start with Introduction** — Read [`docs/introduction.md`](docs/introduction.md) for an overview of Leaflet-Geoman's capabilities and supported geometries.

2. **Set Up the Toolbar** — Use [`docs/toolbar.md`](docs/toolbar.md) to configure which drawing and editing buttons to show, and where to position them.

3. **Choose Your Modes** — Reference [`docs/modes.md`](docs/modes.md) to understand available drawing, editing, and manipulation modes for your use case.

4. **Configure Options** — Fine-tune behavior with [`docs/options.md`](docs/options.md) (snapping, keyboard shortcuts, layer organization).

5. **Add Layers** — Explore specific layer types:
   - Text annotations: [`docs/text-layer.md`](docs/text-layer.md)
   - Multiple layers: [`docs/layer-groups.md`](docs/layer-groups.md)

6. **Optimize Performance** — Use [`docs/lazy-loading.md`](docs/lazy-loading.md) if you need Geoman to load only when required.

7. **Use Utilities** — Reference [`docs/utils.md`](docs/utils.md) for geometry conversions and calculations.

8. **Handle Keyboard** — Set up keyboard shortcuts with [`docs/keyboard.md`](docs/keyboard.md).

---

## Key Concepts

### Supported Geometry Types
Markers, CircleMarkers, Polylines, Polygons, Circles, Rectangles, ImageOverlays, LayerGroups, GeoJSON, MultiLineStrings, MultiPolygons

### Configuration Pattern
```javascript
// Add toolbar to map
map.pm.addControls({ position: 'topleft', ... });

// Enable a drawing mode
map.pm.enableDraw('Polygon', { snappable: true });

// Set global options
map.pm.setGlobalOptions({ exitModeOnEscape: true });
```

---

## Documentation Metadata

**Source**: https://geoman.io/docs/leaflet/  
**Last Updated**: 2026-09-11  
**Plugin**: Leaflet-Geoman  
**Leaflet Compatibility**: 1.9.x+

---

## Progressive Disclosure

The documentation is organized by user journey:
1. **First time?** → Start with Introduction
2. **Want to add UI controls?** → Toolbar Configuration
3. **Need a specific feature?** → Modes or Utilities
4. **Troubleshooting performance?** → Lazy Loading
5. **Looking for an API method?** → Use the tables in Toolbar, Options, Utils, or Keyboard

Each document stands alone but references related sections for cross-linking.
