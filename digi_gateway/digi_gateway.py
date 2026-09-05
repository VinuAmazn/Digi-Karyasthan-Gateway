#!/usr/bin/env python3
import json
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


def load_runtime():
    options = json.loads(OPTIONS_FILE.read_text()) if OPTIONS_FILE.exists() else {}
    saved = json.loads(CREDENTIALS_FILE.read_text()) if CREDENTIALS_FILE.exists() else {}
    origin = str(options.get("karyasthan_origin") or os.getenv("DIGI_SMART_ORIGIN", "https://entekaryasthan.com")).rstrip("/")
    gateway_uuid = str(options.get("gateway_uuid") or os.getenv("DIGI_SMART_GATEWAY_UUID", ""))
    api_base = str(saved.get("api_base") or os.getenv("DIGI_SMART_API_BASE", "")).rstrip("/")
    token = str(saved.get("gateway_token") or os.getenv("DIGI_SMART_GATEWAY_TOKEN", ""))
    claim_code = str(options.get("claim_code") or os.getenv("DIGI_SMART_CLAIM_CODE", ""))
    if (not api_base or not token) and gateway_uuid and claim_code:
        response = requests.post(f"{origin}/api/digi-smart/activate", json={"gateway_uuid": gateway_uuid, "claim_code": claim_code, "software_version": "1.1.0"}, timeout=(5, 20))
        response.raise_for_status()
        saved = response.json()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_FILE.write_text(json.dumps(saved), encoding="utf-8")
        os.chmod(CREDENTIALS_FILE, 0o600)
        api_base, token = saved["api_base"].rstrip("/"), saved["gateway_token"]
    if not api_base or not token:
        raise RuntimeError("Enter the gateway ID and one-time activation code")
    supervisor_token = os.getenv("SUPERVISOR_TOKEN", "")
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://supervisor/core" if supervisor_token else "http://homeassistant.local:8123").rstrip("/")
    ha_token = supervisor_token or os.getenv("HOME_ASSISTANT_TOKEN", "")
    if not ha_token:
        raise RuntimeError("Home Assistant access is unavailable")
    return api_base, token, ha_url, ha_token


API_BASE, API_TOKEN, HA_URL, HA_TOKEN = load_runtime()
ENTITY_FILE = Path(os.getenv("DIGI_SMART_ENTITIES", "/etc/digi-karyasthan/entities.json"))
VERIFY_TLS = os.getenv("DIGI_SMART_VERIFY_TLS", "true").lower() == "true"
VERSION = "1.1.0"
STATE_ATTRIBUTES = {"brightness", "temperature", "current_temperature", "hvac_mode", "locked", "contact", "motion", "power", "energy", "unit_of_measurement"}
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
                                timeout=(5, 20), verify=VERIFY_TLS, **kwargs)
    response.raise_for_status()
    return response.json()


def ha(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {HA_TOKEN}"
    headers["Content-Type"] = "application/json"
    response = requests.request(method, f"{HA_URL}/{path.lstrip('/')}", headers=headers,
                                timeout=(3, 15), verify=VERIFY_TLS, **kwargs)
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
    device_type = {"light": "light", "switch": "switch", "fan": "fan", "climate": "thermostat",
                   "cover": "curtain", "sensor": "other", "binary_sensor": "door_sensor"}.get(domain, "other")
    if domain == "binary_sensor" and device_class not in ("door", "garage_door", "opening", "window"):
        device_type = "motion_sensor"
    capabilities = {"light": ["power", "brightness"], "switch": ["power"], "fan": ["power"],
                    "climate": ["power", "temperature"], "cover": [], "sensor": [],
                    "binary_sensor": ["contact" if device_type == "door_sensor" else "motion"]}.get(domain, [])
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
                        "connection_status": "unavailable" if state.get("state") == "unavailable" else "online",
                        "state": value})
    api("POST", "states", json={"devices": payload})


def service_for(entity_id, action, requested):
    domain = entity_id.split(".", 1)[0]
    data = {"entity_id": entity_id}
    if action in ("turn_on", "turn_off"):
        service = action
        if action == "turn_on" and "value" in requested:
            data["brightness_pct"] = max(0, min(100, float(requested["value"])))
    elif action == "set_brightness" and domain == "light":
        service, data["brightness_pct"] = "turn_on", max(0, min(100, float(requested["value"])))
    elif action == "set_temperature" and domain == "climate":
        service, data["temperature"] = "set_temperature", float(requested["value"])
    elif action in ("lock", "unlock") and domain == "lock":
        service = action
    elif action in ("open", "close") and domain == "cover":
        service = f"{action}_cover"
    else:
        raise ValueError(f"Action {action} is not allowed for {domain}")
    return domain, service, data


def process_commands(configured):
    for command in api("GET", "commands").get("data", []):
        command_id = command["command_uuid"]
        entity_id = command["external_device_id"]
        try:
            domain = entity_id.split(".", 1)[0]
            if domain not in CONTROL_DOMAINS:
                raise PermissionError("This device type requires assisted control approval")
            if entity_id in configured and not configured[entity_id].get("allow_control", False):
                raise PermissionError("Entity control is disabled in the local commissioned allowlist")
            domain, service, data = service_for(entity_id, command["action"], command.get("requested_state") or {})
            ha("POST", f"api/services/{domain}/{service}", json=data)
            api("POST", f"commands/{command_id}/ack", json={"status": "completed"})
        except Exception as exc:
            log.exception("Command %s failed", command_id)
            api("POST", f"commands/{command_id}/ack", json={"status": "failed", "reason": str(exc)[:1000]})


def matter_commission(code):
    ws_url = HA_URL.replace("http://", "ws://").replace("https://", "wss://") + "/websocket"
    connection = websocket.create_connection(ws_url, timeout=130)
    try:
        first = json.loads(connection.recv())
        if first.get("type") == "auth_required":
            connection.send(json.dumps({"type": "auth", "access_token": HA_TOKEN}))
            if json.loads(connection.recv()).get("type") != "auth_ok":
                raise PermissionError("Home Assistant rejected gateway access")
        connection.send(json.dumps({"id": 1, "type": "matter/commission", "code": code, "network_only": False}))
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
            before = {item["entity_id"] for item in ha("GET", "api/states")}
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "waiting", "message": "Gateway is pairing the product"})
            if job["protocol"] == "matter":
                matter_commission(str(job.get("setup", {}).get("setup_code", "")))
            elif job["protocol"] == "zigbee":
                ha("POST", "api/services/zha/permit", json={"duration": 120})
            deadline = time.time() + 125
            found = None
            next_pairing_heartbeat = 0
            while running and time.time() < deadline:
                if time.time() >= next_pairing_heartbeat:
                    heartbeat()
                    next_pairing_heartbeat = time.time() + 25
                states = ha("GET", "api/states")
                found = next((item["entity_id"] for item in states if item["entity_id"] not in before and item["entity_id"].split(".", 1)[0] in SAFE_DOMAINS), None)
                if found:
                    break
                time.sleep(5)
            if not found:
                raise TimeoutError("No new product was found. Reset it, move it closer to the gateway and try again.")
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "completed", "message": "Product connected", "result_device_id": found})
        except Exception as exc:
            log.exception("Pairing %s failed", pairing_id)
            api("POST", f"pairings/{pairing_id}/ack", json={"status": "failed", "message": str(exc)[:1000]})


def main():
    next_heartbeat = 0
    while running:
        try:
            auto_discover, configured = entity_config()
            if time.time() >= next_heartbeat:
                heartbeat()
                next_heartbeat = time.time() + 30
            sync_states(auto_discover, configured)
            process_commands(configured)
            process_pairings()
        except Exception:
            log.exception("Gateway cycle failed")
        time.sleep(10)


if __name__ == "__main__":
    main()
