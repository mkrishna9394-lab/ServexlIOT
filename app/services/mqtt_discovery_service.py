import json
import time
import socket
import os
from typing import Dict, Any, List

import paho.mqtt.client as mqtt


def discover_mqtt_tags(
    host: str,
    port: int,
    username: str,
    password: str,
    topic: str,
    duration: int = 10,
) -> Dict[str, Any]:

    discovered = {}

    client_id = f"iiot_discovery_{socket.gethostname()}_{os.getpid()}_{int(time.time())}"

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[DISCOVERY CONNECTED] {host}:{port}")
            client.subscribe(topic)
        else:
            print(f"[DISCOVERY ERROR] Connection failed: {rc}")

    def on_message(client, userdata, msg):
        try:
            mqtt_topic = msg.topic
            payload = msg.payload.decode()

            if not mqtt_topic.endswith("/slot_metadata"):
                return

            base_topic = mqtt_topic.replace("/slot_metadata", "")

            data = json.loads(payload)

            if not isinstance(data, list):
                return

            for item in data:
                slot_idx = item.get("slot_idx")
                slot_name = item.get("name", f"Slot {slot_idx}")

                if base_topic not in discovered:
                    discovered[base_topic] = {
                        "base_topic": base_topic,
                        "slot_idx": slot_idx,
                        "slot_name": slot_name,
                        "tags": [],
                    }

                for tag in item.get("tags", []):
                    idx = tag.get("idx")
                    name = tag.get("nm", f"TAG_{idx}")
                    unit = tag.get("um", "")

                    key = f"{base_topic}:{idx}"

                    exists = any(t["key"] == key for t in discovered[base_topic]["tags"])

                    if not exists:
                        discovered[base_topic]["tags"].append({
                            "idx": idx,
                            "name": name,
                            "unit": unit,
                            "key": key,
                        })

        except Exception as e:
            print("[DISCOVERY MESSAGE ERROR]", e)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id
    )

    if username:
        client.username_pw_set(username, password)

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(host, int(port), keepalive=60)
        client.loop_start()
        time.sleep(int(duration))
        client.loop_stop()
        client.disconnect()

    except Exception as e:
        print("[DISCOVERY CONNECTION ERROR]", e)
        raise e

    return discovered