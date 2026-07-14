import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Standard local PostgreSQL connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres") # Default local db
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

def get_db_connection():
    """Establishes a connection to the local PostgreSQL instance."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        cursor_factory=RealDictCursor
    )

def initialize_rf_database():
    """Builds the RF Fingerprint schema with secondary telemetry tracking."""
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. NUKE THE OLD TABLE
    cur.execute("DROP TABLE IF EXISTS uav_rf_signatures CASCADE;")

    # 2. CREATE THE NEW TABLE
    cur.execute("""
        CREATE TABLE uav_rf_signatures (
            id SERIAL PRIMARY KEY,
            target_model VARCHAR(100) UNIQUE NOT NULL,
            center_freq_ghz NUMERIC(5, 3) NOT NULL,
            bandwidth_mhz INTEGER NOT NULL,
            packet_length_bytes INTEGER NOT NULL, 
            symbol_rate_mbps NUMERIC(5, 2) NOT NULL, 
            protocol_label VARCHAR(150) NOT NULL,
            protocol_security VARCHAR(50) NOT NULL,
            countermeasure VARCHAR(100) NOT NULL
        );
    """)

    # 3. SEED THE GROUND-TRUTH PROFILES
    seed_profiles = [
    # 1. THE STANDARD (Civilian/Commercial)
    ("DJI Phantom 4", 2.400, 20, 256, 10.00, "DJI Lightbridge", "Encrypted/Secure", "GPS Spoofing"),
    ("Parrot Bebop", 2.410, 15, 512, 2.00, "MAVLink Telemetry", "Open Source", "Protocol Injection"),
    
    # 2. THE ENTERPRISE/MILITARY THREATS
    ("DJI Matrice 300 RTK", 2.450, 40, 512, 15.00, "OcuSync Enterprise", "Encrypted/Secure", "GPS Spoofing"),
    ("Skydio X2", 5.180, 20, 256, 12.00, "Skydio Link", "Encrypted/Secure", "GPS Spoofing"),
    ("Autel EVO Max 4T", 5.850, 20, 1024, 20.00, "Autel SkyLink 3.0", "Encrypted/Secure", "GPS Spoofing"),

    # 3. THE ROGUE/CUSTOM THREATS
    ("Generic Custom FPV", 5.800, 40, 128, 5.00, "Generic RC Link", "Open Source", "Protocol Injection"),
    ("TBS Crossfire FPV", 0.915, 10, 64, 0.25, "CRSF Telemetry", "Open Source", "Protocol Injection"),
    
    # 4. THE CHEAP TOY (Common Nuisance)
    ("Holy Stone HS720E", 5.200, 20, 128, 2.00, "Standard Wi-Fi", "Open Source", "Protocol Injection")
]

    for profile in seed_profiles:
        cur.execute("""
            INSERT INTO uav_rf_signatures 
            (target_model, center_freq_ghz, bandwidth_mhz, packet_length_bytes, symbol_rate_mbps, protocol_label, protocol_security, countermeasure)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (target_model) DO NOTHING;
        """, profile)

    conn.commit()
    cur.close()
    conn.close()
    print("SUCCESS: PostgreSQL 'uav_rf_signatures'.")

def query_signature_by_frequency(target_freq_ghz):
    """Queries the database to match an incoming frequency to a known profile."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Finds the closest matching profile within a 0.05 GHz tolerance window
    cur.execute("""
        SELECT * FROM uav_rf_signatures
        WHERE ABS(center_freq_ghz - %s) < 0.05
        LIMIT 1;
    """, (target_freq_ghz,))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result

def query_signature_by_telemetry(packet_len: int, symbol_rate: float, len_tol: int = 4, rate_tol_pct: float = 0.05):
    """
    DETECTION: Identifies evasive FHSS drones by physical packet shape,
    allowing for real-world calculation tolerances in the DSP pipeline.
    
    :param packet_len: Estimated packet length in bytes.
    :param symbol_rate: Estimated symbol rate in Mbps.
    :param len_tol: Absolute byte tolerance (+/-).
    :param rate_tol_pct: Percentage tolerance for symbol rate (default 5%).
    """
    # Calculate acceptable bounds
    min_len = packet_len - len_tol
    max_len = packet_len + len_tol
    
    rate_margin = symbol_rate * rate_tol_pct
    min_rate = symbol_rate - rate_margin
    max_rate = symbol_rate + rate_margin

    conn = get_db_connection()
    cur = conn.cursor()
    
    # Query using a tolerance bounding box, then sort by the closest symbol rate match
    cur.execute("""
        SELECT * FROM uav_rf_signatures
        WHERE packet_length_bytes BETWEEN %s AND %s 
        AND symbol_rate_mbps BETWEEN %s AND %s
        ORDER BY ABS(symbol_rate_mbps - %s) ASC
        LIMIT 1;
    """, (min_len, max_len, min_rate, max_rate, symbol_rate))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result



# Stores simulation results

def initialize_simulations_table():
    """Builds the schema for storing historical RF simulation runs."""
    conn = get_db_connection()
    cur = conn.cursor()

    # NUKE THE OLD TABLE
    cur.execute("DROP TABLE IF EXISTS rf_simulations CASCADE;")

    # Create the simulations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rf_simulations (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            profile VARCHAR(50) NOT NULL,
            threat_class VARCHAR(50) NOT NULL,
            is_fhss BOOLEAN NOT NULL,
            
            -- Frequency Config
            center_frequency_ghz REAL NOT NULL,
            bandwidth_mhz REAL NOT NULL,
            lowcut_frequency REAL,
            highcut_frequency REAL,
            sample_frequency REAL,
            
            -- Metrics
            peak_magnitude REAL,
            mean_magnitude REAL,
            signal_to_noise_ratio REAL,
            
            -- Heavy Arrays (Native Postgres Arrays)
            carrier_wave_raw REAL[] NOT NULL,
            x_axis_frequencies REAL[] NOT NULL,
            y_axis_magnitudes REAL[] NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("SUCCESS: PostgreSQL 'rf_simulations' table initialized.")


def insert_rf_simulation(payload: dict):
    """Inserts a single simulation dictionary payload into the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    metrics = payload.get("metrics", {})
    freq_domain = payload.get("frequency_domain", {})

    cur.execute("""
        INSERT INTO rf_simulations (
            profile, threat_class, is_fhss, 
            center_frequency_ghz, bandwidth_mhz, lowcut_frequency, highcut_frequency, sample_frequency,
            peak_magnitude, mean_magnitude, signal_to_noise_ratio,
            carrier_wave_raw, x_axis_frequencies, y_axis_magnitudes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        payload["profile"],
        payload["threat_class"],
        payload["is_fhss"],
        payload["center_frequency_ghz"],
        payload["bandwidth_mhz"],
        payload["lowcut_frequency"],
        payload["highcut_frequency"],
        payload["sample_frequency"],
        metrics.get("peak_magnitude", 0.0),
        metrics.get("mean_magnitude", 0.0),
        metrics.get("signal_to_noise_ratio", 0.0),
        payload["carrier_wave_raw"],          # psycopg2 handles Python lists -> Postgres Arrays automatically
        freq_domain.get("x_axis_frequencies", []),
        freq_domain.get("y_axis_magnitudes", [])
    ))
    
    conn.commit()
    cur.close()
    conn.close()


def get_recent_simulations(limit=5):
    """Fetches the most recent RF simulations from the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Query the table we created earlier
    cur.execute("""
        SELECT * FROM rf_simulations 
        ORDER BY timestamp DESC 
        LIMIT %s;
    """, (limit,))
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results

if __name__ == "__main__":
    print("Starting database initialization...")
    
    # 1. Initialize your original telemetry table
    initialize_rf_database()
    
    # 2. Initialize the new simulations table
    initialize_simulations_table()
    
    print("All tables initialized successfully!")