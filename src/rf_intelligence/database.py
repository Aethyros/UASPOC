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

def query_signature_by_telemetry(packet_len: int, symbol_rate: float):
    """DETECTION: Identifies evasive FHSS drones by the physical shape of their data packets."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # We look for a match based on packet size and speed, completely ignoring frequency!
    cur.execute("""
        SELECT * FROM uav_rf_signatures
        WHERE packet_length_bytes = %s 
        AND symbol_rate_mbps = %s
        LIMIT 1;
    """, (packet_len, symbol_rate))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result