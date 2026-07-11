import numpy as np
from scipy.signal import butter, filtfilt

def apply_bandpass_filter(data, lowcut: float, highcut: float, fs: float, order: int = 4):
    """
    Filters a signal based on dynamic parameters provided by the API.
    """
    # 1. Calculate the Nyquist frequency (half the sample rate)
    nyquist = 0.5 * fs
    
    # 2. Normalize the frequencies
    low = max(0.01, min(0.99, lowcut / nyquist))
    high = max(0.01, min(0.99, highcut / nyquist))
    
    # 3. Create the filter parameters
    b, a = butter(order, [low, high], btype='band')
    
    # 4. Apply the filter to the data and return the clean signal
    filtered_signal = filtfilt(b, a, data)
    
    return filtered_signal
