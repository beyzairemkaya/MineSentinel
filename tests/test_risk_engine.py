import sys
from pathlib import Path
import pytest

# Add project root directory to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from backend.risk_engine import RiskEngine


@pytest.fixture
def risk_engine():
    return RiskEngine()


def test_calculate_risk_score_standard(risk_engine):
    """Test standard risk score calculation under nominal hazardous input."""
    # 235 ppm gas (0.10) + 6g accel (clipped to 1.0) + 8s duration (0.80) -> Score: 60.0
    assert risk_engine.calculate_risk_score(235, 6, 8) == 60.0


def test_calculate_risk_score_boundaries(risk_engine):
    """Test min and max boundary limit conditions."""
    # Baseline normal values (ambient air): 150 ppm gas, 1.0g gravity, 0s duration
    assert risk_engine.calculate_risk_score(150, 1.0, 0.0) == 0.0

    # Upper bound values (maximum disaster): 1000 ppm gas, 6.0g accel, 10s duration
    assert risk_engine.calculate_risk_score(1000, 6.0, 10.0) == 100.0


def test_calculate_risk_score_stillness_rule(risk_engine):
    """Test immobility / man-down rule threshold (minimum 75.0 floor)."""
    # Baseline gas (150 ppm), static gravity (1.0g), duration >= 10 seconds
    score = risk_engine.calculate_risk_score(150, 1.0, 10.5)
    assert score >= 75.0


def test_evaluate_risk_level_boundaries(risk_engine):
    """Test classification boundaries for LOW, MEDIUM, and CRITICAL brackets."""
    low_th = RiskEngine.THRESHOLD_LOW
    crit_th = RiskEngine.THRESHOLD_CRITICAL

    # LOW region (risk < THRESHOLD_LOW)
    assert risk_engine.evaluate_risk_level(low_th - 0.1) == "LOW"

    # Edge of MEDIUM region (risk == THRESHOLD_LOW)
    assert risk_engine.evaluate_risk_level(low_th) == "MEDIUM"

    # Mid-range MEDIUM region
    assert risk_engine.evaluate_risk_level((low_th + crit_th) / 2) == "MEDIUM"

    
    assert risk_engine.evaluate_risk_level(crit_th) == "CRITICAL"

    # CRITICAL region (risk > THRESHOLD_CRITICAL)
    assert risk_engine.evaluate_risk_level(crit_th + 0.1) == "CRITICAL"