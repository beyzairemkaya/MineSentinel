from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

class TelemetryInput(BaseModel):
    """
    Data contract for incoming sensor telemetry from ESP32 or simulation.
    Uses fail-safe default values for miner_id and zone to prevent dropping critical alarms.
    
    """
    gas_ppm:float=Field(...,ge=0.0,description="Ambient toxic/flammable gas level in PPM")
    accel_g:float=Field(...,ge=0.0,description="Total acceleration / impact magnitude in G")
    duration_sec:float=Field(...,ge=0.0,description="Persistence duration of the anomaly in seconds")
    miner_id: str = Field(default="UNKNOWN_DEVICE", description="Unique identifier for the miner helmet")
    zone: str = Field(default="UNKNOWN_ZONE", description="Mining sector/zone location")

    model_config= {
        "json_schema_extra":{
            "example":{
                "gas_ppm":850.0,
                "accel_g":4.2,
                "duration_sec": 6.0,
                "miner_id": "MINER-01",
                "zone": "Sector-4"

            }
        }
    }
class TelemetryResponse(BaseModel):
    """Data contract for the processed AI inference result returned to the client."""
    miner_id:str
    zone:str
    risk_level:str=Field(..., description="Predicted risk classification (LOW, MEDIUM, CRITICAL)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model prediction confidence score")
    class_probabilities: Dict[str, float] = Field(..., description="Probability distribution across classes")
    is_anomaly: bool = Field(..., description="Flag indicating whether the data point is an anomaly")
    rule_risk_score: float = Field(..., ge=0.0, le=100.0, description="Rule-based calculated risk score")
    emergency_report: Optional[str] = Field(default=None, description="LLM-generated Action Report for critical incidents")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC processing timestamp")
    action_required: bool = False