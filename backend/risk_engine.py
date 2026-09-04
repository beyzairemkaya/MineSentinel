import numpy as np
import pandas as pd
from pathlib import Path

class RiskEngine:
    THRESHOLD_LOW = 30.0
    THRESHOLD_CRITICAL = 70.0
    def __init__(self,w_gas=0.40,w_accel=0.40,w_duration=0.20):
        assert np.isclose(w_gas + w_accel + w_duration, 1.0), "Total Weight must be equal to 1.0"
        self.w_gas=w_gas
        self.w_accel=w_accel
        self.w_duration=w_duration
    def normalize_gas(self,gas):
        return float(np.clip((gas-150)/850,0.0,1.0))
    
    def normalize_acceleration(self,acc):
        return float(np.clip((abs(acc-1))/4,0.0,1.0))
        
    def normalize_duration(self, durr):
        return float(np.clip(durr/10,0.0,1.0))

    def calculate_risk_score(self,gas,acc,durr):
        gas_risk=self.normalize_gas(gas)*self.w_gas
        accel_risk=self.normalize_acceleration(acc)*self.w_accel
        durr_risk=self.normalize_duration(durr)*self.w_duration
        risk=(gas_risk+accel_risk+durr_risk)*100
        is_completely_still = abs(acc - 1.0) <= 0.08
        if is_completely_still and durr >= 10.0:
            risk = max(risk, 75.0)
        return round(risk,2)

    def evaluate_risk_level(self,risk):
        if risk < RiskEngine.THRESHOLD_LOW:
            risk_level="LOW"
        elif risk<RiskEngine.THRESHOLD_CRITICAL:
            risk_level="MEDIUM"
        else:
            risk_level="CRITICAL"
        return risk_level

if __name__=="__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_PATH = BASE_DIR / "data" / "sample_sensor_data.csv"
    df = pd.read_csv(DATA_PATH)
    r_eng=RiskEngine()
    
    df["risk_score"] = df.apply(lambda row: r_eng.calculate_risk_score(row["gas_ppm"], row["accel_g"], row["duration_sec"]), axis=1)
    df["risk_level"] = df["risk_score"].apply(r_eng.evaluate_risk_level)
    df.to_csv("../data/processed_sensor_data.csv", index=False)
    

