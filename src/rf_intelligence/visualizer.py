import requests
import numpy as np
import matplotlib.pyplot as plt

def visualize_api_stream():
    print("Fetching live RF data from module...")
    
    # 1. Ping your live FastAPI server
    API_URL = "http://127.0.0.1:8000/api/rf/simulate?profile=dji_phantom_4"
    try:
        response = requests.get(API_URL).json()
    except requests.exceptions.ConnectionError:
        print("Error: Is your Uvicorn server running?")
        return

    raw_wave = np.array(response["carrier_wave_raw"])
    num_samples = len(raw_wave)

    # 2. Setup a dark-mode plotting canvas
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    fig.tight_layout(pad=5.0)

    # PLOT 1: TIME DOMAIN (The raw oscilloscope view)
    ax1.plot(raw_wave, color='cyan', linewidth=1.5)
    ax1.set_title(f"Time Domain: Intercepted RF Burst ({num_samples} Samples)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Time (Samples)")
    ax1.set_ylabel("Amplitude")
    ax1.grid(True, alpha=0.2)


    # PLOT 2: FREQUENCY DOMAIN (The Spectrum Analyzer view)

    # Mathematically transform the time-wave into the frequency spectrum using FFT
    fft_result = np.fft.fft(raw_wave)
    fft_freq = np.fft.fftfreq(num_samples)

    # Filter out the mirrored negative frequencies for a clean plot
    pos_mask = fft_freq > 0
    freqs = fft_freq[pos_mask]
    magnitudes = np.abs(fft_result[pos_mask])

    ax2.plot(freqs, magnitudes, color='lime', linewidth=2)
    ax2.fill_between(freqs, magnitudes, color='lime', alpha=0.2) 
    
    ax2.set_title("Frequency Domain: Fast Fourier Transform (FFT) Spectrum", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Normalized Frequency Bin")
    ax2.set_ylabel("Signal Power / Magnitude")
    ax2.grid(True, alpha=0.2)

    print("Rendering Spectrum Analysis...")
    plt.show()

if __name__ == "__main__":
    visualize_api_stream()