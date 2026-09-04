from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from collections import deque

from backend.schemas import TelemetryInput, TelemetryResponse
from backend.risk_engine import RiskEngine
from backend.ml.anomaly import AnomalyDetector
from backend.ml.classifier import RiskClassifier
from backend.llm import generate_emergency_report
import time

BASE_DIR = Path(__file__).resolve().parent.parent
ANOMALY_MODEL_PATH = BASE_DIR / "models" / "anomaly_detector.joblib"
CLASSIFIER_MODEL_PATH = BASE_DIR / "models" / "risk_classifier.joblib"

# Global model references
anomaly_detector = AnomalyDetector()
risk_classifier = RiskClassifier()
risk_engine = RiskEngine()
telemetry_history = deque(maxlen=50)
latest_incident_report = {"report": None, "timestamp": None}
# Son LLM çağrısının zamanını tutan kilit değişkeni
last_llm_call_time = 0.0
LLM_COOLDOWN_SECONDS = 30.0  

def background_llm_task(gas_ppm: float, accel_g: float, duration_sec: float, risk_level: str, confidence: float):
    """LLM task function that runs in the background and does not block the main line"""
    global last_llm_call_time
    try:
        print("[*] Background LLM emergency report is being prepared...")
        report = generate_emergency_report(
            gas_ppm=gas_ppm,
            accel_g=accel_g,
            duration_sec=duration_sec,
            risk_level=risk_level,
            confidence=confidence
        )
        latest_incident_report["report"] = report
        latest_incident_report["timestamp"] = time.time()
        print("[+] LLM report prepared and saved!")
    except Exception as e:
        print(f"[-] Background LLM error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """The server loads the models when it starts and cleans up when it shuts down."""
    try:
        anomaly_detector.load_model(ANOMALY_MODEL_PATH)
        risk_classifier.load_model(CLASSIFIER_MODEL_PATH)
        print("AI models successfully loaded!")
    except Exception as e:
        print(f"Error loading models: {e}")
        raise RuntimeError("Models could not be loaded. Please ensure training scripts were run.")
    yield
    print("Shutting down MineSentinel API...")

app=FastAPI(
    title="MineSentinel API",
    description="Real-time Underground Mining Safety & AI Incident Management System",
    version="1.0.0",
    lifespan=lifespan,
)
@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "MineSentinel Safety Core",
        "version": "1.0.0"
    }
@app.post("/api/telemetry", response_model=TelemetryResponse)
def process_telemetry(payload: TelemetryInput, background_tasks: BackgroundTasks):
    """
    Ingests sensor data from ESP32/simulation, runs inference through
    RiskEngine, AnomalyDetector, and Classifier, and triggers LLM on critical events.
    """
    try:
        rule_score = risk_engine.calculate_risk_score(
            gas=payload.gas_ppm,
            acc=payload.accel_g,
            durr=payload.duration_sec,
        )
        is_anomaly = anomaly_detector.predict_single(payload.gas_ppm, payload.accel_g, payload.duration_sec)
        predicted_risk, confidence, probabilities = risk_classifier.predict_single(
            payload.gas_ppm, payload.accel_g, payload.duration_sec
        )

        # Pessimistic Safety Gating: Kural motoru ve ML kararlarından en yükseğini seç
        rule_level = "CRITICAL" if rule_score >= 70.0 else ("MEDIUM" if rule_score >= 30.0 else "LOW")
        severity_order = {"LOW": 1, "MEDIUM": 2, "CRITICAL": 3}
        
        final_risk = predicted_risk
        if severity_order[rule_level] > severity_order[predicted_risk]:
            final_risk = rule_level

        # Telemetri geçmişine tek ve nihai kayıt
        telemetry_history.append({
            "timestamp": time.time(),
            "gas_ppm": payload.gas_ppm,
            "accel_g": payload.accel_g,
            "duration_sec": payload.duration_sec,
            "risk_level": final_risk,
            "rule_risk_score": rule_score,
            "is_anomaly": is_anomaly
        })

        # Sadece nihai risk CRITICAL ise arka plan LLM çağrısını yap
        global last_llm_call_time
        current_time = time.time()

        if final_risk == "CRITICAL":
            if (current_time - last_llm_call_time) > LLM_COOLDOWN_SECONDS:
                last_llm_call_time = current_time
                background_tasks.add_task(
                    background_llm_task,
                    gas_ppm=payload.gas_ppm,
                    accel_g=payload.accel_g,
                    duration_sec=payload.duration_sec,
                    risk_level=final_risk,
                    confidence=confidence
                )
            else:
                print(f"[*] Lock active: {int(current_time - last_llm_call_time)}s elapsed. Cooldown active.")

        emergency_report = latest_incident_report.get("report")
        action_required = (final_risk != "LOW")
        
        return TelemetryResponse(
            miner_id=payload.miner_id,
            zone=payload.zone,
            risk_level=final_risk,
            confidence=confidence,
            class_probabilities=probabilities,
            is_anomaly=is_anomaly,
            rule_risk_score=rule_score,
            emergency_report=emergency_report,
            action_required=action_required
        )

    

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.get("/api/dashboard-data")
def get_dashboard_data():
    """Streamlit panel returns the latest telemetry history and LLM report."""
    return {
        "telemetry_history": list(telemetry_history),
        "latest_incident": latest_incident_report
    }
