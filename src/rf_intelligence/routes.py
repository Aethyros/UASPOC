from fastapi import APIRouter, Query
from datetime import datetime

from .generator import synthesize_rf_wave, synthesize_fhss_wave
from .database import query_signature_by_frequency, query_signature_by_telemetry

router = APIRouter(
    prefix="/api/rf",
    tags=["RF Detection & Signal Intelligence"]
)

@router.get("/simulate")
def get_raw_simulation_stream(profile: str = Query("dji_phantom_4", description="Threat profile key")):
    """INGESTION: Delivers raw noisy float arrays to Signal Processing."""
    waveform = synthesize_rf_wave(profile_type=profile, num_samples=128)
    
    freq_map = {"dji_phantom_4": 2.400, "generic_fpv": 5.800, "parrot_bebop": 2.410}
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "center_frequency_ghz": freq_map.get(profile, 2.400),
        "carrier_wave_raw": waveform
    }

@router.get("/detect")
def execute_live_rf_threat_detection(
    intercepted_freq_ghz: float = Query(2.402, description="Current physical frequency caught by SDR"),
    packet_len: int = Query(256, description="TELEMETRY: Intercepted packet length in bytes"),
    symbol_rate: float = Query(10.00, description="TELEMETRY: Intercepted symbol rate in Mbps")
):
    """CLASSIFICATION: Identifies threats using advanced Telemetry tracking (immune to FHSS)."""
    
    # 1. Radio down to the Database Bouncer using the unbreakable telemetry fingerprints
    db_match = query_signature_by_telemetry(packet_len, symbol_rate)

    # SCENARIO A: No match found (Civilian air traffic)
    if not db_match:
        return {
            "status": "success",
            "threat_detected": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "intelligence_report": {
                "assessment": "CLEAR - Unrecognized telemetry signature."
            }
        }

    # SCENARIO B: TARGET ACQUIRED! 
    # Because we matched on packet size, we know EXACTLY what drone this is, 
    # even if its frequency is currently hopping wildly out of bounds!
    
    ground_truth_freq = float(db_match["center_freq_ghz"])
    frequency_drift = abs(intercepted_freq_ghz - ground_truth_freq)
    
    # If the drone is hopping, the drift will be massive. 
    # Our Confidence Score is now heavily bolstered by the telemetry match!
    is_hopping = frequency_drift > 0.05
    confidence = 99.9 if not is_hopping else 85.0 # We drop to 85% if we detect evasive hopping maneuvers

    # Synthesize the visual oscilloscope heartbeat
    profile_slug = "dji_phantom_4" if "DJI" in db_match["target_model"] else "generic_fpv"
    live_heartbeat = synthesize_rf_wave(profile_type=profile_slug, num_samples=32)

    return {
        "status": "success",
        "threat_detected": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "intelligence_report": {
            "target_lock": {
                "drone_model": db_match["target_model"],
                "intercepted_freq_ghz": intercepted_freq_ghz,
                "evasive_hopping_detected": is_hopping,
                "confidence_score_pct": confidence
            },
            "telemetry_match": {
                "matched_packet_length": packet_len,
                "matched_symbol_rate": symbol_rate
            },
            "countermeasure_authorized": db_match["countermeasure"],
            "live_telemetry_heartbeat": live_heartbeat
        }
    }

@router.get("/simulate/military")
def simulate_evasive_fhss_drone(
    base_freq: float = Query(5.800, description="Center frequency for the custom FPV attack drone"),
    hops: int = Query(5, description="Number of frequency hops to generate")
):
    """Generates complex Frequency-Hopping waveforms to test advanced tracking."""
    
    fhss_packet = synthesize_fhss_wave(base_freq_ghz=base_freq, num_hops=hops)
    
    return {
        "status": "success",
        "threat_class": "Military / Evasive",
        "intelligence_report": {
            "evasion_tactic": "Frequency-Hopping Spread Spectrum (FHSS)",
            "telemetry": fhss_packet
        }
    }