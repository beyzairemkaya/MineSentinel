from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from backend.schemas import TelemetryInput, TelemetryResponse
from backend.risk_engine import RiskEngine
from backend.anomaly import AnomalyDetector
from backend.classifier import RiskClassifier
from backend.llm import generate_emergency_report

BASE_DIR = Path(__file__).resolve().parent.parent
ANOMALY_MODEL_PATH = BASE_DIR / "models" / "anomaly_detector.joblib"
CLASSIFIER_MODEL_PATH = BASE_DIR / "models" / "risk_classifier.joblib"

# Global model references
anomaly_detector = AnomalyDetector()
risk_classifier = RiskClassifier()
risk_engine = RiskEngine()

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
def process_telemetry(payload: TelemetryInput):
    """
    Ingests sensor data from ESP32/simulation, runs inference through
    RiskEngine, AnomalyDetector, and Classifier, and triggers LLM on critical events.
    """
    try:
        rule_score=risk_engine.calculate_risk_score(
            gas=payload.gas_ppm,
            acc=payload.accel_g,
            durr=payload.duration_sec,
        )
        is_anomaly=anomaly_detector.predict_single(payload.gas_ppm,payload.accel_g,payload.duration_sec)
        predicted_risk, confidence, probabilities=risk_classifier.predict_single(payload.gas_ppm,payload.accel_g,payload.duration_sec)
        emergency_report=None
        if predicted_risk=="CRITICAL":
            emergency_report=generate_emergency_report(
                gas_ppm=payload.gas_ppm,
                accel_g=payload.accel_g,
                duration_sec=payload.duration_sec,
                risk_level=predicted_risk,
                confidence=confidence

                )
        return TelemetryResponse(
            miner_id=payload.miner_id,
            zone=payload.zone,
            risk_level=predicted_risk,
            confidence=confidence,
            class_probabilities=probabilities,
            is_anomaly=is_anomaly,
            rule_risk_score=rule_score,
            emergency_report=emergency_report
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")
