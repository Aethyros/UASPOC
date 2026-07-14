from fastapi import APIRouter, Query
from datetime import datetime, timezone
import numpy as np
import math

from .generator import synthesize_rf_wave, synthesize_fhss_wave, RF_PROFILES
from .database import query_signature_by_frequency, query_signature_by_telemetry, insert_rf_simulation, get_recent_simulations

router = APIRouter(
    prefix="/api/rf",
    tags=["RF Detection & Signal Intelligence"]
)

DB_MODEL_TO_SLUG = {
    "DJI Phantom 4": "dji_phantom_4",
    "Parrot Bebop": "parrot_bebop",
    "DJI Matrice 300 RTK": "dji_matrice_300",
    "Skydio X2": "skydio_x2",
    "Autel EVO Max 4T": "autel_evo_max",
    "Generic Custom FPV": "generic_fpv",
    "TBS Crossfire FPV": "tbs_crossfire",
    "Holy Stone HS720E": "holy_stone",
}

# Reverse mapping: translates URL slugs back to exact PostgreSQL database model names
SLUG_TO_DB_MODEL = {v: k for k, v in DB_MODEL_TO_SLUG.items()}

def decimate_array(data_array, max_points=2048):
    """Downsamples large arrays for fast JSON serialization and UI rendering."""
    num_samples = len(data_array)
    if num_samples <= max_points:
        return data_array.tolist()
    
    # Calculate step size to slice down to max_points
    step = max(1, num_samples // max_points)
    return data_array[::step].tolist()


@router.get("/simulate")
def get_raw_simulation_stream(
    profile: str = Query(
        "dji_phantom_4",
        description="Threat profile slug. One of: " + ", ".join(RF_PROFILES.keys())
    ),
    is_fhss: bool = Query(
        False,
        description="Set to true to simulate military/evasive Frequency-Hopping Spread Spectrum (FHSS)"
    ),
    base_freq: float = Query(
        5.800,
        description="Center frequency for FHSS evasive drone (GHz)"
    ),
    hops: int = Query(
        4,
        description="Number of frequency hops for FHSS"
    )
):
    """
    UNIFIED INGESTION & SPECTRUM ENDPOINT: 
    Delivers synchronized time-domain waveforms and frequency-domain FFT spectrum data.
    Supports both standard commercial RF profiles and evasive military FHSS hopping.
    """
    if is_fhss:
        # Generate FHSS military waveform
        target_model_name = SLUG_TO_DB_MODEL.get(profile, "Autel EVO Max 4T")
        waveform_payload = synthesize_fhss_wave(base_freq_ghz=base_freq, num_hops=hops, target_model = target_model_name)
        # Handle whether synthesize_fhss_wave returns a list or structured dictionary
        if isinstance(waveform_payload, dict):
            waveform = waveform_payload.get("fhss_waveform", waveform_payload.get("waveform", []))
            center_freq_ghz = waveform_payload.get("base_freq_ghz", base_freq)
            bandwidth_mhz = waveform_payload.get("bandwidth_mhz", 40.0)
        else:
            waveform = waveform_payload
            center_freq_ghz = base_freq
            bandwidth_mhz = 40.0  # Default bandwidth window for FHSS hopping
        threat_class = "Military / Evasive"
    else:
        # Generate standard RF civilian waveform
        waveform_payload = synthesize_rf_wave(profile_type=profile, num_samples=1024)
        if isinstance(waveform_payload, dict):
            waveform = waveform_payload.get("waveform", [])
        else:
            waveform = waveform_payload
        
        profile_data = RF_PROFILES.get(profile, RF_PROFILES["dji_phantom_4"])
        center_freq_ghz = profile_data["center_freq_ghz"]
        bandwidth_mhz = profile_data["bandwidth_mhz"]
        threat_class = "Civilian / Commercial"

    raw_array = np.array(waveform)
    num_samples = len(raw_array)

    # Perform FFT directly on the synthesized waveform to prevent signal desynchronization
    fft_result = np.fft.fft(raw_array)
    fft_freq = np.fft.fftfreq(num_samples)

    # Filter positive frequencies only (negative side is a mathematical mirror)
    pos_mask = fft_freq > 0
    freqs = np.round(fft_freq[pos_mask], 4).tolist()
    magnitudes = np.round(np.abs(fft_result[pos_mask]), 4).tolist()

    # Ensure magnitudes are numpy arrays for math
    mag_array = np.array(magnitudes)
    
    # 1. Calculate Peak and Mean
    peak_magnitude = round(float(np.max(mag_array)), 4) if len(mag_array) > 0 else 0.0
    mean_magnitude = round(float(np.mean(mag_array)), 4) if len(mag_array) > 0 else 0.0
    
    # 2. Approximate Signal-to-Noise Ratio (SNR) in dB
    noise_floor = np.median(mag_array) if len(mag_array) > 0 else 0.0
    if noise_floor > 0:
        signal_to_noise = round(float(20 * np.log10(peak_magnitude / noise_floor)), 2)
    else:
        signal_to_noise = 0.0

    response_payload = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "threat_class": threat_class,
        "profile": profile,
        "is_fhss": is_fhss,
        
        # Strictly preserved required keys & exact mathematical formulas
        "center_frequency_ghz": center_freq_ghz,
        "bandwidth_mhz": bandwidth_mhz,
        "lowcut_frequency": center_freq_ghz - bandwidth_mhz/2000,
        "highcut_frequency": center_freq_ghz + bandwidth_mhz/2000,
        "sample_frequency": 2.5 * bandwidth_mhz/1000,
        
        # Synchronized Time domain — for oscilloscope panel
        "samples": min(num_samples, 2048),
        "carrier_wave_raw": decimate_array(raw_array, max_points=2048),
        
        # Synchronized Frequency domain — for spectrum analyser panel
        "frequency_domain": {
            "x_axis_frequencies": decimate_array(fft_freq[pos_mask], max_points=2048),
            "y_axis_magnitudes": decimate_array(np.abs(fft_result[pos_mask]), max_points=2048),
            "total_data_points": len(freqs),
        },
        # Summary metrics — for dashboard status bar widgets
        "metrics": {
            "peak_magnitude": peak_magnitude,
            "mean_magnitude": mean_magnitude,
            "signal_to_noise_ratio": signal_to_noise,
        },
    }

    try:
        insert_rf_simulation(response_payload)
        print(f"Successfully logged {profile} simulation to PostgreSQL.")
    except Exception as e:
        print(f"WARNING: Failed to log simulation to database: {e}")

    # Return the payload back to the FastAPI client
    return response_payload




@router.get("/detect")
def execute_live_rf_threat_detection(
    intercepted_freq_ghz: float = Query(2.402, description="Current physical frequency caught by SDR"),
    packet_len: int = Query(256, description="TELEMETRY: Intercepted packet length in bytes"),
    symbol_rate: float = Query(10.00, description="TELEMETRY: Intercepted symbol rate in Mbps")
):
    """CLASSIFICATION: Multi-Variate Threat Identification (Telemetry + Frequency)."""

    # 1. Query BOTH vectors independently
    telemetry_match = query_signature_by_telemetry(packet_len, symbol_rate)
    freq_match = query_signature_by_frequency(intercepted_freq_ghz)

    # SCENARIO A: No telemetry match — civilian / unknown traffic
    # Even if the frequency matches (e.g., generic 2.4GHz WiFi bleed), 
    # we don't flag a threat without a telemetry fingerprint lock.
    if not telemetry_match:
        return {
            "status": "success",
            "threat_detected": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intelligence_report": {
                "assessment": "CLEAR — Unrecognised telemetry signature.",
                "frequency_lookup_attempt": freq_match["target_model"] if freq_match else "None"
            }
        }

    # SCENARIO B: Target acquired via Telemetry (Ground Truth)
    db_match = telemetry_match
    ground_truth_freq = float(db_match["center_freq_ghz"])
    frequency_drift = abs(intercepted_freq_ghz - ground_truth_freq)
    
    # 2. Compare the two queries to determine alignment
    perfect_alignment = False
    if freq_match and freq_match["target_model"] == db_match["target_model"]:
        perfect_alignment = True

    # 3. Calculate Advanced Confidence Score using Gaussian Decay
    # Formula: Confidence = Base + (Max Bonus) * e^(-k * (Delta f)^2)
    base_confidence = 80.0
    max_bonus = 19.9
    decay_constant = 50.0  # Controls how fast the confidence drops as drift increases

    if perfect_alignment:
        # The ultimate lock: Telemetry and Frequency both point to the exact same drone
        confidence = 99.9
        is_hopping = False
    else:
        # Telemetry locked, but Frequency is drifting/mismatched (Evasive Maneuvers)
        confidence = base_confidence + (max_bonus * math.exp(-decay_constant * (frequency_drift ** 2)))
        is_hopping = frequency_drift > 0.05

    # Resolve the correct generator profile for this specific drone model
    profile_slug   = DB_MODEL_TO_SLUG.get(db_match["target_model"], "dji_phantom_4")
    live_heartbeat = synthesize_rf_wave(profile_type=profile_slug, num_samples=1024)
    if isinstance(live_heartbeat, dict):
        live_heartbeat = live_heartbeat.get("waveform", [])

    return {
        "status": "success",
        "threat_detected": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "intelligence_report": {
            "target_lock": {
                "drone_model": db_match["target_model"],
                "protocol_label": db_match["protocol_label"],
                "protocol_security": db_match["protocol_security"],
                "intercepted_freq_ghz": intercepted_freq_ghz,
                "ground_truth_freq_ghz": ground_truth_freq,
                "frequency_drift_ghz": round(frequency_drift, 4),
                "evasive_hopping_detected": is_hopping,
                "perfect_alignment": perfect_alignment,
                "confidence_score_pct": round(confidence, 2),
            },
            "telemetry_match": {
                "matched_packet_length": packet_len,
                "matched_symbol_rate": symbol_rate,
                "generator_profile": profile_slug,
            },
            "countermeasure_authorized": db_match["countermeasure"],
            "live_telemetry_heartbeat": live_heartbeat,
        }
    }

@router.get("/latest")
def get_latest_simulation(
    limit: int = Query(
        1, 
        ge=1, 
        le=100, 
        description="Number of recent simulations to retrieve (Max: 100)"
    )
):
    """
    Retrieves the most recent RF simulation runs from the PostgreSQL database.
    """
    try:
        simulations = get_recent_simulations(limit=limit)
        if not simulations:
            return {"status": "error", "message": "No simulations found. Please run /simulate first."}
        
        # Smart Return: 
        # If the client only asked for 1, return the flat dictionary (keeps visualizers working)
        if limit == 1:
            return simulations[0]
            
        # If they asked for more than 1, return the whole list
        return {"status": "success", "count": len(simulations), "data": simulations}
        
    except Exception as e:
        return {"status": "error", "message": f"Database retrieval failed: {str(e)}"}