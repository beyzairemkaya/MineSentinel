import matplotlib.pyplot as plt
import pandas as pd 
import seaborn as sns
from pathlib import Path


# Uploading Data
BASE_DIR = Path(__file__).resolve().parent.parent
data_path=BASE_DIR/"data"/"processed_sensor_data.csv"
df=pd.read_csv(data_path)
print(df.head())
df.info()

# This shows the percentage distribution of risk levels:
print(df["risk_level"].value_counts(normalize=True) * 100)

# Drawing Scatter PLot
plt.figure(figsize=(10,6))
sns.scatterplot(data=df,x="gas_ppm",y="accel_g",hue="risk_level")
plt.title("Sensor Data Risk Distribution (Gas vs. Acceleration)")
plt.xlabel("Gaz (PPM)")
plt.ylabel("Acceleration (g)")
plt.show()


