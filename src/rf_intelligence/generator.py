import numpy as np

RF_PROFILES = {
    # CIVILIAN / COMMERCIAL 
    "dji_phantom_4":    {"center_freq_ghz": 2.400, "bandwidth_mhz": 20, "noise_sigma": 0.25},
    "parrot_bebop":     {"center_freq_ghz": 2.410, "bandwidth_mhz": 15, "noise_sigma": 0.30},

    # ENTERPRISE / MILITARY THREATS 
    "dji_matrice_300":  {"center_freq_ghz": 2.450, "bandwidth_mhz": 40, "noise_sigma": 0.20},
    "skydio_x2":        {"center_freq_ghz": 5.180, "bandwidth_mhz": 20, "noise_sigma": 0.20},
    "autel_evo_max":    {"center_freq_ghz": 5.850, "bandwidth_mhz": 20, "noise_sigma": 0.15},

    # ROGUE / CUSTOM THREATS 
    "generic_fpv":      {"center_freq_ghz": 5.800, "bandwidth_mhz": 40, "noise_sigma": 0.35},
    "tbs_crossfire":    {"center_freq_ghz": 0.915, "bandwidth_mhz": 10, "noise_sigma": 0.40},

    # CHEAP TOY / NUISANCE 
    "holy_stone":       {"center_freq_ghz": 5.200, "bandwidth_mhz": 20, "noise_sigma": 0.30},
}


def synthesize_rf_wave(profile_type="dji_phantom_4", num_samples=1024):
    """
    Synthesizes a raw, noisy RF carrier wave float array based on ground-truth profiles.
    Noise level varies per profile — military drones have cleaner signals than rogue FPV.
    """

    profile = RF_PROFILES.get(profile_type)

    if profile is None:
        print(f"[WARN] Unknown profile '{profile_type}' — defaulting to dji_phantom_4")
        profile = RF_PROFILES["dji_phantom_4"]

    noise_sigma = profile["noise_sigma"]

    # Sampling frequency (must match the rest of the project)
    fs = 100e6          # 100 MHz

    # Simulated carrier frequency within Nyquist
    fc = 10e6           # 10 MHz

    # Time vector
    t = np.arange(num_samples) / fs

    # Carrier
    carrier = np.sin(2 * np.pi * fc * t)

    # Optional amplitude modulation to make the spectrogram less flat
    envelope = 1.0 + 0.15 * np.sin(2 * np.pi * 2e5 * t)

    clean_wave = envelope * carrier

    # Channel noise
    noise = np.random.normal(
        0,
        noise_sigma,
        num_samples
    )

    noisy_waveform = clean_wave + noise

    return noisy_waveform.tolist()


def synthesize_fhss_wave(base_freq_ghz: float, num_hops: int = 4, samples_per_hop: int = 256) -> dict:
    """
    Simulates Frequency-Hopping Spread Spectrum (FHSS) used by advanced/military UAVs.
    Generates a randomized sequence of frequency hops and stitches the resulting waveform.
    Military drones hop within a +-0.02 GHz window around the base frequency.
    DB profiles that use FHSS: autel_evo_max (5.850 GHz), dji_matrice_300 (2.450 GHz).
    """

    # 1. Find the matching RF profile to determine channel noise
    matching_profile = next(
        (p for p in RF_PROFILES.values()
         if abs(p["center_freq_ghz"] - base_freq_ghz) < 0.05),
        None
    )

    noise_sigma = matching_profile["noise_sigma"] if matching_profile else 0.25

    # 2. Simulator sampling parameters
    fs = 100e6                    # 100 MHz sampling frequency
    baseband_carrier = 10e6       # 10 MHz simulated carrier

    stitched_wave = []
    hop_sequence = []

    # 3. Generate random hop offsets (±2 MHz around the carrier)
    hop_offsets = np.random.uniform(-2e6, 2e6, num_hops)

    # 4. Generate one burst for every hop frequency
    for hop_offset in hop_offsets:

        # Calculate the baseband carrier for this hop
        fc = baseband_carrier + hop_offset

        # Store the actual RF hop frequency as metadata
        hop_sequence.append(
            round(base_freq_ghz + hop_offset / 1e9, 6)
        )

        # Time vector for this burst
        t = np.arange(samples_per_hop) / fs

        # Generate the carrier waveform
        carrier = np.sin(2 * np.pi * fc * t)

        # Add channel noise
        noise = np.random.normal(
            0,
            noise_sigma,
            samples_per_hop
        )

        # Attach this burst to the master timeline
        stitched_wave.extend((carrier + noise).tolist())

    # 5. Return the synthesized FHSS waveform and hop metadata
    return {
        "base_freq_ghz": base_freq_ghz,
        "hop_sequence_ghz": hop_sequence,
        "total_samples": len(stitched_wave),
        "fhss_waveform": stitched_wave
    }