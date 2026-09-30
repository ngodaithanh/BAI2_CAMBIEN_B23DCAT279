from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import pandas as pd

# ==========================================================
# INFLUXDB CONFIG
# ==========================================================

URL = "http://127.0.0.1:8086"

# Dán token InfluxDB hiện tại của bạn vào đây
TOKEN = "dt-6Vk7wY60P_yn14JPW8-v508zufQbZYpcy9jdOusuYwq8behi4g_Im3uDAAUmrQpfGfYtSmf-ttNVqqI4xLw=="

ORG = "PTIT"
BUCKET = "iot_data"

RAW_MEASUREMENT = "sensor_raw"

# Dùng measurement mới để tránh xung đột kiểu dữ liệu
# với sensor_processed cũ.
PROCESSED_MEASUREMENT = "sensor_processed_v2"

DEVICE_ID = "ESP32-B23DCAT279"


# ==========================================================
# CONNECT INFLUXDB
# ==========================================================

client = InfluxDBClient(
    url=URL,
    token=TOKEN,
    org=ORG
)

query_api = client.query_api()
write_api = client.write_api(write_options=SYNCHRONOUS)


print("=" * 60)
print("          IoT DATA PREPROCESSING")
print("=" * 60)


# ==========================================================
# 1. READ sensor_raw
# ==========================================================

query = f'''
from(bucket: "{BUCKET}")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "{RAW_MEASUREMENT}")
  |> pivot(
      rowKey: ["_time"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
'''

print("[1] Reading sensor_raw from InfluxDB...")

tables = query_api.query(query)

rows = []

for table in tables:
    for record in table.records:

        data = record.values

        rows.append({
            "time": record.get_time(),
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "distance_cm": data.get("distance_cm"),
            "rssi": data.get("rssi"),
            "sequence": data.get("sequence"),
            "uptime_s": data.get("uptime_s")
        })


if len(rows) == 0:
    print("ERROR: No sensor_raw data found.")
    client.close()
    exit()


df = pd.DataFrame(rows)

print("Records read:", len(df))


# ==========================================================
# 2. CONVERT DATA TYPES
# ==========================================================

sensor_columns = [
    "temperature",
    "humidity",
    "distance_cm",
    "rssi"
]

optional_columns = [
    "sequence",
    "uptime_s"
]


for col in sensor_columns + optional_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )


# ==========================================================
# 3. HANDLE MISSING VALUES
# ==========================================================

print()
print("[2] Handling missing values...")

print("Missing values BEFORE:")
print(df[sensor_columns].isnull().sum())


# Nội suy tuyến tính
df[sensor_columns] = df[sensor_columns].interpolate(
    method="linear",
    limit_direction="both"
)


# Nếu vẫn còn NaN thì loại bỏ
df = df.dropna(
    subset=sensor_columns
)


print()
print("Missing values AFTER:")
print(df[sensor_columns].isnull().sum())


# ==========================================================
# 4. PHYSICAL RANGE VALIDATION
# ==========================================================

print()
print("[3] Physical range validation...")


before_range = len(df)


df = df[
    df["temperature"].between(-40, 80)
    & df["humidity"].between(0, 100)
    & df["distance_cm"].between(0, 400)
    & df["rssi"].between(-120, 0)
].copy()


range_removed = before_range - len(df)


print(
    "Invalid physical-range records removed:",
    range_removed
)


if len(df) == 0:
    print(
        "ERROR: No valid data after range validation."
    )

    client.close()
    exit()


# ==========================================================
# 5. OUTLIER DETECTION USING IQR
# ==========================================================

print()
print("[4] Detecting outliers using IQR...")


outlier_columns = [
    "temperature",
    "humidity",
    "distance_cm",
    "rssi"
]


outlier_mask = pd.Series(
    False,
    index=df.index
)


for col in outlier_columns:

    Q1 = df[col].quantile(0.25)
    Q3 = df[col].quantile(0.75)

    IQR = Q3 - Q1


    # Nếu dữ liệu gần như cố định
    # thì IQR = 0 -> bỏ qua cột đó
    if IQR == 0:

        print(
            f"{col:15} -> "
            f"Q1={Q1:.2f}, "
            f"Q3={Q3:.2f}, "
            f"IQR=0 -> skipped"
        )

        continue


    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR


    current_outlier = (
        (df[col] < lower)
        | (df[col] > upper)
    )


    print(
        f"{col:15} -> "
        f"Lower={lower:.2f}, "
        f"Upper={upper:.2f}, "
        f"Outliers={current_outlier.sum()}"
    )


    outlier_mask = (
        outlier_mask
        | current_outlier
    )


outliers_removed = int(
    outlier_mask.sum()
)


df = df[
    ~outlier_mask
].copy()


print(
    "Total outlier records removed:",
    outliers_removed
)


if len(df) == 0:

    print(
        "ERROR: No data remaining "
        "after outlier removal."
    )

    client.close()
    exit()


# ==========================================================
# 6. PREPARE TIME INDEX
# ==========================================================

df["time"] = pd.to_datetime(
    df["time"],
    utc=True
)


df = df.sort_values("time")

df = df.set_index("time")


# ==========================================================
# 7. RESAMPLING
# ==========================================================

print()
print(
    "[5] Resampling data to "
    "30-second windows..."
)


# Mỗi 30 giây lấy trung bình
df_resampled = (
    df[sensor_columns]
    .resample("30s")
    .mean()
)


# Bỏ cửa sổ hoàn toàn không có dữ liệu
df_resampled = (
    df_resampled
    .dropna(how="all")
)


# Nội suy cửa sổ bị thiếu
df_resampled = (
    df_resampled
    .interpolate(
        method="time",
        limit_direction="both"
    )
)


print(
    "Resampled records:",
    len(df_resampled)
)


if len(df_resampled) == 0:

    print(
        "ERROR: No data after resampling."
    )

    client.close()
    exit()


# ==========================================================
# 8. FEATURE ENGINEERING
# ==========================================================

print()
print("[6] Creating features...")


# ----------------------------------------------------------
# Rolling Mean
# ----------------------------------------------------------

df_resampled[
    "temperature_rolling_mean"
] = (
    df_resampled["temperature"]
    .rolling(
        window=3,
        min_periods=1
    )
    .mean()
)


df_resampled[
    "humidity_rolling_mean"
] = (
    df_resampled["humidity"]
    .rolling(
        window=3,
        min_periods=1
    )
    .mean()
)


df_resampled[
    "distance_rolling_mean"
] = (
    df_resampled["distance_cm"]
    .rolling(
        window=3,
        min_periods=1
    )
    .mean()
)


df_resampled[
    "rssi_rolling_mean"
] = (
    df_resampled["rssi"]
    .rolling(
        window=3,
        min_periods=1
    )
    .mean()
)


# ----------------------------------------------------------
# Delta
# ----------------------------------------------------------

df_resampled[
    "temperature_delta"
] = (
    df_resampled["temperature"]
    .diff()
    .fillna(0)
)


df_resampled[
    "humidity_delta"
] = (
    df_resampled["humidity"]
    .diff()
    .fillna(0)
)


df_resampled[
    "distance_delta"
] = (
    df_resampled["distance_cm"]
    .diff()
    .fillna(0)
)


df_resampled[
    "rssi_delta"
] = (
    df_resampled["rssi"]
    .diff()
    .fillna(0)
)


# ==========================================================
# 9. NORMALIZATION - MIN MAX
# ==========================================================

print(
    "[7] Normalizing data using "
    "Min-Max normalization..."
)


def minmax_normalize(series):

    minimum = series.min()
    maximum = series.max()

    # Tránh chia cho 0 nếu tất cả
    # giá trị giống nhau
    if maximum == minimum:

        return pd.Series(
            0.0,
            index=series.index
        )

    return (
        (series - minimum)
        / (maximum - minimum)
    )


df_resampled[
    "temperature_normalized"
] = minmax_normalize(
    df_resampled["temperature"]
)


df_resampled[
    "humidity_normalized"
] = minmax_normalize(
    df_resampled["humidity"]
)


df_resampled[
    "distance_normalized"
] = minmax_normalize(
    df_resampled["distance_cm"]
)


df_resampled[
    "rssi_normalized"
] = minmax_normalize(
    df_resampled["rssi"]
)


# ==========================================================
# 10. WRITE sensor_processed_v2
# ==========================================================

print()
print(
    "[8] Writing sensor_processed_v2 "
    "to InfluxDB..."
)


write_count = 0


for timestamp, row in df_resampled.iterrows():

    point = (
        Point(PROCESSED_MEASUREMENT)

        # TAG
        .tag(
            "device_id",
            DEVICE_ID
        )

        # --------------------------------------------------
        # RESAMPLED VALUES
        # --------------------------------------------------

        .field(
            "temperature",
            float(row["temperature"])
        )

        .field(
            "humidity",
            float(row["humidity"])
        )

        .field(
            "distance_cm",
            float(row["distance_cm"])
        )

        # QUAN TRỌNG:
        # RSSI phải là float vì resampling dùng mean()
        .field(
            "rssi",
            float(row["rssi"])
        )

        # --------------------------------------------------
        # ROLLING MEAN
        # --------------------------------------------------

        .field(
            "temperature_rolling_mean",
            float(
                row[
                    "temperature_rolling_mean"
                ]
            )
        )

        .field(
            "humidity_rolling_mean",
            float(
                row[
                    "humidity_rolling_mean"
                ]
            )
        )

        .field(
            "distance_rolling_mean",
            float(
                row[
                    "distance_rolling_mean"
                ]
            )
        )

        .field(
            "rssi_rolling_mean",
            float(
                row[
                    "rssi_rolling_mean"
                ]
            )
        )

        # --------------------------------------------------
        # DELTA
        # --------------------------------------------------

        .field(
            "temperature_delta",
            float(
                row["temperature_delta"]
            )
        )

        .field(
            "humidity_delta",
            float(
                row["humidity_delta"]
            )
        )

        .field(
            "distance_delta",
            float(
                row["distance_delta"]
            )
        )

        .field(
            "rssi_delta",
            float(
                row["rssi_delta"]
            )
        )

        # --------------------------------------------------
        # NORMALIZED
        # --------------------------------------------------

        .field(
            "temperature_normalized",
            float(
                row[
                    "temperature_normalized"
                ]
            )
        )

        .field(
            "humidity_normalized",
            float(
                row[
                    "humidity_normalized"
                ]
            )
        )

        .field(
            "distance_normalized",
            float(
                row[
                    "distance_normalized"
                ]
            )
        )

        .field(
            "rssi_normalized",
            float(
                row[
                    "rssi_normalized"
                ]
            )
        )

        # Giữ timestamp của cửa sổ resampling
        .time(
            timestamp.to_pydatetime()
        )
    )


    write_api.write(
        bucket=BUCKET,
        org=ORG,
        record=point
    )

    write_count += 1


# ==========================================================
# 11. RESULT
# ==========================================================

print()

print("=" * 60)
print("             PREPROCESSING RESULT")
print("=" * 60)

print(
    "Raw records              :",
    len(rows)
)

print(
    "Range-invalid removed    :",
    range_removed
)

print(
    "IQR outliers removed     :",
    outliers_removed
)

print(
    "Resampled records        :",
    len(df_resampled)
)

print(
    "Processed records written:",
    write_count
)

print()

print(
    "Resampling : 30 seconds"
)

print(
    "Outlier    : IQR"
)

print(
    "Features   : Rolling Mean + Delta"
)

print(
    "Normalize  : Min-Max [0,1]"
)

print(
    "Output     :",
    PROCESSED_MEASUREMENT
)

print("=" * 60)


# ==========================================================
# 12. PREVIEW
# ==========================================================

print()
print("Processed data preview:")


print(
    df_resampled[
        [
            "temperature",
            "humidity",
            "distance_cm",
            "rssi",
            "temperature_rolling_mean",
            "temperature_delta",
            "temperature_normalized"
        ]
    ].tail(10)
)


# ==========================================================
# CLOSE CONNECTION
# ==========================================================

client.close()