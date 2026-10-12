import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split

DB_NAME = "weather_data.db"

print("[INFO] Деректер базасынан мәліметтер оқылуда...")

# 1. Деректер базасынан мәліметтерді оқып алу
try:
  conn = sqlite3.connect(DB_NAME)
  df = pd.read_sql_query(
      "SELECT timestamp, temperature, humidity, pressure FROM telemetry", conn
  )
  conn.close()
except Exception as e:
  print(f"[ҚАТЕ] Базадан оқу кезінде қате шықты: {e}")
  exit()

print(f"Жинақталған барлық жазбалар саны: {len(df)}")

# 2. Модельді оқыту үшін шарт (кем дегенде 5-10 жазба қажет)
if len(df) >= 5:
  # Алдыңғы уақыттағы температураны кіріс белгі (Lag feature) етіп аламыз
  df["temp_lag1"] = df["temperature"].shift(1)
  df = df.dropna()

  if len(df) < 3:
    print(
        "[ЕСКЕРТУ] Деректер өңделгеннен кейін модель үшін әлі де аз болып"
        " тұр. Біраз уақыт күтіңіз."
    )
    exit()

  # Кіріс айнымалылар (Features) және Мақсатты айнымалы (Target)
  X = df[["temp_lag1", "humidity", "pressure"]]
  y = df["temperature"]

  # Оқыту және тестілеу болып бөлу
  X_train, X_test, y_train, y_test = train_test_split(
      X, y, test_size=0.2, shuffle=False
  )

  # Сызықтық регрессия моделін құру және оқыту
  model = LinearRegression()
  model.fit(X_train, y_train)

  # Модельдің дәлдігін тексеру (R² score)
  score = model.score(X_test, y_test)
  print("\n" + "=" * 40)
  print("       МАШИНАЛЫҚ ОҚЫТУ МОДЕЛІНІҢ НӘТИЖЕСІ")
  print("=" * 40)
  print(f"Модельдің дәлдік көрсеткіші (R² Score): {score:.2f}")

  # Соңғы келген деректер арқылы алдағы мәнді болжау
  last_row = X.tail(1)
  prediction = model.predict(last_row)
  print(f"🌡️ Болжанған келесі температура көрсеткіші: {prediction[0]:.2f} °C")
  print("=" * 40)

else:
  print(
      "[ЕСКЕРТУ] Модельді оқыту үшін деректер әлі аз (кем дегенде 5-10 жазба"
      " қажет)."
  )
  print(
      "Wokwi мен receiver.py жұмыс істеп тұрған кезде біраз уақыт дерек"
      " жинаңыз."
  )