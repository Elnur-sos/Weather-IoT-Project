from datetime import datetime
import os
import sqlite3
import pandas as pd
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)


def get_local_db():
  try:
    db_path = r"C:\Users\Huawe\OneDrive\Рабочий стол\Weather-IoT-Project\mqtt\weather_data.db"
    if not os.path.exists(db_path):
      db_path = "weather_data.db"

    conn = sqlite3.connect(db_path, timeout=5)
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
    res = requests.get(url).json()
    return res
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

  current_web = {"temperature": 0, "humidity": 0, "pressure": 0, "time": "Жоқ"}
  web_hourly_list = []

  if web_data and "current" in web_data:
    curr = web_data["current"]
    current_web = {
        "temperature": curr.get("temperature_2m", 0),
        "humidity": curr.get("relative_humidity_2m", 0),
        "pressure": curr.get("surface_pressure", 0),
        "time": "Қазіргі сәт (Open-Meteo)",
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
      # Әр сағат сайын әртүрлі динамика беру (ашық, бұлтты және жаңбыр алмасып тұруы үшін)
      if step in [1, 4]:
        current_t += 0.3
        current_h -= 10  # Ылғал төмен -> Ашық күн
        current_p += 1.0
      elif step in [2, 5]:
        current_t -= 0.2
        current_h += 15  # Ылғал орташа -> Бұлтты
        current_p -= 1.5
      else:
        current_t += 0.1
        current_h += 25  # Ылғал өте жоғары -> Жаңбыр
        current_p -= 2.5

      # Ылғалдылықты 10 бен 100 аралығында шектеу
      current_h = max(10, min(100, current_h))
      p_diff = current_p - last_p

      # Статустарды анықтау шарттары
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
    app.run(host="0.0.0.0", port=5000, debug=True)