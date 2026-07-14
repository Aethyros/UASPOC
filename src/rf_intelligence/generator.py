import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor

# Fallback profile definitions and noise floor mapping.
# Notice: Database stores telemetry signatures, while RF_PROFILES provides channel noise simulation parameters.
RF_PROFILES = {
    # CIVILIAN / COMMERCIAL 
    "dji_phantom_4":    {"db_model": "DJI Phantom 4",       "center_freq_ghz": 2.400, "bandwidth_mhz": 20, "noise_sigma": 0.25},
    "parrot_bebop":     {"db_model": "Parrot Bebop",        "center_freq_ghz": 2.410, "bandwidth_mhz": 15, "noise_sigma": 0.30},

    # ENTERPRISE / MILITARY THREATS 
    "dji_matrice_300":  {"db_model": "DJI Matrice 300 RTK", "center_freq_ghz": 2.450, "bandwidth_mhz": 40, "noise_sigma": 0.20},
    "skydio_x2":        {"db_model": "Skydio X2",           "center_freq_ghz": 5.180, "bandwidth_mhz": 20, "noise_sigma": 0.20},
    "autel_evo_max":    {"db_model": "Autel EVO Max 4T",    "center_freq_ghz": 5.850, "bandwidth_mhz": 20, "noise_sigma": 0.15},

    # ROGUE / CUSTOM THREATS 
    "generic_fpv":      {"db_model": "Generic Custom FPV",  "center_freq_ghz": 5.800, "bandwidth_mhz": 40, "noise_sigma": 0.35},
    "tbs_crossfire":    {"db_model": "TBS Crossfire FPV",   "center_freq_ghz": 0.915, "bandwidth_mhz": 10, "noise_sigma": 0.40},

    # CHEAP TOY / NUISANCE 
    "holy_stone":       {"db_model": "Holy Stone HS720E",   "center_freq_ghz": 5.200, "bandwidth_mhz": 20, "noise_sigma": 0.30},
}


def get_telemetry_from_db(target_model_name: str) -> dict:
    """
    Fetches packet length and symbol rate from the PostgreSQL database.
    Returns default fallback values if the database is unreachable or the model is missing.
    """
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT packet_length_bytes, symbol_rate_mbps 
            FROM uav_rf_signatures 
            WHERE target_model = %s OR target_model ILIKE %s
            LIMIT 1;
        """, (target_model_name, f"%{target_model_name}%"))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return result
    except Exception as e:
        print(f"[WARN] Database query failed for '{target_model_name}': {e}. Using fallback simulation values.")

    # Default fallback if DB lookup fails (defaults to DJI Phantom 4 telemetry)
    return {"packet_length_bytes": 256, "symbol_rate_mbps": 10.00}


def synthesize_rf_wave(profile_type="dji_phantom_4", num_samples=None):
    """
    Synthesizes a realistic RF carrier wave float array based on ground-truth database telemetry.
    """
    profile = RF_PROFILES.get(profile_type)

    if profile is None:
        print(f"[WARN] Unknown profile '{profile_type}' — defaulting to dji_phantom_4")
        profile = RF_PROFILES["dji_phantom_4"]

    noise_sigma = profile["noise_sigma"]
    db_model_name = profile.get("db_model", "DJI Phantom 4")

    # 1. Fetch live telemetry from the RF database
    telemetry = get_telemetry_from_db(db_model_name)
    packet_bytes = telemetry["packet_length_bytes"]
    symbol_rate_mbps = float(telemetry["symbol_rate_mbps"])

    # 2. Hardware sampling parameters
    fs = 100e6          # 100 MHz sampling frequency
    fc = 10e6           # 10 MHz simulated baseband carrier frequency

    # 3. Calculate Time-on-Air (TOA) and dynamic sample count
    # Total bits = bytes * 8. Duration in seconds = bits / (symbol_rate * 1e6)
    total_bits = packet_bytes * 8
    time_on_air_sec = total_bits / (symbol_rate_mbps * 1e6)

    # If num_samples is not explicitly overridden, calculate it from real-world packet duration
    if num_samples is None:
        num_samples = max(1024, int(time_on_air_sec * fs))

    # Time vector
    t = np.arange(num_samples) / fs

    # 4. Generate Carrier Waveform
    carrier = np.sin(2 * np.pi * fc * t)

    # 5. Symbol Rate Envelope Modulation
    # Instead of an arbitrary 200 kHz wave, modulate the envelope using the protocol's true symbol rate
    # We use a fundamental frequency representing bit toggling across the transmission window
    mod_freq = (symbol_rate_mbps * 1e6) / 4.0  # Scaled for visual/spectral representation within baseband
    envelope = 1.0 + 0.25 * np.sin(2 * np.pi * mod_freq * t)

    clean_wave = envelope * carrier

    # 6. Channel Noise Addition
    noise = np.random.normal(0, noise_sigma, num_samples)
    noisy_waveform = clean_wave + noise

    return {
        "signal_type": "STANDARD_RF",
        "center_freq_ghz": profile["center_freq_ghz"],
        "bandwidth_mhz": profile["bandwidth_mhz"],
        "total_samples": num_samples,
        "time_on_air_sec": round(time_on_air_sec, 6),
        "telemetry_used": {
            "model": db_model_name,
            "packet_length_bytes": packet_bytes,
            "symbol_rate_mbps": symbol_rate_mbps
        },
        "waveform": noisy_waveform.tolist()
    }


def synthesize_fhss_wave(
    base_freq_ghz: float = 5.800, 
    num_hops: int = 4,
    target_model: str = "Autel EVO Max 4T"
):
    """
    High-performance FHSS waveform generator.
    Uses pre-allocated float32 memory and dynamically applies database telemetry 
    (packet_length_bytes & symbol_rate_mbps) to produce realistic Time-on-Air and modulation.
    """
    # 1. Fetch exact physical link characteristics from database (with safe fallback)
    db_meta = get_telemetry_from_db(target_model)
    packet_len = db_meta["packet_length_bytes"]
    symbol_rate = db_meta["symbol_rate_mbps"]
    
    # 2. Calculate realistic Time-on-Air (TOA) per hop using: TOA = (bytes * 8) / symbol_rate
    # This ensures larger data payloads physically occupy the RF spectrum for more samples
    bits_per_packet = packet_len * 8
    duration_us_per_hop = bits_per_packet / symbol_rate
    
    # Establish a stable sampling rate (e.g., 200 samples per microsecond of active burst)
    sample_rate_mhz = 200.0
    samples_per_hop = max(512, int(duration_us_per_hop * sample_rate_mhz))
    total_samples = num_hops * samples_per_hop
    
    # 3. OPTIMIZATION: Pre-allocate memory once as single-precision float32
    # Eliminates memory reallocation lag inside the loop and halves RAM usage
    fhss_waveform = np.empty(total_samples, dtype=np.float32)
    hop_sequence = []
    
    # Pre-compute time vector for a single hop window to avoid redundant linspace calls
    t_hop = np.linspace(0, duration_us_per_hop / 1e6, samples_per_hop, endpoint=False, dtype=np.float32)
    
    # Pre-compute the baud-rate amplitude modulation envelope based on exact symbol rate
    f_mod = (symbol_rate * 1e6) / 2.0
    envelope = (0.7 + 0.3 * np.sin(2 * np.pi * f_mod * t_hop)).astype(np.float32)
    
    # 4. Vectorized Hop Synthesis
    for i in range(num_hops):
        start_idx = i * samples_per_hop
        end_idx = start_idx + samples_per_hop
        
        # Pseudo-random frequency jump within +/- 20 MHz bandwidth window
        hop_offset_mhz = np.random.uniform(-20.0, 20.0)
        hop_freq_ghz = round(base_freq_ghz + (hop_offset_mhz / 1000.0), 4)
        hop_sequence.append(hop_freq_ghz)
        
        # Synthesize carrier burst modulated by protocol-specific baud rate
        carrier = np.sin(2 * np.pi * (hop_freq_ghz * 1e9) * t_hop, dtype=np.float32) * envelope
        
        # Add light Additive White Gaussian Noise (AWGN) for real-world channel accuracy
        noise = np.random.normal(0, 0.1, samples_per_hop).astype(np.float32)
        
        # In-place assignment into pre-allocated memory slice
        fhss_waveform[start_idx:end_idx] = carrier + noise

    # 5. Strictly preserve your original return schema
    return {
        "signal_type": "FHSS",
        "base_freq_ghz": base_freq_ghz,
        "bandwidth_mhz": 40.0,
        "total_samples": total_samples,
        "hop_sequence_ghz": hop_sequence,
        "fhss_waveform": fhss_waveform.tolist(), # Convert to Python list at final boundary
        "telemetry_used": {
            "model": target_model,
            "packet_length_bytes": packet_len,
            "symbol_rate_mbps": symbol_rate
        }
    }