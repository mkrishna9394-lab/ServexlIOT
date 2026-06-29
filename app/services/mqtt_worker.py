import json
import threading
import time
from datetime import datetime

from app.core.database import SessionLocal
from app.models import (
    Gateway,
    Sensor,
    Tag,
    ConfiguredMeter,
    ConfiguredTag,
    LiveValue,
    HistoricalValue,
    Alert,
)


def process_payload(gateway_id: int, topic: str, payload: str):
    db = SessionLocal()

    try:
        data = json.loads(payload)

        gateway = db.query(Gateway).filter(Gateway.id == gateway_id).first()
        if not gateway:
            return

        gateway.last_seen = datetime.now()

        flat_data = {}
        current_sensor_id = None

        # Scenario 1: QIOT slot_values format
        if isinstance(data, list):
            base_topic = (
                topic
                .replace("/slot_values", "")
                .replace("/slot_metadata", "")
            )

            for item in data:
                for tag_item in item.get("tags", []):
                    idx = tag_item.get("idx")
                    if "val" in tag_item:
                        flat_data[f"{base_topic}:{idx}"] = tag_item.get("val")

        elif isinstance(data, dict):

            # Scenario 2: PARSHVI/IOLM_55/port/2/pdi format
            if isinstance(data.get("P_ProcessData"), dict):
                process_data = data["P_ProcessData"]

                topic_parts = topic.split("/")
                port_no = str(data.get("port", ""))

                if "port" in topic_parts:
                    port_index = topic_parts.index("port")
                    port_no = topic_parts[port_index + 1]

                device_name = topic_parts[1] if len(topic_parts) > 1 else gateway.code

                meter_code = f"{gateway.code}_{device_name}_PORT_{port_no}"
                meter_name = f"{gateway.code} {device_name} Port {port_no}"

                meter = db.query(Sensor).filter(
                    Sensor.gateway_id == gateway.id,
                    Sensor.code == meter_code
                ).first()

                if not meter:
                    meter = Sensor(
                        gateway_id=gateway.id,
                        code=meter_code,
                        name=meter_name,
                        sensor_type="MQTT_METER",
                        is_active=True,
                        is_configured=False,
                    )
                    db.add(meter)
                    db.flush()

                    print(f"[DISCOVERED METER] {meter_name}")

                for key, value in process_data.items():
                    tag = db.query(Tag).filter(
                        Tag.sensor_id == meter.id,
                        Tag.key == key
                    ).first()

                    if not tag:
                        db.add(Tag(
                            sensor_id=meter.id,
                            key=key,
                            display_name=key,
                            unit="",
                            low_limit=None,
                            high_limit=None,
                            log_enabled=False,
                        ))
                        print(f"[DISCOVERED TAG] {key}")

                    flat_data[key] = value
                db.commit()
                
                current_sensor_id = meter.id

            # Scenario 3: normal JSON key:value
            else:
                flat_data = data

        configured_tags_query = (
            db.query(ConfiguredTag)
            .join(ConfiguredMeter, ConfiguredTag.configured_meter_id == ConfiguredMeter.id)
            .filter(
                ConfiguredMeter.gateway_id == gateway.id,
                ConfiguredTag.is_active == True,
                ConfiguredMeter.is_active == True,
            )
        )

        if current_sensor_id:
            configured_tags_query = configured_tags_query.filter(
                ConfiguredMeter.sensor_id == current_sensor_id
            )

        configured_tags = configured_tags_query.all()

        for configured_tag in configured_tags:
            if configured_tag.key not in flat_data:
                continue

            raw_val = flat_data[configured_tag.key]

            val = None
            value_text = None

            if configured_tag.tag_type == "String Tag":
                value_text = str(raw_val)

            elif configured_tag.tag_type == "Digital Tag":

                if isinstance(raw_val, bool):
                    val = 1 if raw_val else 0
                    value_text = "ON" if raw_val else "OFF"

                else:
                    try:
                        val = float(raw_val)
                        value_text = str(raw_val)
                    except Exception:
                        value_text = str(raw_val)

            else:

                try:
                    val = float(raw_val)
                except Exception:
                    value_text = str(raw_val)

            live = db.query(LiveValue).filter(
                LiveValue.configured_tag_id == configured_tag.id
            ).first()

            if not live:
                live = LiveValue(configured_tag_id=configured_tag.id)

            live.value = val
            live.value_text = value_text
            live.timestamp = datetime.now()
            live.quality = "GOOD"
            db.add(live)

            db.add(
                HistoricalValue(
                    configured_tag_id=configured_tag.id,
                    value=val,
                    value_text=value_text,
                    timestamp=live.timestamp,
                    source="MQTT",
                )
            )

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

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"iiot_{code}_{gateway_id}"
    )

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
        daemon=True,
    ).start()