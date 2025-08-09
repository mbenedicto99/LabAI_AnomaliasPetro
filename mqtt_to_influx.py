
import os
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "plataforma/anomalia")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "dev-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "lab")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "signals")

client_influx = None
write_api = None

def setup_influx():
    global client_influx, write_api
    client_influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)
    write_api = client_influx.write_api(write_options=SYNCHRONOUS)

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with result code", rc, "-> subscribing", MQTT_TOPIC, flush=True)
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Expected keys: timestamp, f1_obs, f1_pred, score, threshold, alert, damaged
        t = payload.get("timestamp", None)
        # Use current time if not provided
        if t is None:
            ts = datetime.now(timezone.utc)
        else:
            # Interpret as seconds since start; still use current time for wall-clock, but keep value as field as well
            ts = datetime.now(timezone.utc)
        p = (
            Point("anomalias")
            .tag("topic", msg.topic)
            .field("f1_obs", float(payload.get("f1_obs", float("nan"))))
            .field("f1_pred", float(payload.get("f1_pred", float("nan"))))
            .field("score", float(payload.get("score", float("nan"))))
            .field("threshold", float(payload.get("threshold", float("nan"))))
            .field("alert", int(bool(payload.get("alert", False))))
            .field("damaged", int(payload.get("damaged", 0)))
            .field("t_mid", float(t) if t is not None else float("nan"))
            .time(ts)
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
        print("Wrote point:", p.to_line_protocol(), flush=True)
    except Exception as e:
        print("Error handling message:", e, flush=True)

def main():
    setup_influx()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
