import numpy as np

def synthesize_rf_wave(profile_type="dji_phantom_4", num_samples=128):
    """
    Synthesizes a raw, noisy RF carrier wave float array based on ground-truth profiles.
    """
    # 1. Map profile to center frequency (GHz)
    freq_map = {
        "dji_phantom_4": 2.400,
        "generic_fpv": 5.800,
        "parrot_bebop": 2.410,
        "mavlink_hub": 0.900
    }
    center_freq = freq_map.get(profile_type, 2.400)
    
    # 2. Generate simulated time domain array
    time_steps = np.linspace(0, 1, num_samples)
    
    # 3. Create clean mathematical sinusoid
    clean_wave = np.sin(2 * np.pi * center_freq * time_steps)
    
    # 4. Superimpose realistic atmospheric/channel noise
    noise = np.random.normal(0, 0.25, clean_wave.shape)
    noisy_waveform = clean_wave + noise
    
    # Return as standard Python float list for clean FastAPI JSON serialization
    return noisy_waveform.tolist()

def synthesize_fhss_wave(base_freq_ghz: float, num_hops: int = 5, samples_per_hop: int = 32) -> dict:
    """
    Simulates Frequency-Hopping Spread Spectrum (FHSS) used by advanced/military UAVs.
    Generates a randomized sequence of frequency hops and stitches the resulting waveform.
    """
    # 1. Define the Hopper Bandwidth (How far it can jump from the center)
    # Military drones usually hop within a +- 0.02 GHz window
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