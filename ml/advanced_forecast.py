import datetime
import sqlite3
import pandas as pd
import requests
from sklearn.linear_model import LinearRegression

print("=" * 60)
print("       КЕШЕНДІ АУА РАЙЫН ТАЛДАУ ЖӘНЕ БОЛЖАУ ЖҮЙЕСІ")
print("=" * 60)

# --- 1. ЖЕРГІЛІКТІ IOT ДАТЧИККЕРІНЕН (WOKWI) ДЕРЕКТІ ОҚУ ---
DB_NAME = "weather_data.db"
local_df = pd.DataFrame()
try:
  conn = sqlite3.connect(DB_NAME)
  local_df = pd.read_sql_query(
      "SELECT timestamp, temperature, humidity, pressure FROM telemetry", conn
  )
  conn.close()
  print(
      f"\n📡 [1. ЖЕРГІЛІКТІ IOT ДАТЧИК ДЕРЕКТЕРІ]: {len(local_df)} жазба табылды"
  )
  if not local_df.empty:
    print(local_df.tail(3).to_string(index=False))
except Exception as e:
  print(f"\n📡 [1. IOT ДАТЧИК ДЕРЕКТЕРІ]: База бос немесе қате: {e}")

# --- 2. ИНТЕРНЕТ САЙТЫНАН (API) ӨТКЕН ЖӘНЕ БОЛАШАҚ ДЕРЕКТЕРДІ АЛУ ---
print(
    "\n🌐 [2. ИНТЕРНЕТ САЙТЫНАН (Open-Meteo) МӘЛІМЕТТЕР АЛЫНУДАН...]"
)
url = "https://api.open-meteo.com/v1/forecast?latitude=43.25&longitude=76.95&current=temperature_2m,relative_humidity_2m,surface_pressure&hourly=temperature_2m,relative_humidity_2m,surface_pressure"

try:
  response = requests.get(url)
  web_data = response.json()

  times = web_data["hourly"]["time"]
  temps = web_data["hourly"]["temperature_2m"]
  hums = web_data["hourly"]["relative_humidity_2m"]
  pressures = web_data["hourly"]["surface_pressure"]

  # Қазіргі сағаттың индексін табу
  now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:00")
  current_idx = 0
  for idx, t in enumerate(times):
    if t >= now_str:
      current_idx = idx
      break

  # А) Өткен 1-2 сағаттағы деректер
  print("\n--- ⏳ ӨТКЕН 1-2 САҒАТ БҰРЫНҒЫ ЖАҒДАЙ ---")
  for i in range(2, 0, -1):
    past_idx = current_idx - i
    if past_idx >= 0:
      t_time = times[past_idx].split("T")[1]
      print(
          f"🕒 Сағат {t_time} | Температура: {temps[past_idx]}°C | Қысым:"
          f" {pressures[past_idx]} hPa | Ылғалдылық: {hums[past_idx]}%"
      )

  # Б) Дәл қазіргі жағдай
  curr_t = times[current_idx].split("T")[1]
  print(f"\n--- ⚡ ДӘЛ ҚАЗІРГІ ЖАҒДАЙ (Сағат {curr_t}) ---")
  print(
      f"Температура: {temps[current_idx]}°C | Қысым: {pressures[current_idx]} hPa"
      f" | Ылғалдылық: {hums[current_idx]}%"
  )

  # В) Алдағы 3-4 сағаттағы деректер
  print("\n--- 🔮 ИНТЕРНЕТ САЙТЫНДАҒЫ АЛДАҒЫ 3-4 САҒАТТЫҚ БОЛЖАМ ---")
  for i in range(1, 5):
    fut_idx = current_idx + i
    if fut_idx < len(times):
      f_time = times[fut_idx].split("T")[1]
      print(
          f"🕒 Сағат {f_time} | Температура: {temps[fut_idx]}°C | Қысым:"
          f" {pressures[fut_idx]} hPa | Ылғалдылық: {hums[fut_idx]}%"
      )

  # --- 3. МАШИНАЛЫҚ ОҚЫТУ АРҚЫЛЫ ӘР 1-2 САҒАТ САЙЫН ЖАҢАРТЫЛҒАН БОЛЖАМ ---
  print("\n" + "=" * 60)
  print("   🤖 МАШИНАЛЫҚ ОҚЫТУ (AI) АРҚЫЛЫ ЖЕКЕ БОЛЖАУ ТАЛДАУЫ")
  print("=" * 60)

  # Сайттың барлық сағаттық мәліметтерін оқыту үшін DataFrame жасаймыз
  train_df = pd.DataFrame({
      "temperature": temps,
      "humidity": hums,
      "pressure": pressures,
  })
  train_df["temp_lag1"] = train_df["temperature"].shift(1)
  train_df = train_df.dropna()

  X = train_df[["temp_lag1", "humidity", "pressure"]]
  y_t = train_df["temperature"]
  y_h = train_df["humidity"]
  y_p = train_df["pressure"]

  m_temp = LinearRegression().fit(X, y_t)
  m_hum = LinearRegression().fit(X, y_h)
  m_press = LinearRegression().fit(X, y_p)

  last_features = X.tail(1)
  last_press = pressures[current_idx]

  # Әр 2 сағат сайын болжам жасау (мысалы: +2 сағат, +4 сағат)
  for step in [2, 4]:
    fut_idx = current_idx + step
    if fut_idx < len(times):
      target_time = times[fut_idx].split("T")[1]

      pred_t = m_temp.predict(last_features)[0]
      pred_h = m_hum.predict(last_features)[0]
      pred_p = m_press.predict(last_features)[0]

      # Қысым өзгерісіне қарап ауа райын анықтау
      p_diff = pred_p - last_press
      if p_diff < -1.0:
        cond = "🌧️ Жаңбыр жаууы мүмкін (Қысым түсуде)"
      elif p_diff > 1.0:
        cond = "☀️ Ашық күн / Күн шығады (Қысым көтерілуде)"
      else:
        cond = "⛅ Бұлтты / Тұрақты ауа райы"

      print(f"\n🕒 Болжам уақыты: {target_time} (Әр 2 сағат сайын):")
      print(f"   • Болжанған температура : {pred_t:.2f} °C")
      print(f"   • Болжанған қысым       : {pred_p:.2f} hPa")
      print(f"   • Болжанған ылғалдылық  : {pred_h:.2f} %")
      print(f"   • Метео-талдау күйі     : {cond}")
      print("-" * 50)

      last_features = pd.DataFrame(
          [[pred_t, pred_h, pred_p]],
          columns=["temp_lag1", "humidity", "pressure"],
      )
      last_press = pred_p

except Exception as e:
  print(f"[ҚАТЕ] Деректерді өңдеу барысында қате шықты: {e}")