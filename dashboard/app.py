import streamlit as st

import pandas as pd

import plotly.express as px

from influxdb_client import InfluxDBClient

# ==========================================================

# PAGE CONFIG

# ==========================================================

st.set_page_config(

    page_title="PTIT IoT Dashboard",

    page_icon="📡",

    layout="wide"

)

st.title("📡 IoT Sensor Monitoring Dashboard")

st.caption("ESP32 • MQTT • InfluxDB • Data Preprocessing")

# ==========================================================

# INFLUXDB CONFIG

# ==========================================================

URL = "http://127.0.0.1:8086"

# DÁN TOKEN INFLUXDB CỦA BẠN

TOKEN = "dt-6Vk7wY60P_yn14JPW8-v508zufQbZYpcy9jdOusuYwq8behi4g_Im3uDAAUmrQpfGfYtSmf-ttNVqqI4xLw=="

ORG = "PTIT"

BUCKET = "iot_data"

RAW_MEASUREMENT = "sensor_raw"

PROCESSED_MEASUREMENT = "sensor_processed_v2"

# ==========================================================

# CONNECT

# ==========================================================

client = InfluxDBClient(

    url=URL,

    token=TOKEN,

    org=ORG

)

query_api = client.query_api()

# ==========================================================

# FUNCTION: READ MEASUREMENT

# ==========================================================

def load_data(measurement, range_time="-1h"):

    query = f'''

    from(bucket: "{BUCKET}")

      |> range(start: {range_time})

      |> filter(fn: (r) =>

          r["_measurement"] == "{measurement}"

      )

      |> pivot(

          rowKey: ["_time"],

          columnKey: ["_field"],

          valueColumn: "_value"

      )

    '''

    tables = query_api.query(query)

    rows = []

    for table in tables:

        for record in table.records:

            row = dict(record.values)

            row["time"] = record.get_time()

            rows.append(row)

    if not rows:

        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["time"] = pd.to_datetime(

        df["time"],

        utc=True

    )

    df = (

        df.sort_values("time")

        .drop_duplicates(

            subset=["time"],

            keep="last"

        )

    )

    return df

# ==========================================================

# SIDEBAR

# ==========================================================

st.sidebar.header("⚙️ Dashboard Settings")

time_range = st.sidebar.selectbox(

    "Time Range",

    options=[

        "-15m",

        "-30m",

        "-1h",

        "-3h",

        "-6h",

        "-24h"

    ],

    index=2

)

st.sidebar.markdown("---")

st.sidebar.write("**Device**")

st.sidebar.code("ESP32-B23DCAT279")

st.sidebar.write("**Bucket**")

st.sidebar.code(BUCKET)

st.sidebar.write("**Raw measurement**")

st.sidebar.code(RAW_MEASUREMENT)

st.sidebar.write("**Processed measurement**")

st.sidebar.code(PROCESSED_MEASUREMENT)

# ==========================================================

# LOAD DATA

# ==========================================================

try:

    raw_df = load_data(

        RAW_MEASUREMENT,

        time_range

    )

    processed_df = load_data(

        PROCESSED_MEASUREMENT,

        time_range

    )

except Exception as e:

    st.error(

        f"Không thể kết nối InfluxDB: {e}"

    )

    st.stop()

# ==========================================================

# CONNECTION STATUS

# ==========================================================

if raw_df.empty:

    st.warning(

        "Không tìm thấy sensor_raw "

        "trong khoảng thời gian đã chọn."

    )

else:

    st.success(

        f"InfluxDB connected • "

        f"{len(raw_df)} raw records loaded"

    )

# ==========================================================
# CURRENT SENSOR VALUES
# ==========================================================
st.subheader("📟 Current Sensor Values")

if not raw_df.empty:
    latest = raw_df.iloc[-1]
    col1, col2, col3, col4, col5 = st.columns(5)
    temperature = latest.get("temperature", float("nan"))
    humidity = latest.get("humidity", float("nan"))
    distance = latest.get("distance_cm", float("nan"))
    rssi = latest.get("rssi", float("nan"))
    latency = latest.get("latency_ms", float("nan"))
    col1.metric("🌡 Temperature", f"{temperature:.2f} °C")
    col2.metric("💧 Humidity", f"{humidity:.2f} %")
    col3.metric("📏 Distance", f"{distance:.2f} cm")
    col4.metric("📶 WiFi RSSI", f"{rssi:.0f} dBm")
    col5.metric("⏱ Latency", f"{latency:.0f} ms" if pd.notna(latency) else "N/A")
else:
    st.info("Chưa có dữ liệu để hiển thị.")

# ==========================================================

# RAW DATA CHARTS

# ==========================================================

st.markdown("---")

st.header("📊 Real-time Raw Sensor Data")

if not raw_df.empty:

    # Temperature

    if "temperature" in raw_df.columns:

        fig_temp = px.line(

            raw_df,

            x="time",

            y="temperature",

            markers=True,

            title="Temperature"

        )

        fig_temp.update_layout(

            xaxis_title="Time",

            yaxis_title="Temperature (°C)"

        )

        st.plotly_chart(

            fig_temp,

            width="stretch"

        )

    # Humidity

    if "humidity" in raw_df.columns:

        fig_humidity = px.line(

            raw_df,

            x="time",

            y="humidity",

            markers=True,

            title="Humidity"

        )

        fig_humidity.update_layout(

            xaxis_title="Time",

            yaxis_title="Humidity (%)"

        )

        st.plotly_chart(

            fig_humidity,

            width="stretch"

        )

    # Distance

    if "distance_cm" in raw_df.columns:

        fig_distance = px.line(

            raw_df,

            x="time",

            y="distance_cm",

            markers=True,

            title="Distance"

        )

        fig_distance.update_layout(

            xaxis_title="Time",

            yaxis_title="Distance (cm)"

        )

        st.plotly_chart(

            fig_distance,

            width="stretch"

        )

    # RSSI

    if "rssi" in raw_df.columns:

        fig_rssi = px.line(

            raw_df,

            x="time",

            y="rssi",

            markers=True,

            title="WiFi RSSI"

        )

        fig_rssi.update_layout(

            xaxis_title="Time",

            yaxis_title="RSSI (dBm)"

        )

        st.plotly_chart(

            fig_rssi,

            width="stretch"

        )

# ==========================================================
# END-TO-END LATENCY ANALYSIS
# ==========================================================
st.markdown("---")
st.header("⏱ End-to-End Latency Analysis")

if not raw_df.empty and "latency_ms" in raw_df.columns:
    latency_df = raw_df[["time", "latency_ms"]].copy().dropna(subset=["latency_ms"])
    if not latency_df.empty:
        current_latency = latency_df["latency_ms"].iloc[-1]
        average_latency = latency_df["latency_ms"].mean()
        minimum_latency = latency_df["latency_ms"].min()
        maximum_latency = latency_df["latency_ms"].max()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⚡ Current Latency", f"{current_latency:.0f} ms")
        c2.metric("📊 Average Latency", f"{average_latency:.0f} ms")
        c3.metric("🟢 Minimum Latency", f"{minimum_latency:.0f} ms")
        c4.metric("🔴 Maximum Latency", f"{maximum_latency:.0f} ms")
        fig_latency = px.line(latency_df, x="time", y="latency_ms", markers=True, title="End-to-End IoT Latency")
        fig_latency.update_layout(xaxis_title="Time", yaxis_title="Latency (ms)")
        st.plotly_chart(fig_latency, width="stretch")
        stats = pd.DataFrame({"Metric":["Current","Average","Minimum","Maximum"], "Latency (ms)":[current_latency,average_latency,minimum_latency,maximum_latency]})
        st.subheader("📋 Latency Statistics")
        st.dataframe(stats, width="stretch", hide_index=True)
    else:
        st.info("Chưa có bản ghi latency trong khoảng thời gian đã chọn.")
else:
    st.info("Chưa có field latency_ms trong sensor_raw. Hãy chạy collector có ghi latency_ms.")

# ==========================================================

# PROCESSED DATA

# ==========================================================

st.markdown("---")

st.header("🧪 Processed Sensor Data")

if processed_df.empty:

    st.warning(

        "Không tìm thấy sensor_processed_v2 "

        "trong khoảng thời gian đã chọn."

    )

else:

    st.write(

        f"Processed records: "

        f"**{len(processed_df)}**"

    )

    # ------------------------------------------------------

    # Temperature vs Rolling Mean

    # ------------------------------------------------------

    if (

        "temperature" in processed_df.columns

        and

        "temperature_rolling_mean"

        in processed_df.columns

    ):

        temp_compare = processed_df[

            [

                "time",

                "temperature",

                "temperature_rolling_mean"

            ]

        ].copy()

        temp_compare = temp_compare.melt(

            id_vars="time",

            value_vars=[

                "temperature",

                "temperature_rolling_mean"

            ],

            var_name="Series",

            value_name="Value"

        )

        fig_processed = px.line(

            temp_compare,

            x="time",

            y="Value",

            color="Series",

            markers=True,

            title=(

                "Temperature vs "

                "Rolling Mean"

            )

        )

        fig_processed.update_layout(

            xaxis_title="Time",

            yaxis_title="Temperature (°C)"

        )

        st.plotly_chart(

            fig_processed,

            width="stretch"

        )

    # ------------------------------------------------------

    # Distance vs Rolling Mean

    # ------------------------------------------------------

    if (

        "distance_cm" in processed_df.columns

        and

        "distance_rolling_mean"

        in processed_df.columns

    ):

        distance_compare = processed_df[

            [

                "time",

                "distance_cm",

                "distance_rolling_mean"

            ]

        ].copy()

        distance_compare = distance_compare.melt(

            id_vars="time",

            value_vars=[

                "distance_cm",

                "distance_rolling_mean"

            ],

            var_name="Series",

            value_name="Value"

        )

        fig_distance_processed = px.line(

            distance_compare,

            x="time",

            y="Value",

            color="Series",

            markers=True,

            title=(

                "Distance vs "

                "Rolling Mean"

            )

        )

        fig_distance_processed.update_layout(

            xaxis_title="Time",

            yaxis_title="Distance (cm)"

        )

        st.plotly_chart(

            fig_distance_processed,

            width="stretch"

        )

# ==========================================================

# NORMALIZED DATA

# ==========================================================

st.markdown("---")

st.header("📐 Normalized Data [0 - 1]")

normalized_columns = [

    "temperature_normalized",

    "humidity_normalized",

    "distance_normalized",

    "rssi_normalized"

]

available_normalized = [

    col

    for col in normalized_columns

    if col in processed_df.columns

]

if (

    not processed_df.empty

    and available_normalized

):

    normalized_df = processed_df[

        ["time"] + available_normalized

    ].copy()

    normalized_long = normalized_df.melt(

        id_vars="time",

        value_vars=available_normalized,

        var_name="Sensor",

        value_name="Normalized Value"

    )

    fig_normalized = px.line(

        normalized_long,

        x="time",

        y="Normalized Value",

        color="Sensor",

        markers=True,

        title="Min-Max Normalized Sensor Data"

    )

    fig_normalized.update_layout(

        xaxis_title="Time",

        yaxis_title="Normalized Value"

    )

    st.plotly_chart(

        fig_normalized,

        width="stretch"

    )

else:

    st.info(

        "Chưa có normalized data."

    )

# ==========================================================

# DATA TABLE

# ==========================================================

st.markdown("---")

st.header("📋 Processed Data Table")

if not processed_df.empty:

    display_columns = [

        col

        for col in [

            "time",

            "temperature",

            "humidity",

            "distance_cm",

            "rssi",

            "temperature_rolling_mean",

            "distance_rolling_mean",

            "temperature_delta",

            "distance_delta",

            "temperature_normalized",

            "humidity_normalized",

            "distance_normalized",

            "rssi_normalized"

        ]

        if col in processed_df.columns

    ]

    st.dataframe(

        processed_df[

            display_columns

        ].sort_values(

            "time",

            ascending=False

        ),

        width="stretch"

    )

# ==========================================================

# PIPELINE INFO

# ==========================================================

st.markdown("---")

st.header("🔄 IoT Data Pipeline")

st.code(

    """

ESP32 / Wokwi

      |

      | MQTT JSON

      v

HiveMQ MQTT Broker

      |

      v

Python MQTT Subscriber

      |

      v

InfluxDB: sensor_raw

      |

      v

Preprocessing

  - Missing value handling

  - Physical range validation

  - IQR outlier detection

  - 30-second resampling

  - Rolling mean

  - Delta

  - Min-Max normalization

      |

      v

InfluxDB: sensor_processed_v2

      |

      v

Streamlit Dashboard

"""

)

# ==========================================================

# CLOSE

# ==========================================================

client.close()