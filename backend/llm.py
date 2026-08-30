import os
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
API_URL = "https://api.groq.com/openai/v1/chat/completions"


def generate_emergency_report(
    gas_ppm: float, 
    accel_g: float, 
    duration_sec: float, 
    risk_level: str, 
    confidence: float
) -> str:
    """
    Generates a structured, professional Emergency Action Report using an LLM
    based on real-time sensor metrics and AI classifier outputs.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please check your .env configuration file.")

    system_prompt = (
        "You are an expert Underground Mining Safety and Incident Response Coordinator. "
        "Your task is to analyze real-time sensor telemetry and AI risk classification outputs "
        "to generate a concise, professional, and actionable Emergency Incident Report. "
        "Your response MUST be entirely in English, highly structured, objective, and focused "
        "directly on life safety and immediate mitigation steps without conversational filler."
    )

    user_prompt = f"""
[TELEMETRY & RISK CLASSIFICATION DATA]
- Ambient Gas Concentration (CH4 / CO): {gas_ppm:.1f} PPM
- Acceleration / Impact Magnitude: {accel_g:.2f} g
- Event Persistence Duration: {duration_sec:.1f} seconds
- Predicted Risk Level: {risk_level}
- Model Confidence: {confidence * 100:.1f}%

Generate a structured emergency incident report with the following exact Markdown sections:
1. INCIDENT SEVERITY & ROOT CAUSE ASSESSMENT (Brief evaluation of the hazard type, threshold breaches, and worker condition)
2. IMMEDIATE OPERATIONAL ACTIONS (Step-by-step instructions for the control room operator and shift supervisor)
3. EVACUATION & LIFE SAFETY PROTOCOLS (Automated ventilation control, alarm triggering, and search & rescue deployment)
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 500
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    except requests.exceptions.HTTPError as http_err:
        raise RuntimeError(f"API HTTP Error ({response.status_code}): {response.text}") from http_err
    except requests.exceptions.Timeout as timeout_err:
        raise TimeoutError("LLM API request timed out after 10 seconds.") from timeout_err
    except requests.exceptions.RequestException as req_err:
        raise RuntimeError(f"Network error during LLM API call: {req_err}") from req_err
    except (KeyError, IndexError) as parse_err:
        raise ValueError(f"Failed to parse LLM API response: {parse_err}") from parse_err


if __name__ == "__main__":
    print("Testing Groq LLM Emergency Report Generator...\n")
    
    # Critical incident simulation
    sample_report = generate_emergency_report(
        gas_ppm=850.0,
        accel_g=4.2,
        duration_sec=6.0,
        risk_level="CRITICAL",
        confidence=0.99
    )
    
    print("--- GENERATED EMERGENCY REPORT ---\n")
    print(sample_report)