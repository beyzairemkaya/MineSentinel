import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import IsolationForest
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
        return bool(prediction == -1) # return true if there is an anomaly
    def save_model(self, file_path: Path):
        if not self.is_fitted:
            raise ValueError("Cannot save an unfitted model!")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, file_path)
        print(f"Anomaly detector successfully saved to: {file_path}")

    def load_model(self, file_path: Path):
        if not file_path.exists():
            raise FileNotFoundError(f"Model file not found at: {file_path}")
        self.model = joblib.load(file_path)
        self.is_fitted = True
        print(f"Anomaly detector successfully loaded from: {file_path}")

if __name__=="__main__":
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    data_path=BASE_DIR/"data"/"processed_sensor_data.csv"
    model_path=BASE_DIR / "models" / "anomaly_detector.joblib"

    # Uploading Data
    df=pd.read_csv(data_path)
    X = df[["gas_ppm", "accel_g", "duration_sec"]]

    detector = AnomalyDetector()
    detector.fit(X)
    predictions=detector.predict(X)
    y_true = df["risk_level"].apply(lambda x: 1 if x == "LOW" else -1)

    # Evaluation
    print("--- Confusion Matrix ---")
    print(confusion_matrix(y_true, predictions))
    print("\n--- Classification Report ---")
    print(classification_report(y_true, predictions, target_names=["Anomali (-1)", "Normal (1)"]))

    # Save the model
    detector.save_model(model_path)
    test_detector = AnomalyDetector()
    test_detector.load_model(model_path)

    # test the model
    is_anom = test_detector.predict_single(850.0, 4.2, 6.0)
    print(f"\nSingle test anomaly result (Expected True): {is_anom}")

        
