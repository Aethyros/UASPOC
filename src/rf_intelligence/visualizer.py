import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import sys

# Import the database function from the sibling module
from database import get_recent_simulations

def visualize_db_stream():
    print("\n[📡] INITIATING SECURE COMMS LINK TO LOCAL POSTGRESQL DATABASE...")
    
    try:
        print("[>] Requesting the most recent RF stream from database...")
        simulations = get_recent_simulations(limit=1)
        
        if not simulations:
            print("\n[!] CRITICAL ERROR: No data found in the 'rf_simulations' table.")
            print("[!] Run a simulation via the API first to populate the database.")
            sys.exit(1)
            
        data = simulations[0]
        
    except Exception as e:
        print(f"\n[!] DATABASE ERROR: {e}")
        sys.exit(1)
    
    # 1. Strict Schema Validation matching the flat database row structure
    if "carrier_wave_raw" not in data or "x_axis_frequencies" not in data:
        print("\n[!] ERROR: Database returned malformed payload.")
        print(f"[!] Received keys: {list(data.keys())}")
        sys.exit(1)

    print("[+] Stream acquired! Rendering Intelligence Dashboard...\n")

    # 2. Extract strictly synchronized arrays (Postgres arrays convert to Python lists automatically)
    time_wave = np.array(data["carrier_wave_raw"])
    freqs = np.array(data["x_axis_frequencies"])
    magnitudes = np.array(data["y_axis_magnitudes"])
    
    # 3. Extract Metadata & Intelligence Metrics directly from the database row
    snr = data.get('signal_to_noise_ratio', 0.0)
    peak_mag = data.get('peak_magnitude', 0.0)
    mean_mag = data.get('mean_magnitude', 0.0)
    
    center_freq = data.get('center_frequency_ghz', 0.0)
    bandwidth = data.get('bandwidth_mhz', 0.0)
    sample_freq = data.get('sample_frequency', 0.0)
    
    target_label = data.get("profile", "UNKNOWN").upper()
    threat_class = data.get("threat_class", "UNKNOWN")
    fhss_active = data.get("is_fhss", False)
    num_samples = len(time_wave)

    # ---------------------------------------------------------
    # UI SETUP: Professional Military HUD (Heads-Up Display)
    # ---------------------------------------------------------
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(14, 8))
    fig.canvas.manager.set_window_title('Intelligent Counter-UAS: Signal Intercept Viewer')
    
    # Use GridSpec to create a layout with a side-panel for intelligence stats
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 0.6], wspace=0.3, hspace=0.4)
    ax1 = fig.add_subplot(gs[0, :2]) # Top row, spanning 2 columns
    ax2 = fig.add_subplot(gs[1, :2]) # Bottom row, spanning 2 columns
    ax_info = fig.add_subplot(gs[:, 2]) # Right column, spanning both rows
    
    # Hide axes on the info panel for a clean text overlay
    ax_info.axis('off')

    # Theme Colors
    color_time = '#00FFFF' if not fhss_active else '#FF4500' # Cyan standard, Orange/Red for FHSS
    color_freq = '#39FF14' # Neon Green
    color_text = '#CCCCCC'

    # ---------------------------------------------------------
    # PLOT 1: TIME DOMAIN (Oscilloscope View)
    # ---------------------------------------------------------
    ax1.plot(time_wave, color=color_time, linewidth=1.2, alpha=0.9)
    ax1.set_title("RAW RF INTERCEPT (TIME DOMAIN)", fontsize=11, fontweight='bold', color='white', loc='left')
    ax1.set_xlabel("Time (Decimated Samples)", color=color_text, fontsize=9)
    ax1.set_ylabel("Amplitude (V)", color=color_text, fontsize=9)
    ax1.grid(True, color='#222222', linestyle='-', alpha=0.8)
    
    # ---------------------------------------------------------
    # PLOT 2: FREQUENCY DOMAIN (Spectrum Analyzer View)
    # ---------------------------------------------------------
    ax2.plot(freqs, magnitudes, color=color_freq, linewidth=1.5)
    ax2.fill_between(freqs, magnitudes, color=color_freq, alpha=0.15) 
    ax2.set_title("POWER SPECTRAL DENSITY (FREQUENCY DOMAIN)", fontsize=11, fontweight='bold', color='white', loc='left')
    ax2.set_xlabel("Frequency Bin (Hz)", color=color_text, fontsize=9)
    ax2.set_ylabel("Magnitude (dB)", color=color_text, fontsize=9)
    ax2.grid(True, color='#222222', linestyle='-', alpha=0.8)

    # Minimalist Spines for charts
    for ax in [ax1, ax2]:
        ax.tick_params(colors=color_text, labelsize=8)
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['bottom', 'left']:
            ax.spines[spine].set_color('#444444')

    # ---------------------------------------------------------
    # OVERLAY: THREAT INTELLIGENCE DASHBOARD
    # ---------------------------------------------------------
    status_color = '#FF4500' if fhss_active else '#39FF14'
    status_text = "EVASIVE TACTICS (FHSS)" if fhss_active else "FIXED-FREQUENCY"

    hud_content = (
        f"--- TACTICAL SIGNAL INTEL ---\n\n"
        f"TARGET LOCK:\n  {target_label}\n\n"
        f"THREAT CLASS:\n  {threat_class}\n\n"
        f"TRANSMISSION MODE:\n  {status_text}\n\n"
        f"--- PHYSICAL LINK STATS ---\n\n"
        f"CENTER FREQ:  {center_freq:.4f} GHz\n"
        f"BANDWIDTH:    {bandwidth:.1f} MHz\n"
        f"SAMPLE FREQ:  {sample_freq:.4f} GHz\n\n"
        f"--- SIGNAL QUALITY (DSP) ---\n\n"
        f"ESTIMATED SNR:\n  {snr} dB\n\n"
        f"PEAK MAGNITUDE:\n  {peak_mag}\n\n"
        f"NOISE FLOOR (MEAN):\n  {mean_mag}\n\n"
        f"DISPLAYED SAMPLES:\n  {num_samples}"
    )

    # Add HUD Text Box
    ax_info.text(0.05, 0.95, hud_content, transform=ax_info.transAxes, 
                 fontsize=10, color=color_text, verticalalignment='top', 
                 family='monospace', linespacing=1.5,
                 bbox=dict(boxstyle='square,pad=1.5', facecolor='#111111', edgecolor=status_color, alpha=0.8))

    # Master Warning Overlay for Military Mode
    if fhss_active:
        fig.suptitle('⚠ MILITARY FHSS EVASION SEQUENCE DETECTED ⚠', 
                     color='#FF4500', fontweight='bold', fontsize=14, y=0.96)
    else:
        fig.suptitle(' NORMAL NON FHSS DRONE SIGNAL DETECTED', 
                     color='white', fontweight='bold', fontsize=14, y=0.96, alpha=0.8)

    fig.text(0.98, 0.02, 'SYSTEM: RF INTELLIGENCE MODULE // DSP ENGINE: ACTIVE', 
             fontsize=8, color='#555555', ha='right', va='bottom', family='monospace')

    # Add slight background padding
    fig.patch.set_facecolor('#0a0a0a')
    plt.tight_layout(rect=[0, 0, 1, 0.93]) # Leave room for suptitle
    plt.show()

if __name__ == "__main__":
    visualize_db_stream()