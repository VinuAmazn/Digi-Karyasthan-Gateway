# Changelog

## 1.2.0

- Correct Home Assistant direct and Supervisor WebSocket endpoints.
- Recognize actual dimmer, sensor and Celsius thermostat capabilities.
- Expire jobs before execution and confirm observed state before acknowledging success.
- Preserve unknown/offline readings and reconcile empty or partial snapshots.
- Match pairing discovery to the requested device type and document Matter mobile commissioning.
- Keep credentials private, require cloud HTTPS, and prevent bearer-token redirects.

## 1.1.0

- One-time portal activation with per-gateway credentials.
- Portal-driven Matter, Zigbee, and local Wi-Fi discovery jobs.
- Automatic Home Assistant Supervisor API access.
- Gateway heartbeat during long pairing windows.
