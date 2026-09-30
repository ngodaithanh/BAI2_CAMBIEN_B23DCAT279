from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ==========================================
# INFLUXDB CONFIG
# ==========================================
URL = "http://127.0.0.1:8086"
TOKEN = "dt-6Vk7wY60P_yn14JPW8-v508zufQbZYpcy9jdOusuYwq8behi4g_Im3uDAAUmrQpfGfYtSmf-ttNVqqI4xLw=="
ORG = "PTIT"
BUCKET = "iot_data"

# ==========================================
# KẾT NỐI INFLUXDB
# ==========================================
client = InfluxDBClient(
    url=URL,
    token=TOKEN,
    org=ORG
)

write_api = client.write_api(
    write_options=SYNCHRONOUS
)

# ==========================================
# TẠO 1 RECORD TEST
# ==========================================
point = (
    Point("sensor_raw")
    .tag("device_id", "ESP32-B23DCAT279")
    .field("temperature", 25.0)
    .field("humidity", 50.0)
    .field("distance_cm", 100.82)
    .field("rssi", -70)
    .field("sequence", 1)
    .field("uptime_s", 5)
)

# ==========================================
# GHI VÀO INFLUXDB
# ==========================================
try:
    write_api.write(
        bucket=BUCKET,
        org=ORG,
        record=point
    )

    print("================================")
    print("INFLUXDB WRITE : SUCCESS")
    print("Measurement    : sensor_raw")
    print("Bucket         :", BUCKET)
    print("Organization   :", ORG)
    print("================================")

except Exception as e:
    print("INFLUXDB WRITE : FAILED")
    print("Error:", e)

finally:
    client.close()