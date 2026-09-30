import json
import math
import time

import paho.mqtt.client as mqtt

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS


# ==================================================
# MQTT CONFIG
# ==================================================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC = "ptit/iot/B23DCAT279/sensor"


# ==================================================
# INFLUXDB CONFIG
# ==================================================
INFLUX_URL = "http://127.0.0.1:8086"

# GIỮ NGUYÊN TOKEN HIỆN TẠI CỦA BẠN Ở ĐÂY
INFLUX_TOKEN = "dt-6Vk7wY60P_yn14JPW8-v508zufQbZYpcy9jdOusuYwq8behi4g_Im3uDAAUmrQpfGfYtSmf-ttNVqqI4xLw=="

INFLUX_ORG = "PTIT"
INFLUX_BUCKET = "iot_data"


# ==================================================
# INFLUXDB CLIENT
# ==================================================
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = influx_client.write_api(
    write_options=SYNCHRONOUS
)


# ==================================================
# SEQUENCE / DATA INTEGRITY
# ==================================================
last_sequence = None
last_uptime = None

total_received = 0
total_written = 0
total_duplicates = 0
total_lost = 0
total_resets = 0


# ==================================================
# VALIDATE DATA
# ==================================================
def validate_data(data):

    required_fields = [
        "temperature",
        "humidity",
        "distance_cm",
        "rssi",
        "sequence",
        "uptime_s",
        "timestamp_ms"
    ]

    # Kiểm tra thiếu field
    for field in required_fields:

        if field not in data:

            print(
                f"INVALID DATA: missing '{field}'"
            )

            return False

    try:

        temperature = float(
            data["temperature"]
        )

        humidity = float(
            data["humidity"]
        )

        distance = float(
            data["distance_cm"]
        )

        rssi = int(
            data["rssi"]
        )

        sequence = int(
            data["sequence"]
        )

        uptime = int(
            data["uptime_s"]
        )

        timestamp_ms = int(
            data["timestamp_ms"]
        )

    except (ValueError, TypeError):

        print(
            "INVALID DATA: wrong data type"
        )

        return False


    # ==================================================
    # NAN / INFINITY
    # ==================================================
    if not all([
        math.isfinite(temperature),
        math.isfinite(humidity),
        math.isfinite(distance)
    ]):

        print(
            "INVALID DATA: NaN or Infinity"
        )

        return False


    # ==================================================
    # PHYSICAL RANGE
    # ==================================================
    if not (-40 <= temperature <= 80):

        print(
            "INVALID DATA: temperature out of range"
        )

        return False


    if not (0 <= humidity <= 100):

        print(
            "INVALID DATA: humidity out of range"
        )

        return False


    if not (0 <= distance <= 400):

        print(
            "INVALID DATA: distance out of range"
        )

        return False


    if not (-120 <= rssi <= 0):

        print(
            "INVALID DATA: RSSI out of range"
        )

        return False


    if sequence < 0:

        print(
            "INVALID DATA: sequence out of range"
        )

        return False


    if uptime < 0:

        print(
            "INVALID DATA: uptime out of range"
        )

        return False


    if timestamp_ms <= 0:

        print(
            "INVALID DATA: timestamp invalid"
        )

        return False


    return True


# ==================================================
# CHECK SEQUENCE
# ==================================================
def check_sequence(current_sequence, current_uptime):

    global last_sequence
    global last_uptime

    global total_duplicates
    global total_lost
    global total_resets


    # ==================================================
    # MESSAGE ĐẦU TIÊN
    # ==================================================
    if last_sequence is None:

        last_sequence = current_sequence
        last_uptime = current_uptime

        return "FIRST", 0


    # ==================================================
    # ESP32 RESTART
    # uptime giảm => thiết bị đã restart
    # ==================================================
    if (
        last_uptime is not None
        and current_uptime < last_uptime
    ):

        total_resets += 1

        last_sequence = current_sequence
        last_uptime = current_uptime

        return "DEVICE_RESET", 0


    # ==================================================
    # DUPLICATE
    # ==================================================
    if current_sequence == last_sequence:

        total_duplicates += 1

        return "DUPLICATE", 0


    # ==================================================
    # DATA LOSS
    #
    # Ví dụ:
    # previous = 5
    # current  = 8
    #
    # thiếu 6,7 => lost = 2
    # ==================================================
    if current_sequence > last_sequence + 1:

        lost = (
            current_sequence
            - last_sequence
            - 1
        )

        total_lost += lost

        last_sequence = current_sequence
        last_uptime = current_uptime

        return "DATA_LOSS", lost


    # ==================================================
    # NORMAL
    # ==================================================
    if current_sequence == last_sequence + 1:

        last_sequence = current_sequence
        last_uptime = current_uptime

        return "NORMAL", 0


    # ==================================================
    # SEQUENCE GIẢM NHƯNG UPTIME KHÔNG GIẢM
    # Reset baseline để tránh tính loss sai
    # ==================================================
    total_resets += 1

    last_sequence = current_sequence
    last_uptime = current_uptime

    return "SEQUENCE_RESET", 0


# ==================================================
# MQTT CONNECT CALLBACK
# ==================================================
def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):

    if reason_code == 0:

        print(
            "======================================"
        )

        print(
            "MQTT       : CONNECTED"
        )

        print(
            "Broker     :",
            MQTT_BROKER
        )

        print(
            "Topic      :",
            MQTT_TOPIC
        )

        print(
            "InfluxDB   :",
            INFLUX_URL
        )

        print(
            "Bucket     :",
            INFLUX_BUCKET
        )

        print(
            "======================================"
        )

        client.subscribe(
            MQTT_TOPIC
        )

    else:

        print(
            "MQTT CONNECTION FAILED"
        )

        print(
            "Reason code:",
            reason_code
        )


# ==================================================
# MQTT MESSAGE CALLBACK
# ==================================================
def on_message(
    client,
    userdata,
    msg
):

    global total_received
    global total_written


    # ==================================================
    # THỜI ĐIỂM PYTHON NHẬN MESSAGE
    # ==================================================
    received_timestamp_ms = int(
        time.time() * 1000
    )


    print()

    print(
        "========== MQTT MESSAGE =========="
    )


    try:

        # ==================================================
        # DECODE MQTT PAYLOAD
        # ==================================================
        payload = msg.payload.decode(
            "utf-8"
        )

        print(
            "Topic       :",
            msg.topic
        )

        print(
            "Raw JSON    :",
            payload
        )


        # JSON -> Python dictionary
        data = json.loads(
            payload
        )


        # ==================================================
        # VALIDATE
        # ==================================================
        if not validate_data(data):

            print(
                "Result      : INVALID"
            )

            print(
                "InfluxDB    : SKIPPED"
            )

            print(
                "=================================="
            )

            return


        print(
            "Result      : VALID"
        )


        # ==================================================
        # SEQUENCE CHECK
        # ==================================================
        total_received += 1

        current_sequence = int(
            data["sequence"]
        )

        current_uptime = int(
            data["uptime_s"]
        )


        sequence_status, sequence_gap = (
            check_sequence(
                current_sequence,
                current_uptime
            )
        )


        print(
            "Sequence chk:",
            sequence_status
        )


        # ==================================================
        # DUPLICATE
        # ==================================================
        if sequence_status == "DUPLICATE":

            print(
                "Duplicate   :",
                current_sequence
            )

            print(
                "InfluxDB    : SKIPPED (duplicate)"
            )

            print(
                "Received    :",
                total_received
            )

            print(
                "Written     :",
                total_written
            )

            print(
                "Duplicates  :",
                total_duplicates
            )

            print(
                "Lost total  :",
                total_lost
            )

            print(
                "=================================="
            )

            return


        # ==================================================
        # DATA LOSS
        # ==================================================
        if sequence_status == "DATA_LOSS":

            missing_start = (
                current_sequence
                - sequence_gap
            )

            missing_end = (
                current_sequence
                - 1
            )

            print(
                "WARNING     : DATA LOSS DETECTED"
            )

            print(
                "Lost now    :",
                sequence_gap
            )

            print(
                "Missing seq :",
                f"{missing_start} -> {missing_end}"
            )


        # ==================================================
        # DEVICE RESET
        # ==================================================
        if sequence_status in [
            "DEVICE_RESET",
            "SEQUENCE_RESET"
        ]:

            print(
                "INFO        : Sequence baseline reset"
            )


        # ==================================================
        # LATENCY CALCULATION
        # ==================================================
        sent_timestamp_ms = int(
            data["timestamp_ms"]
        )


        latency_ms = (
            received_timestamp_ms
            - sent_timestamp_ms
        )


        if latency_ms < 0:

            print(
                "WARNING     : Negative latency detected"
            )

            print(
                "Check NTP / system clock synchronization."
            )


        # ==================================================
        # CREATE INFLUXDB POINT
        # ==================================================
        point = (

            Point("sensor_raw")

            .tag(
                "device_id",
                "ESP32-B23DCAT279"
            )

            .field(
                "temperature",
                float(
                    data["temperature"]
                )
            )

            .field(
                "humidity",
                float(
                    data["humidity"]
                )
            )

            .field(
                "distance_cm",
                float(
                    data["distance_cm"]
                )
            )

            .field(
                "rssi",
                int(
                    data["rssi"]
                )
            )

            .field(
                "sequence",
                current_sequence
            )

            .field(
                "uptime_s",
                current_uptime
            )

            .field(
                "timestamp_ms",
                sent_timestamp_ms
            )

            .field(
                "received_timestamp_ms",
                received_timestamp_ms
            )

            .field(
                "latency_ms",
                float(
                    latency_ms
                )
            )

            # ==========================================
            # DATA INTEGRITY FIELDS
            # ==========================================
            .field(
                "sequence_gap",
                int(
                    sequence_gap
                )
            )

            .field(
                "packet_loss_detected",
                bool(
                    sequence_gap > 0
                )
            )

            .field(
                "packet_loss_total",
                int(
                    total_lost
                )
            )
        )


        # ==================================================
        # WRITE TO INFLUXDB
        # ==================================================
        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point
        )

        total_written += 1


        # ==================================================
        # OUTPUT
        # ==================================================
        print(
            "InfluxDB    : WRITE SUCCESS"
        )


        print(
            "Temperature :",
            data["temperature"],
            "°C"
        )


        print(
            "Humidity    :",
            data["humidity"],
            "%"
        )


        print(
            "Distance    :",
            data["distance_cm"],
            "cm"
        )


        print(
            "RSSI        :",
            data["rssi"],
            "dBm"
        )


        print(
            "Sequence    :",
            current_sequence
        )


        print(
            "Sent time   :",
            sent_timestamp_ms,
            "ms"
        )


        print(
            "Receive time:",
            received_timestamp_ms,
            "ms"
        )


        print(
            "Latency     :",
            latency_ms,
            "ms"
        )


        # ==================================================
        # DATA INTEGRITY STATISTICS
        # ==================================================
        print(
            "Sequence gap:",
            sequence_gap
        )

        print(
            "Received    :",
            total_received
        )

        print(
            "Written     :",
            total_written
        )

        print(
            "Duplicates  :",
            total_duplicates
        )

        print(
            "Lost total  :",
            total_lost
        )

        print(
            "Device reset:",
            total_resets
        )


        print(
            "=================================="
        )


    # ==================================================
    # INVALID JSON
    # ==================================================
    except json.JSONDecodeError:

        print(
            "Result      : INVALID JSON"
        )

        print(
            "InfluxDB    : SKIPPED"
        )

        print(
            "=================================="
        )


    # ==================================================
    # OTHER ERRORS
    # ==================================================
    except Exception as e:

        print(
            "ERROR       :",
            e
        )

        print(
            "InfluxDB    : WRITE FAILED"
        )

        print(
            "=================================="
        )


# ==================================================
# MQTT CLIENT
# ==================================================
mqtt_client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="B23DCAT279-InfluxDB-Collector"
)


mqtt_client.on_connect = (
    on_connect
)

mqtt_client.on_message = (
    on_message
)


# ==================================================
# START
# ==================================================
print()

print(
    "======================================"
)

print(
    "      BAI 2 - IoT DATA COLLECTOR"
)

print(
    "======================================"
)

print(
    "Connecting to MQTT Broker..."
)


mqtt_client.connect(
    MQTT_BROKER,
    MQTT_PORT,
    60
)


try:

    mqtt_client.loop_forever()


except KeyboardInterrupt:

    print()

    print(
        "Stopping collector..."
    )


finally:

    mqtt_client.disconnect()

    influx_client.close()

    print(
        "Collector stopped."
    )