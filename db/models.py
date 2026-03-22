import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/cropsense")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id            SERIAL PRIMARY KEY,
                    user_id       BIGINT,
                    disease_key   TEXT,
                    crop          TEXT,
                    confidence    FLOAT,
                    is_healthy    BOOLEAN,
                    risk_level    TEXT,
                    risk_score    FLOAT,
                    lat           FLOAT,
                    lon           FLOAT,
                    location_name TEXT,
                    lang          TEXT,
                    created_at    TIMESTAMP DEFAULT NOW()
                );
            """)
        conn.commit()
    print("Database initialised.")

def log_detection(
    user_id: int,
    disease_key: str,
    crop: str,
    confidence: float,
    is_healthy: bool,
    risk_level: str,
    risk_score: float,
    lat: float,
    lon: float,
    location_name: str,
    lang: str,
):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO detections
                        (user_id, disease_key, crop, confidence,
                         is_healthy, risk_level, risk_score,
                         lat, lon, location_name, lang)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    user_id, disease_key, crop, confidence,
                    is_healthy, risk_level, risk_score,
                    lat, lon, location_name, lang
                ))
            conn.commit()
    except Exception as e:
        print(f"DB log error: {e}")

def get_stats() -> dict:
    """Summary stats for dashboard header."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM detections")
                total = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(DISTINCT user_id)
                    FROM detections
                """)
                farmers = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*) FROM detections
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                """)
                week = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*) FROM detections
                    WHERE is_healthy = FALSE
                """)
                diseases = cur.fetchone()[0]

        return {
            "total":   total,
            "farmers": farmers,
            "week":    week,
            "diseases": diseases,
        }
    except Exception:
        return {"total": 0, "farmers": 0, "week": 0, "diseases": 0}

def get_recent_detections(limit: int = 100) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT disease_key, crop, confidence, is_healthy,
                           risk_level, lat, lon, location_name, created_at
                    FROM detections
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
        return [
            {
                "disease_key":   r[0],
                "crop":          r[1],
                "confidence":    r[2],
                "is_healthy":    r[3],
                "risk_level":    r[4],
                "lat":           r[5],
                "lon":           r[6],
                "location_name": r[7],
                "created_at":    r[8].strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    except Exception:
        return []

def get_disease_frequency(days: int = 30) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT disease_key, crop, COUNT(*) as count
                    FROM detections
                    WHERE is_healthy = FALSE
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY disease_key, crop
                    ORDER BY count DESC
                    LIMIT 10
                """, (days,))
                rows = cur.fetchall()
        return [
            {"disease": r[0].replace("___", " — ").replace("_", " "),
             "crop": r[1], "count": r[2]}
            for r in rows
        ]
    except Exception:
        return []

def get_daily_trend(days: int = 14) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DATE(created_at) as date,
                           COUNT(*) as total,
                           SUM(CASE WHEN is_healthy=FALSE THEN 1 ELSE 0 END) as diseases
                    FROM detections
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY DATE(created_at)
                    ORDER BY date
                """, (days,))
                rows = cur.fetchall()
        return [
            {"date": str(r[0]), "total": r[1], "diseases": r[2]}
            for r in rows
        ]
    except Exception:
        return []

def get_risk_distribution() -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT risk_level, COUNT(*) as count
                    FROM detections
                    WHERE is_healthy = FALSE
                    GROUP BY risk_level
                """)
                rows = cur.fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}