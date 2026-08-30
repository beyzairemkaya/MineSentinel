import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix

class AnomalyDetector:
    def __init__(self,contamination=0.20,random_state=42):
        self.contamination=contamination
        self.random_state=random_state
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100
        )
        self.is_fitted = False

    def fit(self,X):
        self.model.fit(X)
        self.is_fitted=True

    def predict(self,X):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. The fit() function must be called first.")
        return self.model.predict(X)

    def predict_single(self, gas, accel, durr):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. The fit() function must be called first.")
        sample=np.array([[gas, accel, durr]])
        prediction = self.model.predict(sample)[0]
        return prediction == -1 # return true if there is an anomaly

if __name__=="__main__":
    # Uploading Data
    BASE_DIR = Path(__file__).resolve().parent.parent
    data_path=BASE_DIR/"data"/"processed_sensor_data.csv"
    df=pd.read_csv(data_path)
    X = df[["gas_ppm", "accel_g", "duration_sec"]]
    detector = AnomalyDetector()
    detector.fit(X)
    predictions=detector.predict(X)
    y_true = df["risk_level"].apply(lambda x: 1 if x == "LOW" else -1)
    print("--- Confusion Matrix ---")
    print(confusion_matrix(y_true, predictions))
    print("\n--- Classification Report ---")
    print(classification_report(y_true, predictions, target_names=["Anomali (-1)", "Normal (1)"]))

        
