import json
import threading
import time
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models import Gateway, Sensor, Tag, LiveValue, HistoricalValue, Alert


def process_payload(gateway_id: int, topic: str, payload: str):
    db = SessionLocal()
    try:
        data = json.loads(payload)

        gateway = db.query(Gateway).filter(Gateway.id == gateway_id).first()
        if not gateway:
            return

        gateway.last_seen = datetime.utcnow()

        flat_data = {}

        # Scenario 1: QIOT direct device format
        # Topic: QIOT/.../v3/6/slot_values
        # Payload: [{"slot_idx":6,"tags":[{"idx":0,"val":10}]}]
        if isinstance(data, list):
            base_topic = topic.replace("/slot_values", "").replace("/slot_metadata", "")

            for item in data:
                if "tags" not in item:
                    continue

                for tag_item in item.get("tags", []):
                    idx = tag_item.get("idx")

                    if "val" in tag_item:
                        flat_data[f"{base_topic}:{idx}"] = tag_item.get("val")

                    # Optional: metadata support
                    if "nm" in tag_item:
                        flat_data[f"{base_topic}:{idx}:name"] = tag_item.get("nm")
                    if "um" in tag_item:
                        flat_data[f"{base_topic}:{idx}:unit"] = tag_item.get("um")

        # Scenario 2: Gateway structured tag:value format
        # Payload: {"kwh":123.45,"voltage":240}
        elif isinstance(data, dict):
            flat_data = data

        tags = (
            db.query(Tag)
            .join(Sensor)
            .filter(Sensor.gateway_id == gateway.id)
            .all()
        )

        for tag in tags:
            if tag.key not in flat_data:
                continue

            try:
                val = float(flat_data[tag.key])
            except Exception:
                continue

            live = db.query(LiveValue).filter(LiveValue.tag_id == tag.id).first()
            if not live:
                live = LiveValue(tag_id=tag.id)

            live.value = val
            live.timestamp = datetime.now()
            live.quality = "GOOD"
            db.add(live)

            if getattr(tag, "log_enabled", True):
                db.add(
                    HistoricalValue(
                        tag_id=tag.id,
                        value=val,
                        timestamp=live.timestamp,
                        source="MQTT",
                    )
                )

            if tag.high_limit is not None and val > tag.high_limit:
                exists = db.query(Alert).filter(
                    Alert.tag_id == tag.id,
                    Alert.status == "active"
                ).first()

                if not exists:
                    db.add(Alert(
                        tag_id=tag.id,
                        severity="high",
                        message=f"{tag.display_name} high limit crossed: {val}"
                    ))

            if tag.low_limit is not None and val < tag.low_limit:
                exists = db.query(Alert).filter(
                    Alert.tag_id == tag.id,
                    Alert.status == "active"
                ).first()

                if not exists:
                    db.add(Alert(
                        tag_id=tag.id,
                        severity="low",
                        message=f"{tag.display_name} low limit crossed: {val}"
                    ))

        db.commit()

    except Exception as e:
        db.rollback()
        print("MQTT process error:", e)

    finally:
        db.close()


def run_gateway_worker(gateway_id: int):
    import paho.mqtt.client as mqtt

    db = SessionLocal()
    gateway = db.query(Gateway).filter(Gateway.id == gateway_id).first()

    if not gateway:
        db.close()
        return

    host = gateway.mqtt_host
    port = int(gateway.mqtt_port or 1883)
    username = gateway.mqtt_username or ""
    password = gateway.mqtt_password or ""
    topic = gateway.mqtt_topic or "#"
    code = gateway.code

    db.close()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"iiot_{code}_{gateway_id}")

    if username:
        client.username_pw_set(username, password)

    def on_connect(c, u, flags, rc, props=None):
        print(f"MQTT connected for gateway {code}: {host}:{port}, topic={topic}")
        c.subscribe(topic, qos=1)

    def on_message(c, u, msg):
        try:
            payload = msg.payload.decode()
            print(f"MQTT received [{code}] {msg.topic}: {payload}")
            process_payload(gateway_id, msg.topic, payload)
        except Exception as e:
            print("MQTT message error:", e)

    def on_disconnect(c, u, flags, rc, props=None):
        print(f"MQTT disconnected for gateway {code}. Reconnecting...")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(host, port, keepalive=60)
            client.loop_forever()
        except Exception as e:
            print(f"MQTT connection failed for gateway {code}:", e)
            time.sleep(10)


def start_mqtt_worker():
    db = SessionLocal()
    try:
        gateways = db.query(Gateway).all()
        for gw in gateways:
            threading.Thread(
                target=run_gateway_worker,
                args=(gw.id,),
                daemon=True,
            ).start()
            print(f"Started MQTT worker for gateway: {gw.code}")
    finally:
        db.close()

def start_single_gateway_worker(gateway_id: int):
    threading.Thread(
        target=run_gateway_worker,
        args=(gateway_id,),
        daemon=True
    ).start()