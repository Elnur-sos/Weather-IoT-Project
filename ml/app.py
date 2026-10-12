from datetime import datetime
import json
import os
import sqlite3
import threading

import paho.mqtt.client as mqtt
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

DB_PATH = os.path.join(app.root_path, "weather_data.db")

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_PARAMS = {
    "latitude": 43.25,
    "longitude": 76.95,
    "current": (
        "temperature_2m,"
        "relative_humidity_2m,"
        "surface_pressure"
    ),
    "hourly": (
        "temperature_2m,"
        "relative_humidity_2m,"
        "surface_pressure"
    ),
    "timezone": "Asia/Almaty",
    "forecast_days": 2
}


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                temperature REAL,
                humidity REAL,
                pressure REAL
            )
        """)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        pressure = data.get("pressure")

        if (
            temperature is None
            or humidity is None
            or pressure is None
        ):
            print("MQTT: не все погодные значения получены")
            return

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO telemetry
                (timestamp, temperature, humidity, pressure)
                VALUES (?, ?, ?, ?)
                """,
                (timestamp, temperature, humidity, pressure)
            )

        print("MQTT: измерение сохранено")

    except Exception as e:
        print("Ошибка MQTT:", e)


def start_mqtt_listener():
    try:
        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        client.on_message = on_message

        client.connect("broker.hivemq.com", 1883, 60)
        client.subscribe("smart/weather/telemetry")
        client.loop_start()

        print("MQTT: подключение успешно")

    except Exception as e:
        print("MQTT недоступен:", e)


def get_local_data():
    try:
        with sqlite3.connect(DB_PATH, timeout=5) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute("""
                SELECT timestamp, temperature, humidity, pressure
                FROM telemetry
                ORDER BY id DESC
                LIMIT 30
            """).fetchall()

            return [dict(row) for row in rows]

    except Exception as e:
        print("Ошибка локальной базы:", e)
        return []


def get_web_weather():
    try:
        response = requests.get(
            WEATHER_URL,
            params=WEATHER_PARAMS,
            timeout=20
        )
        response.raise_for_status()

        data = response.json()

        if "current" not in data or "hourly" not in data:
            raise ValueError(
                "В ответе Open-Meteo отсутствуют current или hourly"
            )

        print("Open-Meteo: данные успешно получены")
        return data

    except Exception as e:
        print("Ошибка Open-Meteo:", e)
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    local_records = get_local_data()
    web_data = get_web_weather()

    if web_data:
        current = web_data["current"]

        current_web = {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "pressure": current.get("surface_pressure"),
            "time": current.get("time")
        }

        hourly = web_data["hourly"]
        current_time = current.get("time", "")

        forecast = []

        for i, time_value in enumerate(hourly["time"]):
            if time_value < current_time:
                continue

            forecast.append({
                "time": time_value.replace("T", " "),
                "temperature": hourly["temperature_2m"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "pressure": hourly["surface_pressure"][i]
            })

            if len(forecast) >= 24:
                break

        weather_error = None

    else:
        current_web = None
        forecast = []
        weather_error = (
            "Не удалось получить погоду. "
            "Проверьте интернет и терминал Python."
        )

    return jsonify({
        "current_web": current_web,
        "web_table": forecast,
        "chart_data": forecast,
        "local_table": local_records,
        "weather_error": weather_error
    })


if __name__ == "__main__":
    init_db()

    threading.Thread(
        target=start_mqtt_listener,
        daemon=True
    ).start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False
    )