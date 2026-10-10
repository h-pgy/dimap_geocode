# Lazy Loading - Leaflet-Geoman Documentation

## Overview

When minimizing initial webpage load times is a priority, you can defer Geoman's JavaScript to load only when needed. However, this approach requires special handling to ensure proper initialization.

## The Problem

If the L.Map object is already initialized before Geoman's JavaScript loads, the library won't automatically attach itself to the existing map instance. This results in the `pm` property remaining undefined on the map object.

## Solution

After the Geoman JavaScript file has loaded, execute this command to establish the connection:

```javascript
L.PM.reInitLayer(map);
```

## Implementation Example

Using ES6 modules, here's a practical approach:

```javascript
import * as L from 'leaflet'

let map = L.Map();
// map created and displayed on webpage...

/* drawing script */
// At this point map.pm is undefined

if (!map.pm) {
  await import(/* webpackChunkName: "leaflet-geoman" */ '@geoman-io/leaflet-geoman-free');
  L.PM.reInitLayer(map)
}

// map.pm is now defined and ready for use
```

This pattern allows you to dynamically load Geoman only when drawing functionality is required, improving initial page performance while maintaining full feature access when needed.
