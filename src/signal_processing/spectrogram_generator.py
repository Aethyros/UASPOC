import requests
import io
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from signal_filter import apply_bandpass_filter


def generate_live_spectrogram(api_url="http://127.0.0.1:8000/api/rf/latest"):
    """
    Pulls live drone data from the API and streams a spectrogram image from memory.
    """
    print(f"Fetching drone profile from {api_url}...")
    
    try:
        # TWEAK 1: Call RF Module's API directly to get the JSON array
        response = requests.get(api_url)
        response.raise_for_status() # Check for errors
        
        # Extract the JSON data RF Module mentioned
        drone_data = response.json() 
        
        # Assuming his API returns a list of signal points and a sample rate
        
        raw_wave   = np.array(drone_data.get("carrier_wave_raw", [])) + 1e-10
        bandwidth_mhz = drone_data.get("bandwidth_mhz", 20.0)
        fs_hz      = drone_data.get("sample_frequency", 0.05) * 1e9       # 50 MHz -> 50,000,000 Hz
        lowcut_hz  = 1e6  # 1 MHz lower bound
        highcut_hz = (bandwidth_mhz / 2.0) * 1e6  # Half-bandwidth upper bound
        center_hz  = drone_data.get("center_frequency_ghz", 2.4) * 1e9    # Convert to Hz
        clean_wave = apply_bandpass_filter(raw_wave, lowcut_hz, highcut_hz, fs_hz)
        
    except Exception as e:
        print(f"Failed to connect to API. Is the server running? Error: {e}")
        return None

    print("Data received! Generating in-memory spectrogram...")
    
    # Create the spectrogram plot
    plt.figure(figsize=(10, 6))
    plt.specgram(clean_wave,Fs=fs_hz,Fc=center_hz, cmap='inferno')
    plt.title("Live API Spectrogram Stream")
    plt.ylabel("Frequency (Hz)")
    plt.xlabel("Time (sec)")
    
    # TWEAK 2: The Memory Buffer
    # Instead of plt.savefig("my_image.png"), we create an invisible digital file
    image_buffer = io.BytesIO()
    
    # Save the plot directly into the buffer
    plt.savefig(image_buffer, format='png')
    
    # Reset the buffer's "cursor" to the beginning so other modules can read it
    image_buffer.seek(0) 
    # Temporary debug: save to disk to confirm it works
    
    """with open("debug_spectrogram.png", "wb") as f:
        f.write(image_buffer.read())
    print("Spectrogram saved as 'debug_spectrogram.png' for verification.")"""
    
    
    # Clear the plot from matplotlib's memory so it doesn't slow down the computer
    print(f"DEBUG: Buffer has {image_buffer.getbuffer().nbytes} bytes of data.")
    plt.close()
    
    print("Spectrogram successfully buffered and ready to stream!")
    
    # Return the raw byte data so the dashboard or API can stream it
    return image_buffer

# (Optional) Test block to ensure it runs locally
if __name__ == "__main__":
    # Note: This will likely fail with a connection error right now unless the server is working
    buffer = generate_live_spectrogram()