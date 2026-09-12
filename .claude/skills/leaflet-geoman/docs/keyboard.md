# Keyboard Documentation - Leaflet-Geoman

## Overview

"We implemented a built-in keyboard listener to make one central place where keyboard events can be accessed (without adding a listener yourself)."

## Available Methods

The following methods are accessible via `map.pm.Keyboard`:

| Method | Returns | Purpose |
|--------|---------|---------|
| `getLastKeyEvent(type = 'current')` | Object | Retrieves the most recent event; accepts `keydown` or `keyup` to specify event type |
| `getPressedKey()` | String | Gets the currently pressed key using KeyboardEvent.key standard |
| `isShiftKeyPressed()` | Boolean | Checks Shift key status |
| `isAltKeyPressed()` | Boolean | Checks Alt key status |
| `isCtrlKeyPressed()` | Boolean | Checks Ctrl key status |
| `isMetaKeyPressed()` | Boolean | Checks Meta key status |

## Available Events

Map instances support the following keyboard event:

| Event | Parameters | Details |
|-------|-----------|---------|
| `pm:keyevent` | `e` | "Fired when keydown or keyup on the document is fired" with `eventType` and `focusOn` properties |

## Global Keyboard Options

### Exit Mode with Escape

Enable users to deactivate active modes by pressing Escape:

```javascript
map.pm.setGlobalOptions({ exitModeOnEscape: true });
```

Compatible with all drawing modes and edit, drag, removal, rotate, and cut modes. Defaults to `false`.

### Finish Drawing with Enter

Allow shape completion by pressing Enter once sufficient vertices exist:

```javascript
map.pm.setGlobalOptions({ finishOnEnter: true });
```

- **Line**: Minimum 2 vertices required
- **Polygon**: Minimum 3 vertices required

Defaults to `false`.
