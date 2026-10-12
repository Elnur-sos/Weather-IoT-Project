import datetime
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression

DB_NAME = "weather_data.db"

print("[INFO] Деректер базасынан соңғы мәліметтер оқылуда...")

try:
  conn = sqlite3.connect(DB_NAME)
  df = pd.read_sql_query(
      "SELECT timestamp, temperature, humidity, pressure FROM telemetry", conn
  )
  conn.close()
except Exception as e:
  print(f"[ҚАТЕ] Базадан оқу қатесі: {e}")
  exit()

if len(df) < 5:
  print(
      "[ЕСКЕРТУ] Болжам жасау үшін деректер әлі аз. Wokwi симуляторын біраз"
      " уақыт қосып қойыңыз."
  )
  exit()

# Модельді дайындау
df["temp_lag1"] = df["temperature"].shift(1)
df = df.dropna()

X = df[["temp_lag1", "humidity", "pressure"]]
y_temp = df["temperature"]
y_hum = df["humidity"]
y_press = df["pressure"]

# Модельдерді оқыту
model_temp = LinearRegression().fit(X, y_temp)
model_hum = LinearRegression().fit(X, y_hum)
model_press = LinearRegression().fit(X, y_press)

# Соңғы көрсеткіштерді аламыз
last_row = X.tail(1)
curr_temp = df["temperature"].iloc[-1]
curr_press = df["pressure"].iloc[-1]
curr_hum = df["humidity"].iloc[-1]

print("\n" + "=" * 50)
print("       АУА РАЙЫН САҒАТ САЙЫН БОЛЖАУ ЖҮЙЕСІ")
print("=" * 50)
print(
    f"Ағымдағы жағдай: Температура: {curr_temp:.1f}°C | Қысым:"
    f" {curr_press:.1f} hPa | Ылғалдылық: {curr_hum:.1f}%\n"
)

# Ағымдағы уақыттан бастап алдағы 4 сағатқа болжам жасау
current_time = datetime.datetime.now()

for i in range(1, 5):
  future_time = current_time + datetime.timedelta(hours=i)
  time_str = future_time.strftime("%H:00")

  pred_temp = model_temp.predict(last_row)[0]
  pred_hum = model_hum.predict(last_row)[0]
  pred_press = model_press.predict(last_row)[0]

  # Қысымның өзгеруіне қарап ауа райын анықтау
  pressure_diff = pred_press - curr_press
  if pressure_diff < -1.0:
    weather_condition = "🌧️ Жаңбыр жаууы мүмкін (Қысым төмендеуде)"
  elif pressure_diff > 1.0:
    weather_condition = "☀️ Ашық күн, күн шығады (Қысым көтерілуде)"
  else:
    weather_condition = "⛅ Бұлтты / Тұрақты ауа райы"

  print(f"🕒 Сағат {time_str}:")
  print(f"   • Температура : {pred_temp:.2f} °C")
  print(f"   • Қысым       : {pred_press:.2f} hPa")
  print(f"   • Ылғалдылық  : {pred_hum:.2f} %")
  print(f"   • Болжам      : {weather_condition}")
  print("-" * 50)

  last_row = pd.DataFrame(
      [[pred_temp, pred_hum, pred_press]],
      columns=["temp_lag1", "humidity", "pressure"],
  )
  curr_press = pred_press