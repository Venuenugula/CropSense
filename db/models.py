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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS farmer_profiles (
                    user_id BIGINT PRIMARY KEY,
                    lang TEXT,
                    district TEXT,
                    primary_crop TEXT,
                    acres FLOAT,
                    irrigation_type TEXT,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    district TEXT,
                    crop TEXT,
                    alert_type TEXT DEFAULT 'outbreak',
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    request_id TEXT,
                    helpful BOOLEAN,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS official_interventions (
                    id SERIAL PRIMARY KEY,
                    district TEXT,
                    disease_key TEXT,
                    action TEXT,
                    status TEXT DEFAULT 'planned',
                    owner TEXT,
                    due_date DATE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
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
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
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
                    WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
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
def get_subscriber_ids() -> list:
    """Get all unique user IDs who have used the bot."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT user_id FROM detections
                    WHERE user_id > 0
                """)
                return [row[0] for row in cur.fetchall()]
    except Exception:
        return []


def upsert_farmer_profile(
    user_id: int,
    lang: str = None,
    district: str = None,
    primary_crop: str = None,
    acres: float = None,
    irrigation_type: str = None,
):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO farmer_profiles (
                        user_id, lang, district, primary_crop, acres, irrigation_type, updated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        lang = COALESCE(EXCLUDED.lang, farmer_profiles.lang),
                        district = COALESCE(EXCLUDED.district, farmer_profiles.district),
                        primary_crop = COALESCE(EXCLUDED.primary_crop, farmer_profiles.primary_crop),
                        acres = COALESCE(EXCLUDED.acres, farmer_profiles.acres),
                        irrigation_type = COALESCE(EXCLUDED.irrigation_type, farmer_profiles.irrigation_type),
                        updated_at = NOW()
                """, (user_id, lang, district, primary_crop, acres, irrigation_type))
            conn.commit()
    except Exception as e:
        print(f"Profile upsert error: {e}")


def get_farmer_profile(user_id: int) -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, lang, district, primary_crop, acres, irrigation_type, updated_at
                    FROM farmer_profiles
                    WHERE user_id = %s
                """, (user_id,))
                row = cur.fetchone()
                if not row:
                    return {}
                return {
                    "user_id": row[0],
                    "lang": row[1],
                    "district": row[2],
                    "primary_crop": row[3],
                    "acres": row[4],
                    "irrigation_type": row[5],
                    "updated_at": row[6].strftime("%Y-%m-%d %H:%M") if row[6] else None,
                }
    except Exception:
        return {}


def add_subscription(user_id: int, district: str, crop: str, alert_type: str = "outbreak"):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_subscriptions (user_id, district, crop, alert_type, active)
                    VALUES (%s,%s,%s,%s,TRUE)
                """, (user_id, district, crop, alert_type))
            conn.commit()
    except Exception as e:
        print(f"Subscription insert error: {e}")


def get_subscriptions(user_id: int = None) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute("""
                        SELECT id, user_id, district, crop, alert_type, active, created_at
                        FROM user_subscriptions
                        WHERE user_id = %s AND active = TRUE
                        ORDER BY created_at DESC
                    """, (user_id,))
                else:
                    cur.execute("""
                        SELECT id, user_id, district, crop, alert_type, active, created_at
                        FROM user_subscriptions
                        WHERE active = TRUE
                        ORDER BY created_at DESC
                    """)
                rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "user_id": r[1],
                "district": r[2],
                "crop": r[3],
                "alert_type": r[4],
                "active": r[5],
                "created_at": r[6].strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    except Exception:
        return []


def log_feedback(user_id: int, request_id: str, helpful: bool, note: str = ""):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_feedback (user_id, request_id, helpful, note)
                    VALUES (%s,%s,%s,%s)
                """, (user_id, request_id, helpful, note))
            conn.commit()
    except Exception as e:
        print(f"Feedback log error: {e}")


def get_feedback_summary(days: int = 30) -> dict:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN helpful = TRUE THEN 1 ELSE 0 END) AS positive,
                        SUM(CASE WHEN helpful = FALSE THEN 1 ELSE 0 END) AS negative
                    FROM user_feedback
                    WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
                """, (days,))
                row = cur.fetchone()
        total = row[0] or 0
        positive = row[1] or 0
        negative = row[2] or 0
        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "positive_rate": round((positive / total) * 100, 1) if total else 0.0,
        }
    except Exception:
        return {"total": 0, "positive": 0, "negative": 0, "positive_rate": 0.0}


def create_intervention(
    district: str,
    disease_key: str,
    action: str,
    status: str = "planned",
    owner: str = "",
    due_date: str = None,
    notes: str = "",
):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO official_interventions
                        (district, disease_key, action, status, owner, due_date, notes, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW())
                """, (district, disease_key, action, status, owner, due_date, notes))
            conn.commit()
    except Exception as e:
        print(f"Intervention create error: {e}")


def get_interventions(limit: int = 100) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, district, disease_key, action, status, owner, due_date, notes, updated_at
                    FROM official_interventions
                    ORDER BY updated_at DESC
                    LIMIT %s
                """, (limit,))
                rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "district": r[1],
                "disease_key": r[2],
                "action": r[3],
                "status": r[4],
                "owner": r[5],
                "due_date": str(r[6]) if r[6] else "",
                "notes": r[7] or "",
                "updated_at": r[8].strftime("%Y-%m-%d %H:%M") if r[8] else "",
            }
            for r in rows
        ]
    except Exception:
        return []


def get_hotspots(days: int = 7, min_cases: int = 2) -> list:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COALESCE(location_name, 'Unknown') AS location_name,
                        disease_key,
                        COUNT(*) AS cases,
                        ROUND(AVG(confidence)::numeric, 2) AS avg_confidence,
                        ROUND(AVG(risk_score)::numeric, 2) AS avg_risk
                    FROM detections
                    WHERE is_healthy = FALSE
                      AND created_at >= NOW() - (%s * INTERVAL '1 day')
                    GROUP BY location_name, disease_key
                    HAVING COUNT(*) >= %s
                    ORDER BY cases DESC, avg_risk DESC
                    LIMIT 30
                """, (days, min_cases))
                rows = cur.fetchall()
        return [
            {
                "location_name": r[0],
                "disease_key": r[1],
                "cases": r[2],
                "avg_confidence": float(r[3] or 0),
                "avg_risk": float(r[4] or 0),
            }
            for r in rows
        ]
    except Exception:
        return []

def get_outbreak_alerts() -> list:
    """
    Find diseases detected 3+ times in same district
    within last 7 days — trigger community alert.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT disease_key, location_name,
                           COUNT(*) as count,
                           MAX(created_at) as latest
                    FROM detections
                    WHERE is_healthy = FALSE
                      AND created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY disease_key, location_name
                    HAVING COUNT(*) >= 3
                    ORDER BY count DESC
                """)
                rows = cur.fetchall()
        return [
            {
                "disease_key":   r[0],
                "location_name": r[1],
                "count":         r[2],
                "latest":        r[3].strftime("%Y-%m-%d %H:%M"),
            }
            for r in rows
        ]
    except Exception:
        return []

def get_district_subscribers(district_name: str) -> list:
    """Get user IDs who have scanned crops in a specific district."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT user_id FROM detections
                    WHERE LOWER(location_name) LIKE LOWER(%s)
                      AND user_id > 0
                """, (f"%{district_name.split(',')[0].strip()}%",))
                return [row[0] for row in cur.fetchall()]
    except Exception:
        return []

def mark_alert_sent(disease_key: str, location_name: str):
    """Track which alerts have been sent to avoid duplicates."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sent_alerts (
                        id SERIAL PRIMARY KEY,
                        disease_key TEXT,
                        location_name TEXT,
                        sent_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(disease_key, location_name)
                    )
                """)
                cur.execute("""
                    INSERT INTO sent_alerts (disease_key, location_name)
                    VALUES (%s, %s)
                    ON CONFLICT (disease_key, location_name) DO UPDATE
                    SET sent_at = NOW()
                """, (disease_key, location_name))
            conn.commit()
    except Exception as e:
        print(f"Alert tracking error: {e}")

def was_alert_sent_recently(disease_key: str, location_name: str) -> bool:
    """Check if alert was sent in last 24 hours."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sent_alerts (
                        id SERIAL PRIMARY KEY,
                        disease_key TEXT,
                        location_name TEXT,
                        sent_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(disease_key, location_name)
                    )
                """)
                cur.execute("""
                    SELECT COUNT(*) FROM sent_alerts
                    WHERE disease_key = %s
                      AND location_name = %s
                      AND sent_at >= NOW() - INTERVAL '24 hours'
                """, (disease_key, location_name))
                return cur.fetchone()[0] > 0
    except Exception:
        return False