import numpy as np

RF_PROFILES = {
    # ── CIVILIAN / COMMERCIAL ──────────────────────────────────────────────
    "dji_phantom_4":    {"center_freq_ghz": 2.400, "bandwidth_mhz": 20, "noise_sigma": 0.25},
    "parrot_bebop":     {"center_freq_ghz": 2.410, "bandwidth_mhz": 15, "noise_sigma": 0.30},

    # ── ENTERPRISE / MILITARY THREATS ──────────────────────────────────────
    "dji_matrice_300":  {"center_freq_ghz": 2.450, "bandwidth_mhz": 40, "noise_sigma": 0.20},
    "skydio_x2":        {"center_freq_ghz": 5.180, "bandwidth_mhz": 20, "noise_sigma": 0.20},
    "autel_evo_max":    {"center_freq_ghz": 5.850, "bandwidth_mhz": 20, "noise_sigma": 0.15},

    # ── ROGUE / CUSTOM THREATS ─────────────────────────────────────────────
    "generic_fpv":      {"center_freq_ghz": 5.800, "bandwidth_mhz": 40, "noise_sigma": 0.35},
    "tbs_crossfire":    {"center_freq_ghz": 0.915, "bandwidth_mhz": 10, "noise_sigma": 0.40},

    # ── CHEAP TOY / NUISANCE ───────────────────────────────────────────────
    "holy_stone":       {"center_freq_ghz": 5.200, "bandwidth_mhz": 20, "noise_sigma": 0.30},
}


def synthesize_rf_wave(profile_type="dji_phantom_4", num_samples=128):
    """
    Synthesizes a raw, noisy RF carrier wave float array based on ground-truth profiles.
    Noise level varies per profile — military drones have cleaner signals than rogue FPV.
    """

    profile = RF_PROFILES.get(profile_type)

    if profile is None:
        print(f"[WARN] Unknown profile '{profile_type}' — defaulting to dji_phantom_4")
        profile = RF_PROFILES["dji_phantom_4"]

    center_freq = profile["center_freq_ghz"]
    noise_sigma = profile["noise_sigma"]

    # Generate simulated time domain array
    time_steps = np.linspace(0, 1, num_samples)

    # Clean mathematical sinusoid at the drone's broadcast frequency
    clean_wave = np.sin(2 * np.pi * center_freq * time_steps)

    # Superimpose realistic atmospheric/channel noise
    noise = np.random.normal(0, noise_sigma, clean_wave.shape)
    noisy_waveform = clean_wave + noise

    return noisy_waveform.tolist()



def synthesize_fhss_wave(base_freq_ghz: float, num_hops: int = 4, samples_per_hop: int = 32) -> dict:
    """
    Simulates Frequency-Hopping Spread Spectrum (FHSS) used by advanced/military UAVs.
    Generates a randomized sequence of frequency hops and stitches the resulting waveform.
    Military drones hop within a +-0.02 GHz window around the base frequency.
    DB profiles that use FHSS: autel_evo_max (5.850 GHz), dji_matrice_300 (2.450 GHz).
    """
    # 1. Define the Hopper Bandwidth (How far it can jump from the center)
    hop_offsets = np.random.uniform(-0.02, 0.02, num_hops)

    # 2. Calculate the exact frequency for each hop
    hop_sequence = [round(base_freq_ghz + offset, 4) for offset in hop_offsets]

    stitched_wave = []

    # 3. Generate a burst of radio wave for each specific hop, then stitch them together
    for hop_freq in hop_sequence:
        t = np.linspace(0, 1, samples_per_hop)
        carrier = np.sin(2 * np.pi * hop_freq * t)

        # Superimpose physical channel noise
        noise = np.random.normal(0, 0.25, samples_per_hop)
        burst = carrier + noise

        # Attach this burst to the master timeline
        stitched_wave.extend(burst.tolist())

    return {
        "base_freq_ghz": base_freq_ghz,
        "hop_sequence_ghz": hop_sequence,
        "total_samples": len(stitched_wave),
        "fhss_waveform": stitched_wave
    }