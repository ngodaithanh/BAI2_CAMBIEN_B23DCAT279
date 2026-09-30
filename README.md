# BÀI THỰC HÀNH SỐ 2 – THU THẬP, LƯU TRỮ VÀ TIỀN XỬ LÝ DỮ LIỆU IoT

**Học phần:** IoT và Ứng dụng – INT14149  
**Sinh viên:** Ngô Đại Thành  
**Mã sinh viên:** B23DCAT279  

---

# 1. Giới thiệu

Project xây dựng một pipeline IoT hoàn chỉnh để:

- Thu thập dữ liệu cảm biến từ ESP32.
- Gửi dữ liệu qua giao thức MQTT.
- Validate dữ liệu tại phía gateway.
- Lưu dữ liệu dạng time-series vào InfluxDB.
- Phát hiện dữ liệu trùng lặp và mất mát.
- Tiền xử lý dữ liệu cảm biến.
- Phát hiện và loại bỏ outlier bằng IQR.
- Resampling dữ liệu theo cửa sổ thời gian.
- Tạo các đặc trưng Rolling Mean và Delta.
- Chuẩn hóa dữ liệu bằng Min-Max Normalization.
- Lưu dữ liệu đã xử lý vào measurement mới.
- Hiển thị dữ liệu thông qua Streamlit Dashboard.
- Theo dõi độ trễ end-to-end của pipeline.

---

# 2. Kiến trúc hệ thống

Pipeline của hệ thống:

```text
ESP32 / Wokwi
      |
      | Sensor Data
      v
DHT22 + HC-SR04
      |
      | JSON / MQTT
      v
HiveMQ Public MQTT Broker
      |
      | Subscribe
      v
Python MQTT Collector
      |
      | Validate
      | Duplicate Detection
      | Data Loss Detection
      v
InfluxDB
sensor_raw
      |
      | Query
      v
Python Preprocessing
      |
      | Missing Value Handling
      | Physical Range Validation
      | IQR Outlier Detection
      | 30-second Resampling
      | Rolling Mean
      | Delta
      | Min-Max Normalization
      v
InfluxDB
sensor_processed_v2
      |
      v
Streamlit Dashboard
```

---

# 3. Phần cứng và cảm biến

Hệ thống sử dụng ESP32 với các cảm biến:

| Thiết bị | Chức năng | GPIO |
|---|---|---:|
| ESP32 | Thiết bị xử lý trung tâm | - |
| DHT22 | Đo nhiệt độ và độ ẩm | GPIO 15 |
| HC-SR04 TRIG | Phát xung siêu âm | GPIO 5 |
| HC-SR04 ECHO | Nhận xung phản hồi | GPIO 18 |
| LED | Báo publish thành công | GPIO 2 |

ESP32 được mô phỏng bằng Wokwi.

Chu kỳ thu thập và publish dữ liệu:

```text
5 giây / lần
```

---

# 4. MQTT

## 4.1 MQTT Broker

Project sử dụng HiveMQ Public Broker:

```text
Broker: broker.hivemq.com
Port:   1883
```

Topic của thiết bị:

```text
ptit/iot/B23DCAT279/sensor
```

ESP32 đóng vai trò MQTT Publisher.

Python Collector đóng vai trò MQTT Subscriber.

---

# 5. Định dạng dữ liệu

ESP32 publish dữ liệu dưới dạng JSON.

Ví dụ:

```json
{
    "temperature": 25.00,
    "humidity": 50.00,
    "distance_cm": 100.82,
    "rssi": -77,
    "sequence": 1,
    "uptime_s": 10,
    "timestamp_ms": 1790794053282
}
```

Ý nghĩa các trường:

| Field | Ý nghĩa |
|---|---|
| temperature | Nhiệt độ đo từ DHT22 |
| humidity | Độ ẩm đo từ DHT22 |
| distance_cm | Khoảng cách đo bằng HC-SR04 |
| rssi | Cường độ tín hiệu Wi-Fi |
| sequence | Số thứ tự bản tin |
| uptime_s | Thời gian ESP32 đã hoạt động |
| timestamp_ms | Thời điểm gửi bản tin |

`sequence` được sử dụng để hỗ trợ phát hiện bản tin trùng lặp hoặc bị mất.

`timestamp_ms` được sử dụng để phục vụ việc phân tích độ trễ của pipeline.

---

# 6. Cấu trúc project

```text
BAI2_CAMBIEN_B23DCAT279/
│
├── src/
│   └── main.cpp
│
├── collector/
│   ├── mqtt_to_influx.py
│   └── preprocess.py
│
├── app.py
├── diagram.json
├── platformio.ini
├── requirements.txt
└── README.md
```

Chức năng chính:

### `src/main.cpp`

Firmware ESP32:

- kết nối Wi-Fi;
- đọc DHT22;
- đọc HC-SR04;
- lấy RSSI;
- tạo sequence number;
- tạo timestamp;
- đóng gói JSON;
- publish MQTT.

### `collector/mqtt_to_influx.py`

Gateway/collector:

```text
MQTT
 ↓
Subscribe
 ↓
JSON Decode
 ↓
Validation
 ↓
Duplicate / Loss Detection
 ↓
InfluxDB sensor_raw
```

### `collector/preprocess.py`

Thực hiện pipeline tiền xử lý:

```text
sensor_raw
 ↓
Missing Values
 ↓
Range Validation
 ↓
IQR
 ↓
Resampling
 ↓
Feature Engineering
 ↓
Normalization
 ↓
sensor_processed_v2
```

### `app.py`

Streamlit Dashboard để giám sát dữ liệu.

---

# 7. Cài đặt môi trường

## 7.1 Yêu cầu

Cần cài đặt:

- Python 3.x
- PlatformIO
- VS Code
- Wokwi
- InfluxDB 2.x

Các thư viện Python chính:

```text
paho-mqtt
influxdb-client
pandas
numpy
streamlit
```

---

# 8. Cài đặt thư viện Python

Mở PowerShell tại thư mục project:

```powershell
cd "C:\Users\THANH PC\OneDrive\Documents\PlatformIO\Projects\BAI2_CAMBIEN_B23DCAT279"
```

Cài đặt thư viện:

```powershell
python -m pip install paho-mqtt influxdb-client pandas numpy streamlit
```

Hoặc nếu project có `requirements.txt`:

```powershell
python -m pip install -r requirements.txt
```

---

# 9. Cấu hình InfluxDB

## 9.1 Khởi động InfluxDB

Khởi động InfluxDB 2.x trên máy.

Sau đó truy cập:

```text
http://localhost:8086
```

## 9.2 Cấu hình sử dụng

Project sử dụng:

```text
Organization: PTIT
Bucket:       iot_data
```

Trong bucket `iot_data` có các measurement chính:

```text
sensor_raw
sensor_processed_v2
```

Trong quá trình phát triển có thể xuất hiện measurement cũ:

```text
sensor_processed
```

Measurement chính được sử dụng trong phiên bản hiện tại là:

```text
sensor_processed_v2
```

---

# 10. Retention Policy

Bucket `iot_data` được cấu hình retention:

```text
30 days
```

Điều này có nghĩa dữ liệu cũ hơn 30 ngày sẽ tự động được xóa.

Mục đích:

- giới hạn dung lượng database;
- tránh dữ liệu IoT tăng không giới hạn;
- giảm chi phí lưu trữ;
- phù hợp với dữ liệu time-series phục vụ giám sát ngắn hạn.

Cấu hình trong InfluxDB:

```text
Load Data
→ Buckets
→ iot_data
→ Edit
→ Delete Data: Older Than
→ 30 days
→ Save Changes
```

---

# 11. Thiết kế schema InfluxDB

## Measurement `sensor_raw`

Lưu dữ liệu nhận trực tiếp từ MQTT.

### Tag

```text
device_id = ESP32-B23DCAT279
```

### Fields

```text
temperature
humidity
distance_cm
rssi
sequence
uptime_s
timestamp_ms
latency_ms
```

Ví dụ:

```text
measurement = sensor_raw
tag:
    device_id = ESP32-B23DCAT279

fields:
    temperature = 25.0
    humidity = 50.0
    distance_cm = 100.82
    rssi = -77
    sequence = 1
```

---

# 12. Chạy ESP32 / Wokwi

Mở project PlatformIO và Wokwi.

Chạy simulation.

Khi hoạt động thành công, Serial Monitor hiển thị:

```text
WiFi        : CONNECTED

MQTT        : CONNECTED

========== SENSOR DATA ==========
Temperature : 25.00 °C
Humidity    : 50.00 %RH
Distance    : 100.82 cm
WiFi RSSI   : -77 dBm
Sequence    : 1
Topic       : ptit/iot/B23DCAT279/sensor
Publish     : OK
=================================
```

ESP32 publish một bản tin khoảng mỗi 5 giây theo thời gian mô phỏng.

---

# 13. Chạy MQTT Collector

Mở PowerShell mới tại thư mục project:

```powershell
python collector\mqtt_to_influx.py
```

Nếu kết nối thành công:

```text
======================================
      BAI 2 - IoT DATA COLLECTOR
======================================

MQTT       : CONNECTED
Broker     : broker.hivemq.com
Topic      : ptit/iot/B23DCAT279/sensor
InfluxDB   : http://127.0.0.1:8086
Bucket     : iot_data
```

Khi nhận dữ liệu:

```text
========== MQTT MESSAGE ==========

Result      : VALID
Sequence chk: NORMAL
InfluxDB    : WRITE SUCCESS

Temperature : 25.0 °C
Humidity    : 50.0 %
Distance    : 100.82 cm
RSSI        : -80 dBm

Sequence gap: 0
Received    : 8
Written     : 8
Duplicates  : 0
Lost total  : 0
Device reset: 0
```

---

# 14. Validation dữ liệu

Collector kiểm tra dữ liệu trước khi lưu.

Các trường bắt buộc:

```text
temperature
humidity
distance_cm
rssi
sequence
uptime_s
```

Ngoài ra chương trình kiểm tra:

- kiểu dữ liệu;
- NaN;
- Infinity;
- phạm vi vật lý.

Ví dụ phạm vi nhiệt độ:

```text
-40 <= temperature <= 80
```

Độ ẩm:

```text
0 <= humidity <= 100
```

Dữ liệu không hợp lệ sẽ không được ghi vào database.

---

# 15. Phát hiện dữ liệu trùng lặp

Mỗi MQTT message có:

```text
sequence
```

Ví dụ:

```text
1
2
3
4
5
```

Nếu collector nhận lại cùng sequence:

```text
1
2
3
3
4
```

thì có thể xác định bản tin `3` bị trùng.

Collector theo dõi:

```text
Duplicates
```

Ví dụ trong quá trình chạy bình thường:

```text
Duplicates : 0
```

---

# 16. Phát hiện mất dữ liệu

Sequence cũng được dùng để phát hiện khoảng trống.

Ví dụ:

```text
1
2
3
5
```

Sau `3`, collector mong đợi:

```text
4
```

nhưng nhận:

```text
5
```

Do đó:

```text
Sequence gap = 1
```

Điều này cho thấy có khả năng một message bị mất trong pipeline.

Các thống kê:

```text
Sequence gap
Lost total
```

Ví dụ thực nghiệm:

```text
Sequence gap: 0
Lost total  : 0
```

nghĩa là trong khoảng thử nghiệm chưa phát hiện mất bản tin theo sequence.

---

# 17. Tiền xử lý dữ liệu

Chạy:

```powershell
python collector\preprocess.py
```

Pipeline thực hiện:

```text
[1] Reading sensor_raw from InfluxDB

[2] Handling missing values

[3] Physical range validation

[4] Detecting outliers using IQR

[5] Resampling data to 30-second windows

[6] Creating features

[7] Normalizing data using Min-Max normalization

[8] Writing sensor_processed_v2 to InfluxDB
```

---

# 18. Missing Values

Chương trình kiểm tra dữ liệu thiếu của:

```text
temperature
humidity
distance_cm
rssi
```

Ví dụ:

```text
Missing values BEFORE:

temperature    0
humidity       0
distance_cm    0
rssi           0
```

Sau xử lý:

```text
Missing values AFTER:

temperature    0
humidity       0
distance_cm    0
rssi           0
```

---

# 19. Physical Range Validation

Dữ liệu vượt khỏi phạm vi vật lý được loại bỏ.

Ví dụ:

```text
temperature < -40
temperature > 80

humidity < 0
humidity > 100

distance < 0
distance > 400

rssi < -120
rssi > 0
```

---

# 20. Phát hiện Outlier bằng IQR

Project sử dụng Interquartile Range (IQR).

Công thức:

```text
IQR = Q3 - Q1
```

Ngưỡng dưới:

```text
Lower = Q1 - 1.5 × IQR
```

Ngưỡng trên:

```text
Upper = Q3 + 1.5 × IQR
```

Giá trị ngoài khoảng:

```text
[Lower, Upper]
```

được xem là outlier.

Ví dụ kết quả thực nghiệm:

```text
rssi -> Lower=-106.00, Upper=-66.00, Outliers=2
```

Hai mẫu RSSI bất thường được phát hiện và loại khỏi dữ liệu dùng cho bước xử lý tiếp theo.

Nếu:

```text
IQR = 0
```

chương trình bỏ qua IQR cho trường đó vì dữ liệu không có đủ độ biến thiên để tạo ngưỡng IQR có ý nghĩa.

---

# 21. Resampling

Sau khi làm sạch, dữ liệu được resampling theo:

```text
30 seconds
```

Mục đích:

- đưa dữ liệu về cùng cửa sổ thời gian;
- giảm số lượng điểm dữ liệu;
- hỗ trợ phân tích time-series;
- giảm nhiễu ngắn hạn.

Ví dụ:

```text
Raw records       : 72
Resampled records : 28
```

---

# 22. Feature Engineering

Project tạo thêm các đặc trưng.

## Rolling Mean

Ví dụ:

```text
temperature_rolling_mean
humidity_rolling_mean
distance_rolling_mean
rssi_rolling_mean
```

Rolling Mean giúp làm mượt biến động ngắn hạn của dữ liệu.

## Delta

Ví dụ:

```text
temperature_delta
humidity_delta
distance_delta
rssi_delta
```

Delta biểu diễn mức thay đổi giữa các mẫu liên tiếp:

```text
delta(t) = x(t) - x(t-1)
```

Nó giúp phát hiện các thay đổi nhanh của cảm biến.

---

# 23. Min-Max Normalization

Dữ liệu được chuẩn hóa về khoảng:

```text
[0, 1]
```

Công thức:

```text
x_normalized =
(x - x_min) / (x_max - x_min)
```

Các trường được tạo có dạng:

```text
temperature_normalized
humidity_normalized
distance_normalized
rssi_normalized
```

Nếu một trường có:

```text
max = min
```

thì không thể áp dụng phép chia Min-Max thông thường vì mẫu số bằng 0. Chương trình xử lý trường hợp này riêng để tránh lỗi chia cho 0.

---

# 24. Dữ liệu sau tiền xử lý

Dữ liệu được lưu vào:

```text
sensor_processed_v2
```

Ví dụ output:

```text
Raw records              : 72
Range-invalid removed    : 0
IQR outliers removed     : 2
Resampled records        : 28
Processed records written: 28

Resampling : 30 seconds
Outlier    : IQR
Features   : Rolling Mean + Delta
Normalize  : Min-Max [0,1]
Output     : sensor_processed_v2
```

---

# 25. Kiểm tra dữ liệu bằng InfluxDB Data Explorer

Truy cập:

```text
http://localhost:8086
```

Mở:

```text
Data Explorer
```

Chọn:

```text
FROM
→ iot_data
```

Sau đó có thể chọn:

```text
sensor_raw
```

hoặc:

```text
sensor_processed_v2
```

Các field processed có thể gồm:

```text
distance_cm
distance_delta
distance_normalized
distance_rolling_mean

humidity
humidity_delta
humidity_normalized
humidity_rolling_mean

rssi
rssi_delta
rssi_normalized
rssi_rolling_mean

temperature
temperature_delta
temperature_normalized
temperature_rolling_mean
```

---

# 26. Streamlit Dashboard

Chạy:

```powershell
streamlit run app.py
```

Streamlit sẽ cung cấp URL local, thường có dạng:

```text
http://localhost:8501
```

Dashboard gồm các phần:

```text
IoT Sensor Monitoring Dashboard

Current Sensor Values

Real-time Raw Sensor Data

End-to-End Latency Analysis

Latency Statistics

Processed Sensor Data

Normalized Data [0 - 1]

Processed Data Table

IoT Data Pipeline
```

---

# 27. Current Sensor Values

Dashboard hiển thị giá trị gần nhất:

```text
Temperature
Humidity
Distance
WiFi RSSI
Latency
```

Ví dụ:

```text
Temperature : 25.00 °C
Humidity    : 50.00 %
Distance    : 100.82 cm
WiFi RSSI   : -93 dBm
```

---

# 28. Đo độ trễ End-to-End

ESP32 tạo:

```text
timestamp_ms
```

Collector lấy thời gian nhận:

```text
receive_time_ms
```

Độ trễ được tính:

```text
latency_ms =
receive_time_ms - timestamp_ms
```

Dashboard có thể thống kê:

```text
Current Latency
Average Latency
Minimum Latency
Maximum Latency
```

## Lưu ý về Wokwi

Trong thực nghiệm, thời gian mô phỏng của Wokwi và thời gian thực của máy host có thể không tiến triển hoàn toàn đồng bộ.

Ví dụ ESP32 được lập trình publish sau mỗi:

```text
5000 ms
```

theo thời gian mô phỏng, nhưng một chu kỳ mô phỏng có thể mất nhiều hơn 5 giây theo đồng hồ của máy tính.

Vì vậy giá trị latency đo được trong môi trường Wokwi có thể tăng dần hoặc đôi khi xuất hiện giá trị âm nhỏ.

Do đó kết quả latency trong bài này được sử dụng chủ yếu để:

- minh họa phương pháp đo end-to-end;
- quan sát pipeline;
- phát hiện vấn đề đồng bộ thời gian.

Nó không nên được xem là benchmark chính xác của độ trễ mạng MQTT thực tế.

Trong triển khai trên ESP32 vật lý, các thiết bị cần được đồng bộ thời gian tốt trước khi đánh giá latency chính xác.

---

# 29. Dashboard Real-time

Luồng dữ liệu dashboard:

```text
ESP32
 ↓
MQTT
 ↓
Python Collector
 ↓
sensor_raw
 ↓
Streamlit
```

Khi ESP32 tiếp tục publish, collector tiếp tục ghi dữ liệu mới vào InfluxDB.

Dashboard truy vấn dữ liệu để hiển thị các giá trị và biểu đồ theo khoảng thời gian được chọn.

---

# 30. Thứ tự chạy toàn bộ hệ thống

Khi demo, thực hiện theo thứ tự sau.

## Bước 1 – Khởi động InfluxDB

Đảm bảo:

```text
http://localhost:8086
```

truy cập được.

## Bước 2 – Chạy Wokwi

Kiểm tra Serial Monitor:

```text
WiFi : CONNECTED
MQTT : CONNECTED
```

## Bước 3 – Chạy Collector

Mở PowerShell:

```powershell
python collector\mqtt_to_influx.py
```

Kiểm tra:

```text
MQTT       : CONNECTED
Result     : VALID
InfluxDB   : WRITE SUCCESS
```

## Bước 4 – Kiểm tra `sensor_raw`

Mở InfluxDB Data Explorer:

```text
iot_data
→ sensor_raw
```

## Bước 5 – Chạy preprocessing

```powershell
python collector\preprocess.py
```

Kiểm tra:

```text
Processed records written: ...
Output: sensor_processed_v2
```

## Bước 6 – Kiểm tra processed data

InfluxDB:

```text
iot_data
→ sensor_processed_v2
```

## Bước 7 – Chạy Dashboard

Mở PowerShell khác:

```powershell
streamlit run app.py
```

Mở URL Streamlit được hiển thị.

---

# 31. Kịch bản demo

Kịch bản demo ngắn:

```text
1. Mở Wokwi.
2. Cho ESP32 gửi dữ liệu.
3. Mở MQTT Collector.
4. Chứng minh JSON được nhận.
5. Chứng minh dữ liệu VALID.
6. Chứng minh WRITE SUCCESS.
7. Cho xem sequence/loss/duplicate.
8. Mở InfluxDB sensor_raw.
9. Chạy preprocess.py.
10. Cho xem IQR/outlier.
11. Cho xem resampling.
12. Cho xem sensor_processed_v2.
13. Mở Streamlit Dashboard.
14. Cho xem raw data.
15. Cho xem processed data.
16. Cho xem normalized data.
17. Cho xem latency.
18. Giải thích retention 30 days.
```

---

# 32. Troubleshooting

## Không truy cập được InfluxDB

Kiểm tra:

```text
http://localhost:8086
```

Nếu không truy cập được, kiểm tra InfluxDB đã được khởi động hay chưa.

---

## MQTT không nhận được dữ liệu

Kiểm tra topic của ESP32:

```text
ptit/iot/B23DCAT279/sensor
```

và topic trong:

```text
mqtt_to_influx.py
```

phải giống nhau.

---

## `sensor_raw` không có dữ liệu

Kiểm tra Collector có hiển thị:

```text
InfluxDB : WRITE SUCCESS
```

hay không.

Kiểm tra:

```text
INFLUX_URL
INFLUX_TOKEN
INFLUX_ORG
INFLUX_BUCKET
```

---

## Không thấy `sensor_processed_v2`

Chạy:

```powershell
python collector\preprocess.py
```

Sau đó kiểm tra:

```text
Processed records written
```

Nếu bằng 0, cần kiểm tra khoảng thời gian query và dữ liệu trong `sensor_raw`.

---

## Field type conflict

InfluxDB yêu cầu một field trong cùng measurement có kiểu dữ liệu nhất quán.

Ví dụ lỗi:

```text
field type conflict:
input field "rssi" is type float,
already exists as type integer
```

Đây là lý do project sử dụng measurement:

```text
sensor_processed_v2
```

sau khi thay đổi schema/kiểu dữ liệu trong quá trình phát triển.

---

## Dashboard không thấy processed data

Kiểm tra:

```text
sensor_processed_v2
```

có dữ liệu trong khoảng thời gian Dashboard đang chọn hay không.

Ví dụ nếu dữ liệu cũ hơn một giờ nhưng Dashboard đang query:

```text
-1h
```

thì processed data sẽ không xuất hiện.

Hãy chọn khoảng thời gian lớn hơn hoặc chạy lại:

```powershell
python collector\preprocess.py
```

---

## Latency tăng dần

Điều này có thể xảy ra khi sử dụng Wokwi do tốc độ thời gian mô phỏng không hoàn toàn trùng với thời gian của máy host.

Không nên tự ý trừ một hằng số cố định để làm đẹp kết quả vì sai lệch không nhất thiết cố định.

---

# 33. Đánh giá kết quả

Pipeline đã thực hiện được:

```text
ESP32
→ MQTT
→ Python Collector
→ InfluxDB
→ Preprocessing
→ InfluxDB Processed Data
→ Streamlit
```

Các chức năng đã triển khai:

- Thu thập dữ liệu cảm biến.
- MQTT publish/subscribe.
- JSON data format.
- Input validation.
- Time-series storage.
- Retention policy.
- Duplicate detection.
- Data-loss detection.
- Missing-value handling.
- Physical range validation.
- IQR outlier detection.
- 30-second resampling.
- Rolling Mean.
- Delta.
- Min-Max normalization.
- Measurement riêng cho processed data.
- Dashboard.
- End-to-end latency monitoring.

---

# 34. Khó khăn gặp phải

## 34.1 Field type conflict trong InfluxDB

Trong quá trình phát triển, trường `rssi` từng được ghi với các kiểu dữ liệu khác nhau giữa dữ liệu cũ và dữ liệu sau xử lý.

InfluxDB trả về lỗi:

```text
field type conflict
```

Giải pháp:

```text
sensor_processed_v2
```

được sử dụng làm measurement mới với schema nhất quán.

---

## 34.2 Outlier với dữ liệu ít biến thiên

Một số cảm biến mô phỏng có giá trị gần như cố định.

Ví dụ:

```text
temperature = 25
humidity = 50
```

Khi:

```text
Q1 = Q3
```

thì:

```text
IQR = 0
```

Trong trường hợp này chương trình bỏ qua IQR cho field đó.

---

## 34.3 Đồng bộ thời gian

Timestamp của Wokwi và đồng hồ máy host có thể có sai lệch.

Điều này ảnh hưởng tới phép đo:

```text
latency =
receive_time - sent_time
```

Do đó latency trong môi trường mô phỏng được xem là số liệu phục vụ phân tích pipeline, không phải benchmark mạng chính xác.

---

# 35. Hướng phát triển

Hệ thống có thể được mở rộng bằng:

- ESP32 vật lý thay cho Wokwi.
- MQTT over TLS.
- MQTT authentication.
- Private MQTT Broker.
- Docker hóa InfluxDB và dashboard.
- Grafana.
- Edge processing.
- Alert khi nhiệt độ vượt ngưỡng.
- Phát hiện bất thường nâng cao.
- So sánh InfluxDB và MongoDB Time-Series.
- Machine Learning trên dữ liệu cảm biến.
- QoS 1/2 để tăng độ tin cậy truyền dữ liệu.

---

# 36. Kết luận

Bài thực hành xây dựng thành công một pipeline dữ liệu IoT từ thiết bị đến hệ thống giám sát.

Luồng xử lý chính:

```text
Sensor
→ ESP32
→ MQTT
→ Python
→ InfluxDB
→ Data Preprocessing
→ Streamlit Dashboard
```

Dữ liệu thô được lưu trong:

```text
sensor_raw
```

Dữ liệu sau tiền xử lý được lưu trong:

```text
sensor_processed_v2
```

Hệ thống đáp ứng các chức năng chính gồm thu thập, lưu trữ, validation, phát hiện mất/trùng dữ liệu, tiền xử lý, phát hiện outlier, resampling, tạo đặc trưng, normalization và trực quan hóa dữ liệu IoT.