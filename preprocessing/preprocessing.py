import pandas as pd
import matplotlib.pyplot as plt

CSV_FILE = "../data/weather_data_cleaned.csv"

data = pd.read_csv(CSV_FILE)

print("================================")
print("MAIN SIGNALS VISUALIZATION")
print("================================")

print("\nDataset information:")
print(data[["temperature", "humidity"]].describe())

# Convert timestamp
data["timestamp"] = pd.to_datetime(data["timestamp"])

# Temperature visualization
plt.figure(figsize=(10, 5))
plt.plot(
    data["timestamp"],
    data["temperature"],
    marker="o"
)
plt.title("Temperature Over Time")
plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.xticks(rotation=45)
plt.grid()
plt.tight_layout()
plt.savefig("temperature_signal.png")
plt.close()

# Humidity visualization
plt.figure(figsize=(10, 5))
plt.plot(
    data["timestamp"],
    data["humidity"],
    marker="o"
)
plt.title("Humidity Over Time")
plt.xlabel("Time")
plt.ylabel("Humidity (%)")
plt.xticks(rotation=45)
plt.grid()
plt.tight_layout()
plt.savefig("humidity_signal.png")
plt.close()

print("\nVisualization completed!")
print("Graphs saved:")
print("- temperature_signal.png")
print("- humidity_signal.png")