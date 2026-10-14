#!/usr/bin/env python3
"""Deploy updated IOPGPS custom component to Home Assistant via File Editor ingress."""
import asyncio
import os
from pathlib import Path
import aiohttp

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "custom_components" / "iopgps"
ENV_FILE = Path("/home/pruet/Development/homeassistance/.env")


def get_ha_config():
    token = ""
    url = "http://100.81.34.78:8123"
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("HASS_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip("'\"")
                elif line.startswith("HASS_URL="):
                    url = line.split("=", 1)[1].strip().strip("'\"")
    return url, token


async def main():
    ha_url, token = get_ha_config()
    print(f"Target Home Assistant: {ha_url}")

    connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
    async with aiohttp.ClientSession(connector=connector) as session:
        ws_url = ha_url.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
        print(f"Connecting to WebSocket {ws_url}...")
        async with session.ws_connect(ws_url) as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": token})
            auth_res = await ws.receive_json()
            if auth_res.get("type") != "auth_ok":
                raise RuntimeError(f"Auth failed: {auth_res}")
            print("Authenticated with Home Assistant WebSocket API.")

            # Get ingress entry for file editor
            await ws.send_json({
                "id": 1,
                "type": "supervisor/api",
                "endpoint": "/addons/core_configurator/info",
                "method": "get"
            })
            info_res = await ws.receive_json()
            ingress_url_path = info_res["result"]["ingress_url"]

            # Create ingress session
            await ws.send_json({
                "id": 2,
                "type": "supervisor/api",
                "endpoint": "/ingress/session",
                "method": "post"
            })
            sess_res = await ws.receive_json()
            ingress_session = sess_res["result"]["session"]
            print(f"Obtained ingress session: {ingress_session[:16]}...")

            base_ingress_url = ha_url.rstrip("/") + ingress_url_path
            cookies = {"ingress_session": ingress_session}

            # Create brand directory on HA
            async with session.post(
                f"{base_ingress_url}api/newfolder",
                data={"name": "brand", "path": "custom_components/iopgps"},
                cookies=cookies
            ) as resp:
                print("  [FOLDER] custom_components/iopgps/brand ->", resp.status)

            # Deploy files
            print("\nDeploying files to custom_components/iopgps...")
            for path in sorted(SRC_DIR.rglob("*")):
                if path.is_dir():
                    continue
                rel_path = path.relative_to(SRC_DIR)
                if any(part in ("__pycache__", "tests") for part in rel_path.parts):
                    continue
                if path.suffix in (".pyc", ".pyo"):
                    continue

                target_filename = f"custom_components/iopgps/{rel_path}"
                if path.suffix == ".png":
                    # Upload binary file
                    data = aiohttp.FormData()
                    data.add_field("file", open(path, "rb"), filename=path.name, content_type="image/png")
                    parent_dir = f"custom_components/iopgps/{rel_path.parent}".rstrip("/")
                    data.add_field("path", parent_dir)
                    async with session.post(f"{base_ingress_url}api/upload", data=data, cookies=cookies) as resp:
                        res = await resp.text()
                        print(f"  [UPLOAD] {target_filename} -> {resp.status}")
                else:
                    # Save text file
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    payload = {
                        "filename": target_filename,
                        "text": content
                    }
                    async with session.post(f"{base_ingress_url}api/save", data=payload, cookies=cookies) as resp:
                        res = await resp.json(content_type=None)
                        if res.get("error"):
                            print(f"  [ERROR] {target_filename}: {res}")
                        else:
                            print(f"  [SAVE] {target_filename} -> OK")

            # Reload IOPGPS Config Entry
            print("\nReloading IOPGPS Integration in Home Assistant...")
            # Find entry id
            await ws.send_json({"id": 3, "type": "config_entries/get", "domain": "iopgps"})
            entries_res = await ws.receive_json()
            entry_id = entries_res["result"][0]["entry_id"]

            await ws.send_json({
                "id": 4,
                "type": "call_service",
                "domain": "homeassistant",
                "service": "reload_config_entry",
                "service_data": {"entry_id": entry_id}
            })
            reload_res = await ws.receive_json()
            print("Reload result:", reload_res)


if __name__ == "__main__":
    asyncio.run(main())
