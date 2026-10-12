import datetime
import sqlite3
import pandas as pd
import requests  # Сайттан дерек алу үшін кітапхана
from sklearn.linear_model import LinearRegression

print("1. Интернеттегі ауа райы сайтынан (API) деректер алынуда...")

# Open-Meteo тегін ауа райы API (Мысалы, Алматы координаталары: Кеңдік 43.25, Бойлық 76.95)
url = "https://api.open-meteo.com/v1/forecast?latitude=43.25&longitude=76.95&current=temperature_2m,relative_humidity_2m,surface_pressure&hourly=temperature_2m,relative_humidity_2m,surface_pressure"

try:
  response = requests.get(url)
  web_data = response.json()

  # Сайттан келген ағымдағы көрсеткіштер
  web_temp = web_data["current"]["temperature_2m"]
  web_hum = web_data["current"]["relative_humidity_2m"]
  web_press = web_data["current"]["surface_pressure"]

  print(
      f"   [САЙТҚАҢ ALYNDY] Температура: {web_temp}°C | Қысым: {web_press} hPa"
      f" | Ылғалдылық: {web_hum}%"
  )
except Exception as e:
  print(f"   [ЕСКЕРТУ] Сайттан дерек алу мүмкін болмады: {e}")
  web_temp, web_hum, web_press = 25.0, 50.0, 1013.0  # Қосалқы мән

print(
    "\n2. Жергілікті IoT датчиктерінен (Wokwi базасынан) деректер оқылуда..."
)
DB_NAME = "weather_data.db"

try:
  conn = sqlite3.connect(DB_NAME)
  df = pd.read_sql_query(
      "SELECT timestamp, temperature, humidity, pressure FROM telemetry", conn
  )
  conn.close()
  print(f"   [IOT БАЗАСЫ] Жинақталған жазбалар саны: {len(df)}")
except Exception as e:
  print(f"   [ЕСКЕРТУ] Базадан оқу қатесі: {e}")
  # Егер база бос болса, сайт деректерін база ретінде қолданамыз
  df = pd.DataFrame({
      "timestamp": [str(datetime.datetime.now())],
      "temperature": [web_temp],
      "humidity": [web_hum],
      "pressure": [web_press],
  })

# Модельді оқыту және алдағы сағаттарға болжау
df["temp_lag1"] = df["temperature"].shift(1)
df = df.dropna()

if len(df) < 3:
  # Егер дерек аз болса, сайттың ағымдағы мәніне сүйеніп жалған тарихи қатар жасаймыз
  df = pd.DataFrame({
      "timestamp": ["1", "2", "3"],
      "temperature": [web_temp - 1, web_temp - 0.5, web_temp],
      "humidity": [web_hum, web_hum, web_hum],
      "pressure": [web_press + 2, web_press + 1, web_press],
      "temp_lag1": [web_temp - 2, web_temp - 1, web_temp - 0.5],
  })

X = df[["temp_lag1", "humidity", "pressure"]]
y_temp = df["temperature"]
y_hum = df["humidity"]
y_press = df["pressure"]

model_temp = LinearRegression().fit(X, y_temp)
model_hum = LinearRegression().fit(X, y_hum)
model_press = LinearRegression().fit(X, y_press)

last_row = X.tail(1)
curr_temp = web_temp
curr_press = web_press

print("\n" + "=" * 55)
print("   ГИБРИДТІ ЖҮЙЕ: САҒАТ САЙЫНҒЫ БОЛЖАМ (САЙТ + IOT)")
print("=" * 55)
print(
    f"Ағымдағы нақты жағдай: {curr_temp}°C | Қысым: {curr_press} hPa |"
    f" Ылғалдылық: {web_hum}%\n"
)

current_time = datetime.datetime.now()

for i in range(1, 6):
  future_time = current_time + datetime.timedelta(hours=i)
  time_str = future_time.strftime("%H:00")

  pred_temp = model_temp.predict(last_row)[0]
  pred_hum = model_hum.predict(last_row)[0]
  pred_press = model_press.predict(last_row)[0]

  # Ауа райын болжау логикасы (қысымға қарап)
  pressure_diff = pred_press - curr_press
  if pressure_diff < -1.0:
    weather_condition = "🌧️ Жаңбыр жаууы мүмкін (Қысым төмендеуде)"
  elif pressure_diff > 1.0:
    weather_condition = "☀️ Ашық күн, күн шығады (Қысым көтерілуде)"
  else:
    weather_condition = "⛅ Бұлтты / Тұрақты ауа райы"

  print(f"🕒 Сағат {time_str} болжамы:")
  print(f"   • Температура : {pred_temp:.2f} °C")
  print(f"   • Қысым       : {pred_press:.2f} hPa")
  print(f"   • Ылғалдылық  : {pred_hum:.2f} %")
  print(f"   • Ауа күйі    : {weather_condition}")
  print("-" * 55)

  last_row = pd.DataFrame(
      [[pred_temp, pred_hum, pred_press]],
      columns=["temp_lag1", "humidity", "pressure"],
  )
  curr_press = pred_press