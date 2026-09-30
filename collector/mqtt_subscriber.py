import json
import paho.mqtt.client as mqtt

# =================================================
# CẤU HÌNH MQTT
# =================================================
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "ptit/iot/B23DCAT279/sensor"


# =================================================
# KHI KẾT NỐI MQTT THÀNH CÔNG
# =================================================
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("========================================")
        print("       MQTT SUBSCRIBER - BAI 2")
        print("========================================")
        print("MQTT        : CONNECTED")
        print("Broker      :", BROKER)
        print("Port        :", PORT)
        print("Topic       :", TOPIC)

        # Đăng ký nhận dữ liệu từ topic của ESP32
        client.subscribe(TOPIC)

        print("Subscribe   : OK")
        print("Waiting for sensor data...")

    else:
        print("MQTT        : CONNECTION FAILED")
        print("Reason code :", reason_code)


# =================================================
# KHI NHẬN ĐƯỢC MESSAGE TỪ ESP32
# =================================================
def on_message(client, userdata, msg):
    try:
        # Chuyển dữ liệu bytes -> string
        payload = msg.payload.decode("utf-8")

        # Chuyển JSON string -> Python dictionary
        data = json.loads(payload)

        print()
        print("========== MQTT DATA ==========")

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
            data["sequence"]
        )

        print(
            "Uptime      :",
            data["uptime_s"],
            "seconds"
        )

        print("================================")

    # Payload không phải JSON hợp lệ
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON")
        print("Raw payload:", msg.payload)

    # JSON thiếu trường dữ liệu
    except KeyError as e:
        print("ERROR: Missing field:", e)


# =================================================
# TẠO MQTT CLIENT
# =================================================
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="Python-B23DCAT279"
)

# Gán callback
client.on_connect = on_connect
client.on_message = on_message


# =================================================
# KẾT NỐI MQTT BROKER
# =================================================
print("Connecting to MQTT Broker...")

client.connect(
    BROKER,
    PORT,
    60
)

# Chạy liên tục để nhận dữ liệu MQTT
client.loop_forever()