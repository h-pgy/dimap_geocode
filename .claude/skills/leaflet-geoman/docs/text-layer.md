# Text Layer Documentation - Leaflet-Geoman

## Overview

The Text Layer feature enables text annotation capabilities in Leaflet maps. This documentation covers drawing, editing, and creating text layers programmatically.

## Text Layer Drawing

Enable text drawing with:

```javascript
map.pm.enableDraw("Text", { 
  textOptions: { 
    text: "Geoman is fantastic! 🚀", 
    textMarkerCentered: true 
  } 
});
```

### Drawing Options

| Option | Default | Purpose |
|--------|---------|---------|
| text | `` | Pre-populate text content |
| focusAfterDraw | `true` | Auto-activate editing immediately after placement |
| removeIfEmpty | `true` | Delete layer if no text is entered |
| className | `` | Custom CSS classes (space-separated) |
| textMarkerCentered | `true` | Center text around marker position |

## Text Layer Editing

### Available Methods

| Method | Returns | Function |
|--------|---------|----------|
| focus() | — | Activate text editing mode |
| blur() | — | Deactivate text editing mode |
| hasFocus() | `Boolean` | Check if editing is active |
| getElement() | `HTMLElement` | Access textarea DOM element |
| setText(`text`) | — | Modify text content or styling |
| getText() | `String` | Retrieve current text |

### Event Listeners

| Event | Parameters | Trigger |
|-------|-----------|---------|
| pm:textchange | `e` | Fires when text is modified |
| pm:textfocus | `e` | Fires when layer gains focus |
| pm:textblur | `e` | Fires when layer loses focus |

### Custom Styling

Apply CSS to text elements using:

```javascript
layer.pm.getElement().style.color = "red";
```

## Manual Text Layer Creation

Create text layers programmatically:

```javascript
L.marker(latlng, {  
  textMarker: true,  
  text: "Your text here"
}).addTo(map);
```

## Global Configuration

Set default text options for all future text layers:

```javascript
map.pm.setGlobalOptions({ 
  textOptions: { 
    textMarkerCentered: true, 
    removeIfEmpty: false 
  } 
});
```
