from datetime import datetime
import json
import sqlite3
import paho.mqtt.client as mqtt

DB_NAME = "weather_data.db"


# Деректер базасын және кестені инициализациялау функциясы
def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      """
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        device TEXT,
        temperature REAL,
        humidity REAL,
        pressure REAL
    )
    """
  )
  conn.commit()
  conn.close()


init_db()
print("[INFO] Деректер базасы сәтті дайындалды!")


# MQTT арқылы хабар келгенде іске қосылатын функция
def on_message(client, userdata, msg):
  try:
    payload_str = msg.payload.decode("utf-8")
    data = json.loads(payload_str)

    device = data.get("device")
    temp = data.get("temperature")
    hum = data.get("humidity")
    pressure = data.get("pressure")

    # Дәл қазіргі нақты уақытты аламыз (YYYY-MM-DD HH:MM:SS форматында)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"[{current_time}] АЛЫНДЫ -> Температура: {temp}°C | Ылғалдылық:"
        f" {hum}% | Қысым: {pressure} hPa"
    )

    # Деректі нақты уақытпен базаға жазамыз
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry (timestamp, device, temperature, humidity,"
        " pressure) VALUES (?, ?, ?, ?, ?)",
        (current_time, device, temp, hum, pressure),
    )
    conn.commit()
    conn.close()
    print("[SAXTALDY] Дерек нақты уақытпен базаға сәтті жазылды!")

  except Exception as e:
    print(f"[ҚАТЕ] Деректі сақтау кезінде қате кетті: {e}")


# MQTT клиент баптаулары
broker_address = "broker.hivemq.com"
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2, "PythonWeatherReceiverClient"
)
client.on_message = on_message

print(f"[INFO] {broker_address} серверіне қосылуда...")
client.connect(broker_address, 1883)
client.subscribe("smart/weather/telemetry")

client.loop_start()

try:
  print(
      "[INFO] Деректерді қабылдау басталды. Тоқтату үшін Ctrl+C басыңыз."
  )
  while True:
    pass
except KeyboardInterrupt:
  print("\n[INFO] Бағдарлама тоқтатылды.")
  client.loop_stop()