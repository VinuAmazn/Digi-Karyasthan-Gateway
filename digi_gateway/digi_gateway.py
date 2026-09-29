#!/usr/bin/env python3
import json
import math
from datetime import datetime, timezone
from urllib.parse import urlparse
import logging
import os
import signal
import time
from pathlib import Path

import requests
import websocket

DATA_DIR = Path(os.getenv("DIGI_SMART_DATA_DIR", "/data" if Path("/data/options.json").exists() else "/etc/digi-karyasthan"))
OPTIONS_FILE = DATA_DIR / "options.json"
CREDENTIALS_FILE = DATA_DIR / "credentials.json"


def private_json(destination, value):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(value, stream)
    os.chmod(temporary, 0o600)
    os.replace(temporary, destination)

def not_expired(value):
    try:
        deadline = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return deadline.tzinfo is not None and deadline > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False

def websocket_url(base):
    endpoint = base.rstrip("/")
    suffix = "/websocket" if urlparse(endpoint).hostname == "supervisor" and urlparse(endpoint).path == "/core" else "/api/websocket"
    return endpoint.replace("http://", "ws://", 1).replace("https://", "wss://", 1) + suffix


def load_runtime():
    options = json.loads(OPTIONS_FILE.read_text()) if OPTIONS_FILE.exists() else {}
    saved = json.loads(CREDENTIALS_FILE.read_text()) if CREDENTIALS_FILE.exists() else {}
    origin = str(options.get("karyasthan_origin") or os.getenv("DIGI_SMART_ORIGIN", "https://entekaryasthan.com")).rstrip("/")
    gateway_uuid = str(options.get("gateway_uuid") or os.getenv("DIGI_SMART_GATEWAY_UUID", ""))
    api_base = str(saved.get("api_base") or os.getenv("DIGI_SMART_API_BASE", "")).rstrip("/")
    token = str(saved.get("gateway_token") or os.getenv("DIGI_SMART_GATEWAY_TOKEN", ""))
    claim_code = str(options.get("claim_code") or os.getenv("DIGI_SMART_CLAIM_CODE", ""))
    if urlparse(origin).scheme != "https" or urlparse(origin).username or urlparse(origin).password:
        raise RuntimeError("Karyasthan origin must be an HTTPS address without credentials")
    if (not api_base or not token) and gateway_uuid and claim_code:
        response = requests.post(f"{origin}/api/digi-smart/activate", json={"gateway_uuid": gateway_uuid, "claim_code": claim_code, "software_version": "1.2.0"}, timeout=(5, 20), allow_redirects=False)
        response.raise_for_status()
        saved = response.json()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        private_json(CREDENTIALS_FILE, saved)
        api_base, token = saved["api_base"].rstrip("/"), saved["gateway_token"]
    if api_base and (urlparse(api_base).scheme != "https" or urlparse(api_base).netloc != urlparse(origin).netloc):
        raise RuntimeError("Gateway API must use HTTPS on the configured Karyasthan host")
    if saved.get("gateway_uuid") and gateway_uuid and saved["gateway_uuid"] != gateway_uuid:
        raise RuntimeError("Saved gateway differs from the configured gateway. Recommission this app before continuing.")
    if not api_base or not token:
        raise RuntimeError("Enter the gateway ID and one-time activation code")
    supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://supervisor/core" if supervisor_token else "http://homeassistant.local:8123").rstrip("/")
    ha_token = supervisor_token or os.getenv("HOME_ASSISTANT_TOKEN", "")
    if not ha_token:
        raise RuntimeError("Home Assistant access is unavailable")
    if ha_url.startswith("http://") and urlparse(ha_url).hostname not in {"supervisor", "homeassistant", "homeassistant.local"}:
        raise RuntimeError("Use HTTPS for Home Assistant outside the local app network")
    return api_base, token, ha_url, ha_token


API_BASE = API_TOKEN = HA_URL = HA_TOKEN = ""
ENTITY_FILE = Path(os.getenv("DIGI_SMART_ENTITIES", "/etc/digi-karyasthan/entities.json"))
VERIFY_TLS = os.getenv("DIGI_SMART_VERIFY_TLS", "true").lower() == "true"
VERSION = "1.2.0"
STATE_ATTRIBUTES = {"brightness", "temperature", "current_temperature", "hvac_mode", "min_temp", "max_temp", "supported_features", "supported_color_modes", "device_class", "locked", "contact", "motion", "power", "energy", "unit_of_measurement"}
SAFE_DOMAINS = {"light", "switch", "fan", "climate", "cover", "sensor", "binary_sensor"}
CONTROL_DOMAINS = {"light", "switch", "fan", "climate", "cover"}
running = True

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("digi-gateway")


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)


def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {API_TOKEN}"
    response = requests.request(method, f"{API_BASE}/{path.lstrip('/')}", headers=headers,
                                timeout=(5, 20), verify=True, allow_redirects=False, **kwargs)
    response.raise_for_status()
    return response.json()


def ha(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {HA_TOKEN}"
    headers["Content-Type"] = "application/json"
    response = requests.request(method, f"{HA_URL}/{path.lstrip('/')}", headers=headers,
                                timeout=(3, 15), verify=True, allow_redirects=False, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def entity_config():
    data = json.loads(ENTITY_FILE.read_text(encoding="utf-8"))
    result = data.get("entities", [])
    if not isinstance(result, list) or len(result) > 100:
        raise ValueError("entities.json must contain at most 100 entities")
    return data.get("auto_discover", True), {item["entity_id"]: item for item in result if item.get("enabled", True)}


def describe(entity_id, state):
    domain = entity_id.split(".", 1)[0]
    attrs = state.get("attributes", {})
    device_class = attrs.get("device_class")
    device_type = {"light": "light", "switch": "switch", "fan": "fan", "climate": "thermostat", "cover": "curtain"}.get(domain, "other")
    capabilities = []
    if domain == "binary_sensor":
        if device_class in ("door", "opening", "window"):
            device_type, capabilities = "door_sensor", ["contact"]
        elif device_class in ("motion", "occupancy", "presence"):
            device_type, capabilities = "motion_sensor", ["motion"]
    elif domain == "sensor" and device_class in ("energy", "power"):
        device_type, capabilities = "energy_meter", ["energy"]
    elif domain in ("light", "switch", "fan"):
        capabilities = ["power"]
        modes = set(attrs.get("supported_color_modes") or [])
        if domain == "light" and modes - {"onoff", "unknown"}:
            capabilities.append("brightness")
    elif domain == "climate":
        capabilities = ["temperature"] if int(attrs.get("supported_features", 0)) & 1 and attrs.get("unit_of_measurement") == "°C" else []
    elif domain == "cover" and device_class in ("garage", "gate", "door"):
        device_type = "other"
    return {"name": str(attrs.get("friendly_name") or entity_id.split(".", 1)[-1].replace("_", " ")).title()[:160],
            "device_type": device_type, "capabilities": capabilities}


def heartbeat():
    api("POST", "heartbeat", json={"status": "online", "software_version": VERSION,
                                    "metadata": {"platform": os.uname().sysname}})


def sync_states(auto_discover, configured):
    states = {item["entity_id"]: item for item in ha("GET", "api/states")}
    allowed = dict(configured)
    if auto_discover:
        allowed.update({entity_id: {"allow_control": False} for entity_id in states
                        if entity_id.split(".", 1)[0] in SAFE_DOMAINS and entity_id not in allowed})
    payload = []
    for entity_id in allowed:
        state = states.get(entity_id)
        if not state:
            payload.append({"external_device_id": entity_id, "connection_status": "unavailable", "state": {}})
            continue
        attributes = {key: value for key, value in state.get("attributes", {}).items() if key in STATE_ATTRIBUTES}
        value = {"state": state.get("state"), "attributes": attributes}
        payload.append({"external_device_id": entity_id, **describe(entity_id, state),
                        "connection_status": "unavailable" if state.get("state") in ("unknown", "unavailable", None) else "online",
                        "state": value})
    if len(payload) > 100:
        log.warning("More than 100 entities: configure an explicit commissioned selection")
    api("POST", "states", json={"devices": payload[:100], "full_snapshot": len(payload) <= 100})


def service_for(entity_id, action, requested):
    domain = entity_id.split(".", 1)[0]
    data = {"entity_id": entity_id}
    if action in ("turn_on", "turn_off") and domain in ("light", "switch", "fan", "climate"):
        service = action
    elif action in ("set_brightness", "set_temperature"):
        value = float(requested.get("value", float("nan")))
        low, high = (0, 100) if action == "set_brightness" else (16, 32)
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError("Requested setting is outside the supported range")
        if action == "set_brightness" and domain == "light":
            service, data["brightness_pct"] = "turn_on", value
        elif action == "set_temperature" and domain == "climate":
            service, data["temperature"] = "set_temperature", value
        else:
            raise ValueError("Setting is incompatible with this entity")
    elif action in ("open", "close") and domain == "cover":
        service = f"{action}_cover"
    else:
        raise ValueError(f"Action {action} is not allowed for {domain}")
    return domain, service, data

def confirmed(state, action, requested):
    value = state.get("state")
    attrs = state.get("attributes", {})
    if action in ("turn_on", "turn_off"):
        return value == ("on" if action == "turn_on" else "off")
    if action == "set_brightness":
        expected = float(requested["value"])
        return value == "off" if expected == 0 else value == "on" and abs(float(attrs.get("brightness", -1000)) / 255 * 100 - expected) <= 2
    if action == "set_temperature":
        return abs(float(attrs.get("temperature", -1000)) - float(requested["value"])) <= 0.5
    return value in (("open", "opening") if action == "open" else ("closed", "closing"))

def process_commands(configured):
    for command in api("GET", "commands").get("data", []):
        command_id = command["command_uuid"]
        entity_id = command["external_device_id"]
        try:
            if not not_expired(command.get("expires_at")):
                raise TimeoutError("Command expired before execution")
            if entity_id in configured and not configured[entity_id].get("allow_control", False):
                raise PermissionError("Entity control is disabled in the local commissioned allowlist")
            before = ha("GET", f"api/states/{entity_id}")
            if before.get("state") in ("unknown", "unavailable", None):
                raise PermissionError("Device has no available state")
            profile = describe(entity_id, before)
            if profile["device_type"] not in ("light", "switch", "plug", "fan", "thermostat", "curtain"):
                raise PermissionError("This device requires assisted verification")
            if command["action"] == "set_brightness" and "brightness" not in profile["capabilities"]:
                raise PermissionError("This light cannot be dimmed")
            if command["action"] == "set_temperature":
                requested = float(command.get("requested_state", {}).get("value", float("nan")))
                attrs = before.get("attributes", {})
                if "temperature" not in profile["capabilities"] or not float(attrs.get("min_temp", 16)) <= requested <= float(attrs.get("max_temp", 32)):
                    raise PermissionError("This thermostat cannot accept the requested temperature")
            domain, service, data = service_for(entity_id, command["action"], command.get("requested_state") or {})
            if not not_expired(command.get("expires_at")):
                raise TimeoutError("Command expired during device verification")
            ha("POST", f"api/services/{domain}/{service}", json=data)
            observed = ha("GET", f"api/states/{entity_id}")
            if not confirmed(observed, command["action"], command.get("requested_state") or {}):
                raise RuntimeError("Service accepted, but the device state is not yet confirmed. Check the property before retrying.")
            acknowledgement = {"status": "completed", "provider_response": {"observed_state": observed.get("state")}}
        except Exception as exc:
            log.warning("Command %s was not confirmed: %s", command_id, type(exc).__name__)
            acknowledgement = {"status": "failed", "reason": str(exc)[:300]}
        # Keep ACK transport errors outside the execution block: never retry a physical action.
        api("POST", f"commands/{command_id}/ack", json=acknowledgement)


def matter_commission(code):
    ws_url = websocket_url(HA_URL)
    connection = websocket.create_connection(ws_url, timeout=130)
    try:
        first = json.loads(connection.recv())
        if first.get("type") == "auth_required":
            connection.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
            if json.loads(connection.recv()).get("type") != "auth_ok":
                raise PermissionError("Home Assistant rejected gateway access")
        connection.send(json.dumps({"id": 1, "type": "matter/commission", "code": code, "network_only": True}))
        while True:
            result = json.loads(connection.recv())
            if result.get("id") == 1:
                if not result.get("success"):
                    raise RuntimeError(str(result.get("error", {}).get("message", "Matter commissioning failed")))
                return
    finally:
        connection.close()


def process_pairings():
    for job in api("GET", "pairings").get("data", []):
        pairing_id = job["pairing_uuid"]
        try:
            if not not_expired(job.get("expires_at")):
                raise TimeoutError("Pairing job expired")
            before = {item["entity_id"] for item in ha("GET", "api/states")}
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "waiting", "message": "Gateway is pairing the product"})
            if job["protocol"] == "matter":
                matter_commission(str(job.get("setup", {}).get("setup_code", "")))
            elif job["protocol"] == "zigbee":
                ha("POST", "api/services/zha/permit", json={"duration": 120})
            if job["protocol"] == "wifi":
                api("POST", f"pairings/{pairing_id}/ack", json={"status": "completed", "message": "Local integrations synchronized. Refresh devices; add the brand integration in Home Assistant if your product is missing."})
                continue
            deadline = time.time() + 125
            found = None
            next_pairing_heartbeat = 0
            while running and time.time() < deadline:
                if time.time() >= next_pairing_heartbeat:
                    heartbeat()
                    next_pairing_heartbeat = time.time() + 25
                states = ha("GET", "api/states")
                found = next((item["entity_id"] for item in states if item["entity_id"] not in before
                              and item["entity_id"].split(".", 1)[0] in SAFE_DOMAINS
                              and (job.get("device_type") == "other" or describe(item["entity_id"], item)["device_type"] == job.get("device_type")
                                   or (job.get("device_type"), describe(item["entity_id"], item)["device_type"]) in (("plug", "switch"), ("air_conditioner", "thermostat")))), None)
                if found:
                    break
                time.sleep(5)
            if not found:
                raise TimeoutError("No new product was found. Reset it, move it closer to the gateway and try again.")
            auto_discover, configured = entity_config()
            sync_states(auto_discover, configured)
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "completed", "message": "Product connected. Refresh devices to view it.", "result_device_id": found})
        except Exception as exc:
            log.exception("Pairing %s failed", pairing_id)
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "failed", "message": str(exc)[:1000]})


def main():
    global API_BASE, API_TOKEN, HA_URL, HA_TOKEN
    API_BASE, API_TOKEN, HA_URL, HA_TOKEN = load_runtime()
    next_heartbeat = 0
    while running:
        try:
            auto_discover, configured = entity_config()
            if time.time() >= next_heartbeat:
                heartbeat()
                next_heartbeat = time.time() + 30
            sync_states(auto_discover, configured)
            process_commands(configured)
            sync_states(auto_discover, configured)
            process_pairings()
        except Exception:
            log.exception("Gateway cycle failed")
        time.sleep(10)


if __name__ == "__main__":
    main()
