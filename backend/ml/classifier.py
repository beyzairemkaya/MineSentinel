from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from pathlib import Path
import pandas as pd
import numpy as np

class RiskClassifier:
    def __init__(self,random_state=42):
        self.random_state=random_state
        self.model=RandomForestClassifier(
            n_estimators=100,
            class_weight="balanced",
            random_state=self.random_state,
            )
        self.is_fitted = False

    def fit(self,X_train,y_train):
        self.model.fit(X_train,y_train)
        self.is_fitted = True
    def predict(self, X):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. The fit() function must be called first.")
        return self.model.predict(X)

    def predict_proba(self, X):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. The fit() function must be called first.")
        return self.model.predict_proba(X)

    def predict_single(self, gas: float, accel: float, durr: float):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. Call load_model() or fit() first.")
        
        sample = np.array([[gas, accel, durr]])
        prediction = self.model.predict(sample)[0]
        
        proba_values = self.model.predict_proba(sample)[0]
        classes = self.model.classes_
        probabilities = {str(cls): float(prob) for cls, prob in zip(classes, proba_values)}
        
        confidence = float(np.max(proba_values))
        
        return prediction, confidence, probabilities

    def save_model(self, filepath):
        if not self.is_fitted:
            raise ValueError("The model has not been trained yet. The fit() function must be called first.")
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, filepath)
        print(f"The model was successfully registered: {filepath}")

    def load_model(self, filepath):
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Model dosyası bulunamadı: {filepath}")
        self.model = joblib.load(filepath)
        self.is_fitted = True
        print(f"The model was successfully registered: {filepath}")


if __name__=="__main__":
    
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    data_path=BASE_DIR/"data"/"processed_sensor_data.csv"
    model_path = BASE_DIR / "models" / "risk_classifier.joblib"

    # 1 Uploading Data
    df=pd.read_csv(data_path)
    X = df[["gas_ppm", "accel_g", "duration_sec"]]
    y=df["risk_level"]

    # 2 Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42,stratify=y)

    # 3 Model Traning 
    clf = RiskClassifier()
    clf.fit(X_train, y_train)

    # 4 Evaluation
    y_pred = clf.predict(X_test)

    print("--- Confusion Matrix  ---")
    print(confusion_matrix(y_test, y_pred))

    print("\n--- Classification Report  ---")
    print(classification_report(y_test, y_pred))

    # 5 Save the model
    clf.save_model(model_path)
    
    # 6 Test the saved model
    test_clf = RiskClassifier()
    test_clf.load_model(model_path)
    pred, confidence, probs = test_clf.predict_single(gas=850, accel=4.2, durr=6)
    print(f"\nLive Test Prediction: {pred} (confidence: {confidence:.2f})")
    print(f"Class Probabilities: {probs}")





