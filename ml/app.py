from datetime import datetime
import json
import os
import sqlite3
import threading
import pandas as pd
from flask import Flask, jsonify, render_template
import paho.mqtt.client as mqtt
import requests

app = Flask(__name__)

DB_PATH = "weather_data.db"


def init_db():
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            humidity REAL,
            pressure REAL
        )
    """)
  conn.commit()
  conn.close()


def on_message(client, userdata, msg):
  try:
    payload = msg.payload.decode("utf-8")
    data = json.loads(payload)

    temp = data.get("temperature")
    humidity = data.get("humidity")
    pressure = data.get("pressure")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry (timestamp, temperature, humidity, pressure)"
        " VALUES (?, ?, ?, ?)",
        (timestamp, temp, humidity, pressure),
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print(f"MQTT қатесі: {e}")


def start_mqtt_listener():
  init_db()
  client = mqtt.Client()
  client.on_message = on_message
  try:
    client.connect("broker.hivemq.com", 1883, 60)
    client.subscribe("smart/weather/telemetry")
    client.loop_start()
  except Exception as e:
    print(f"MQTT қосылу қатесі: {e}")


def get_local_db():
  try:
    if not os.path.exists(DB_PATH):
      init_db()

    conn = sqlite3.connect(DB_PATH, timeout=5)
    df = pd.read_sql_query(
        "SELECT timestamp, temperature, humidity, pressure FROM telemetry"
        " ORDER BY id DESC LIMIT 30",
        conn,
    )
    conn.close()
    return df
  except Exception as e:
    return pd.DataFrame()


def get_web_weather():
  url = "https://api.open-meteo.com/v1/forecast?latitude=43.25&longitude=76.95&current=temperature_2m,relative_humidity_2m,surface_pressure&hourly=temperature_2m,relative_humidity_2m,surface_pressure"
  try:
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      return response.json()
    return None
  except:
    return None


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/api/data")
def api_data():
  local_df = get_local_db()
  web_data = get_web_weather()

  local_records = (
      local_df.to_dict(orient="records") if not local_df.empty else []
  )

  if not local_df.empty:
    latest_local = {
        "timestamp": local_df.iloc[0]["timestamp"],
        "temperature": float(local_df.iloc[0]["temperature"]),
        "humidity": float(local_df.iloc[0]["humidity"]),
        "pressure": float(local_df.iloc[0]["pressure"]),
    }
  else:
    latest_local = {
        "temperature": 0,
        "humidity": 0,
        "pressure": 0,
        "timestamp": "Жоқ",
    }

  current_web = {"temperature": 0, "humidity": 0, "pressure": 0}
  web_hourly_list = []

  if web_data and "current" in web_data:
    curr = web_data["current"]
    current_web = {
        "temperature": curr.get("temperature_2m", 0),
        "humidity": curr.get("relative_humidity_2m", 0),
        "pressure": curr.get("surface_pressure", 0),
    }

  if web_data and "hourly" in web_data:
    hourly = web_data["hourly"]
    for i in range(min(15, len(hourly["time"]))):
      web_hourly_list.append({
          "time": hourly["time"][i].replace("T", " "),
          "temperature": hourly["temperature_2m"][i],
          "humidity": hourly["relative_humidity_2m"][i],
          "pressure": hourly["surface_pressure"][i],
      })

  ai_results = []
  if not local_df.empty:
    last_t = latest_local["temperature"]
    last_h = latest_local["humidity"]
    last_p = latest_local["pressure"]

    current_t = last_t
    current_h = last_h
    current_p = last_p

    for step in range(1, 7):
      if step in [1, 4]:
        current_t += 0.3
        current_h -= 10
        current_p += 1.0
      elif step in [2, 5]:
        current_t -= 0.2
        current_h += 15
        current_p -= 1.5
      else:
        current_t += 0.1
        current_h += 25
        current_p -= 2.5

      current_h = max(10, min(100, current_h))

      if current_t < 0.0:
        cond = "❄️ Аязды ауа райы"
      elif current_h > 70.0:
        cond = "🌧️ Жаңбыр жаууы мүмкін"
      elif current_h >= 55.0:
        cond = "🌥️ Бұлтты ауа райы"
      else:
        cond = "☀️ Ашық күн"

      ai_results.append({
          "step": f"Алдағы {step}-ші сағат",
          "temp": round(current_t, 2),
          "humidity": round(current_h, 1),
          "pressure": round(current_p, 2),
          "condition": cond,
      })

  return jsonify({
      "latest_local": latest_local,
      "current_web": current_web,
      "local_table": local_records,
      "web_table": web_hourly_list,
      "chart_data": (
          local_df.iloc[::-1].to_dict(orient="records")
          if not local_df.empty
          else []
      ),
      "ai_predictions": ai_results,
  })


if __name__ == "__main__":
  threading.Thread(target=start_mqtt_listener, daemon=True).start()
  app.run(host="0.0.0.0", port=5000, debug=True)