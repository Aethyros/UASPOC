from fastapi import APIRouter, Query
from datetime import datetime, timezone
import numpy as np

from .generator import synthesize_rf_wave, synthesize_fhss_wave, RF_PROFILES
from .database import query_signature_by_frequency, query_signature_by_telemetry

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


@router.get("/simulate")
def get_raw_simulation_stream(
    profile: str = Query(
        "dji_phantom_4",
        description="Threat profile slug. One of: " + ", ".join(RF_PROFILES.keys())
    )
):
    """INGESTION: Delivers raw noisy float arrays to Signal Processing."""
    waveform = synthesize_rf_wave(profile_type=profile, num_samples=1024)

    # Pull freq directly from RF_PROFILES — no duplicate freq_map needed
    profile_data = RF_PROFILES.get(profile, RF_PROFILES["dji_phantom_4"])

    center_freq_ghz = profile_data["center_freq_ghz"]
    bandwidth_mhz = profile_data["bandwidth_mhz"]

    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "center_frequency_ghz": center_freq_ghz,
        "bandwidth_mhz": bandwidth_mhz,
        "carrier_wave_raw": waveform,
        "lowcut_frequency": center_freq_ghz - bandwidth_mhz/2000,
        "highcut_frequency": center_freq_ghz + bandwidth_mhz/2000,
        "sample_frequency": 2.5 * bandwidth_mhz/1000
    }


@router.get("/detect")
def execute_live_rf_threat_detection(
    intercepted_freq_ghz: float = Query(2.402, description="Current physical frequency caught by SDR"),
    packet_len: int = Query(256, description="TELEMETRY: Intercepted packet length in bytes"),
    symbol_rate: float = Query(10.00, description="TELEMETRY: Intercepted symbol rate in Mbps")
):
    """CLASSIFICATION: Identifies threats using telemetry fingerprinting (immune to FHSS)."""

    db_match = query_signature_by_telemetry(packet_len, symbol_rate)

    # SCENARIO A: No match — civilian / unknown traffic
    if not db_match:
        return {
            "status": "success",
            "threat_detected": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intelligence_report": {
                "assessment": "CLEAR — Unrecognised telemetry signature."
            }
        }

    # SCENARIO B: Target acquired
    # Because we matched on packet size, we know EXACTLY what drone this is, 
    # even if its frequency is currently hopping wildly out of bounds!

    ground_truth_freq = float(db_match["center_freq_ghz"])
    frequency_drift = abs(intercepted_freq_ghz - ground_truth_freq)

    # If the drone is hopping, the drift will be massive. 
    # Our Confidence Score is now heavily bolstered by the telemetry match!
    is_hopping = frequency_drift > 0.05
    confidence = 99.9 if not is_hopping else 85.0
    # We drop to 85% if we detect evasive hopping maneuvers

    # Resolve the correct generator profile for this specific drone model
    profile_slug   = DB_MODEL_TO_SLUG.get(db_match["target_model"], "dji_phantom_4")
    live_heartbeat = synthesize_rf_wave(profile_type=profile_slug, num_samples=1024)

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
                "confidence_score_pct": confidence,
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


@router.get("/simulate/military")
def simulate_evasive_fhss_drone(
    base_freq: float = Query(5.800, description="Center frequency for the evasive drone (GHz)"),
    hops: int = Query(4, description="Number of frequency hops to generate")
):
    """Generates complex FHSS multi-hop waveforms to stress-test advanced tracking."""
    fhss_packet = synthesize_fhss_wave(base_freq_ghz=base_freq, num_hops=hops)

    return {
        "status": "success",
        "threat_class": "Military / Evasive",
        "intelligence_report": {
            "evasion_tactic": "Frequency-Hopping Spread Spectrum (FHSS)",
            "telemetry": fhss_packet,
        }
    }


@router.get("/spectrum")
def get_frequency_spectrum(
    profile: str = Query(
        "dji_phantom_4",
        description="Threat profile slug. One of: " + ", ".join(RF_PROFILES.keys())
    )
):
    """
    Performs FFT on the raw waveform and returns
    frequency-domain data for dashboard visualisation and signal processing consumption.
    """
    waveform = synthesize_rf_wave(profile_type=profile, num_samples=128)
    raw_array = np.array(waveform)
    num_samples = len(raw_array)

    fft_result = np.fft.fft(raw_array)
    fft_freq = np.fft.fftfreq(num_samples)

    # Filter positive frequencies only (negative side is a mathematical mirror)
    pos_mask = fft_freq > 0
    freqs = np.round(fft_freq[pos_mask], 4).tolist()
    magnitudes = np.round(np.abs(fft_result[pos_mask]), 4).tolist()

    profile_data = RF_PROFILES.get(profile, RF_PROFILES["dji_phantom_4"])

    # Ensure magnitudes are numpy arrays for math
    mag_array = np.array(magnitudes)
    
    # 1. Calculate Peak and Mean
    peak_magnitude = round(float(np.max(mag_array)), 4)
    mean_magnitude = round(float(np.mean(mag_array)), 4)
    
    # 2. Approximate Signal-to-Noise Ratio (SNR) in dB
    # We use the median as a quick approximation of the noise floor
    noise_floor = np.median(mag_array)
    if noise_floor > 0:
        # Standard SNR formula: 10 * log10(Signal_Power / Noise_Power)
        # Since magnitudes are voltage/amplitude, we use 20 * log10
        signal_to_noise = round(float(20 * np.log10(peak_magnitude / noise_floor)), 2)
    else:
        signal_to_noise = 0.0

    return {
        "status":    "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile":   profile,
        "center_frequency_ghz": profile_data["center_freq_ghz"],
        "bandwidth_mhz":        profile_data["bandwidth_mhz"],
        # Time domain — for oscilloscope panel
        "time_domain": {
            "samples":      num_samples,
            "waveform":     waveform,
        },
        # Frequency domain — for spectrum analyser panel
        "frequency_domain": {
            "x_axis_frequencies": freqs,
            "y_axis_magnitudes":  magnitudes,
            "total_data_points":  len(freqs),
        },
        # Summary metrics — for dashboard status bar widgets
        "metrics": {
            "peak_magnitude":      peak_magnitude,
            "mean_magnitude":      mean_magnitude,
            "signal_to_noise_ratio": signal_to_noise,
        },
    }