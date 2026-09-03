import sys
from pathlib import Path
import pytest

# Add project root directory to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from backend.ml.anomaly import AnomalyDetector
from backend.ml.classifier import RiskClassifier


@pytest.fixture(scope="module")
def anomaly_detector():
    """Load the pre-trained Isolation Forest anomaly detector from disk."""
    model_path = ROOT_DIR / "models" / "anomaly_detector.joblib"
    detector = AnomalyDetector()
    detector.load_model(model_path)
    return detector


@pytest.fixture(scope="module")
def risk_classifier():
    """Load the pre-trained Random Forest risk classifier from disk."""
    model_path = ROOT_DIR / "models" / "risk_classifier.joblib"
    classifier = RiskClassifier()
    classifier.load_model(model_path)
    return classifier


# --- Anomaly Detector Tests ---

def test_anomaly_detector_nominal_telemetry(anomaly_detector):
    """Ensure ambient baseline telemetry is classified as normal (False)."""
    # gas=180.0 ppm, accel=1.0g, durr=0.0s
    is_anomaly = anomaly_detector.predict_single(gas=180.0, accel=1.0, durr=0.0)
    
    assert isinstance(is_anomaly, bool)
    assert is_anomaly is False


def test_anomaly_detector_extreme_telemetry(anomaly_detector):
    """Ensure extreme/disaster telemetry triggers an anomaly flag (True)."""
    # gas=950.0 ppm, accel=7.5g, durr=30.0s
    is_anomaly = anomaly_detector.predict_single(gas=950.0, accel=7.5, durr=30.0)
    
    assert isinstance(is_anomaly, bool)
    assert is_anomaly is True


# --- Risk Classifier Tests ---

def test_risk_classifier_valid_labels_and_probabilities(risk_classifier):
    """Ensure the classifier outputs valid labels, confidence score, and probability distribution."""
    # gas=220.0 ppm, accel=1.05g, durr=0.0s
    label, confidence, proba_dict = risk_classifier.predict_single(gas=220.0, accel=1.05, durr=0.0)

    # Label validation
    assert label in ["LOW", "MEDIUM", "CRITICAL"]
    
    # Confidence bounds
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
    
    # Probability distribution consistency
    assert set(proba_dict.keys()) == {"LOW", "MEDIUM", "CRITICAL"}
    assert pytest.approx(sum(proba_dict.values()), abs=1e-4) == 1.0


def test_risk_classifier_critical_hazard_scenario(risk_classifier):
    """Ensure lethal gas combined with severe impact predicts CRITICAL."""
    # gas=850.0 ppm, accel=5.2g, durr=8.0s
    label, confidence, _ = risk_classifier.predict_single(gas=850.0, accel=5.2, durr=8.0)

    assert label == "CRITICAL"
    assert confidence > 0.60