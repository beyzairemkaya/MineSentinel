import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

# Add project root directory to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from backend.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient instance for issuing synchronous HTTP requests."""
    with TestClient(app) as test_client:
        yield test_client


# --- Telemetry Ingestion Tests ---

# --- Telemetry Ingestion Tests ---

def test_telemetry_post_success(client):
    """Test receiving valid telemetry payload and verifying response schema."""
    payload = {
        "miner_id": "MINER-01",
        "zone": "Sector-3",
        "gas_ppm": 210.5,
        "accel_g": 1.02,
        "duration_sec": 0.0
    }
    
    response = client.post("/api/telemetry", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    # 'status' yerine API'nin gerçekten döndürdüğü anahtarları kontrol ediyoruz:
    assert "miner_id" in data
    assert "risk_level" in data
    assert data["risk_level"] in ["LOW", "MEDIUM", "CRITICAL"]
    assert "confidence" in data


# --- Dashboard Data Retrieval Tests ---

def test_get_dashboard_data(client):
    """Test retrieving the dashboard telemetry buffer."""
    response = client.get("/api/dashboard-data")
    
    assert response.status_code == 200
    data = response.json()
    
    # API'nin gerçekten döndürdüğü 'telemetry_history' listesini doğrula
    assert "telemetry_history" in data
    assert isinstance(data["telemetry_history"], list)


def test_telemetry_critical_triggers_background_task(client):
    """Ensure CRITICAL risk payload triggers the emergency background task."""
    critical_payload = {
        "miner_id": "MINER-01",
        "zone": "Sector-3",
        "gas_ppm": 880.0,
        "accel_g": 5.4,
        "duration_sec": 8.0
    }

    # Mock the background LLM task to avoid network overhead or API quota consumption during testing
    with patch("backend.main.background_llm_task") as mock_llm_task:
        response = client.post("/api/telemetry", json=critical_payload)
        
        assert response.status_code == 200
        assert response.json()["risk_level"] == "CRITICAL"
        mock_llm_task.assert_called_once()


def test_telemetry_invalid_payload_validation(client):
    """Ensure malformed or missing fields trigger HTTP 422 Unprocessable Entity."""
    incomplete_payload = {
        "miner_id": "MINER-01",
        # missing gas_ppm, accel_g, zone, duration_sec
    }
    
    response = client.post("/api/telemetry", json=incomplete_payload)
    assert response.status_code == 422


