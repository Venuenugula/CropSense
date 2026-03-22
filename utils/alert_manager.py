import asyncio
from db.models import (
    get_outbreak_alerts,
    get_district_subscribers,
    mark_alert_sent,
    was_alert_sent_recently,
)

def build_alert_message(alert: dict, lang: str = "telugu") -> str:
    """Build community alert message."""
    disease = alert["disease_key"].replace("___", " — ").replace("_", " ")
    location = alert["location_name"]
    count    = alert["count"]

    if lang == "telugu":
        return (
            f"⚠️ <b>వ్యాధి వ్యాప్తి హెచ్చరిక!</b>\n\n"
            f"🌾 <b>వ్యాధి:</b> {disease}\n"
            f"📍 <b>ప్రాంతం:</b> {location}\n"
            f"📊 <b>నిర్ధారణలు:</b> గత 7 రోజుల్లో {count} మంది రైతులు\n\n"
            f"⚠️ మీ పంట జాగ్రత్తగా పరిశీలించండి.\n"
            f"అనుమానం వస్తే వెంటనే ఫోటో పంపండి.\n\n"
            f"🌱 Rythu Mitra — రైతు మిత్ర"
        )
    else:
        return (
            f"⚠️ <b>Disease Outbreak Alert!</b>\n\n"
            f"🌾 <b>Disease:</b> {disease}\n"
            f"📍 <b>Area:</b> {location}\n"
            f"📊 <b>Detections:</b> {count} farmers in last 7 days\n\n"
            f"⚠️ Inspect your crops carefully.\n"
            f"Send a photo immediately if you see symptoms.\n\n"
            f"🌱 Rythu Mitra"
        )

async def send_community_alerts(bot):
    """Check for outbreaks and send alerts to affected farmers."""
    alerts = get_outbreak_alerts()
    sent   = 0

    for alert in alerts:
        disease_key   = alert["disease_key"]
        location_name = alert["location_name"]

        # Skip if already sent in last 24 hours
        if was_alert_sent_recently(disease_key, location_name):
            continue

        # Get subscribers in that district
        subscribers = get_district_subscribers(location_name)
        if not subscribers:
            continue

        # Build message
        message = build_alert_message(alert, lang="telugu")

        # Send to all subscribers
        success = 0
        for user_id in subscribers:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="HTML"
                )
                success += 1
                await asyncio.sleep(0.1)  # avoid flood limits
            except Exception as e:
                print(f"Alert to {user_id} failed: {e}")

        if success > 0:
            mark_alert_sent(disease_key, location_name)
            sent += success
            print(f"Alert sent: {disease_key} in {location_name} → {success} farmers")

    return sent