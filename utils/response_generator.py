from utils.gemini import call_gemini
from utils.language import get_system_prompt
from rag.retriever import retrieve_treatment

def generate_disease_response(
    disease_key: str,
    confidence: float,
    weather_risk: dict,
    lang: str = "telugu"
) -> str:
    info = retrieve_treatment(disease_key)
    if not info:
        return "వ్యాధి గుర్తించబడలేదు. దయచేసి స్పష్టమైన ఫోటో పంపండి." \
               if lang == "telugu" else \
               "Disease not identified. Please send a clearer photo."

    system = get_system_prompt(lang)
    risk_level = weather_risk.get("risk_level", "Unknown")
    risk_reason = weather_risk.get("reason", "")

    if lang == "telugu":
        prompt = f"""
{system}

రైతు పంట ఫోటో విశ్లేషించబడింది. దిగువ సమాచారం ఆధారంగా తెలుగులో సమాధానం ఇవ్వండి:

వ్యాధి: {info.get('telugu_name', disease_key)} 
నమ్మకం: {confidence:.0f}%
పంట: {info.get('crop', '')}
తీవ్రత: {info.get('severity', '')}
లక్షణాలు: {', '.join(info.get('symptoms', []))}
చికిత్స: {' | '.join(info.get('treatment', []))}
నివారణ: {' | '.join(info.get('prevention', []))}
వ్యాప్తి పరిస్థితులు: {', '.join(info.get('spread_conditions', []))}
7 రోజుల వ్యాప్తి ప్రమాదం: {risk_level}
కారణం: {risk_reason}

దయచేసి ఈ format లో సమాధానం ఇవ్వండి:

🌾 *పంట వ్యాధి గుర్తింపు*
వ్యాధి పేరు మరియు నమ్మకం శాతం చెప్పండి.

🔍 *లక్షణాలు*
2-3 ముఖ్యమైన లక్షణాలు సులభంగా వివరించండి.

💊 *చికిత్స*
దుకాణంలో దొరికే మందుల పేర్లతో సహా step-by-step చికిత్స చెప్పండి.

🛡️ *నివారణ*
2-3 నివారణ చర్యలు చెప్పండి.

⛅ *వ్యాప్తి ప్రమాదం (7 రోజులు)*
{risk_level} - కారణం వివరించండి మరియు ఏమి చేయాలో చెప్పండి.
"""
    else:
        prompt = f"""
{system}

A farmer's crop photo has been analyzed. Reply in simple English based on:

Disease: {disease_key.replace('___', ' - ').replace('_', ' ')}
Confidence: {confidence:.0f}%
Crop: {info.get('crop', '')}
Severity: {info.get('severity', '')}
Symptoms: {', '.join(info.get('symptoms', []))}
Treatment: {' | '.join(info.get('treatment', []))}
Prevention: {' | '.join(info.get('prevention', []))}
Spread conditions: {', '.join(info.get('spread_conditions', []))}
7-day spread risk: {risk_level}
Reason: {risk_reason}

Reply in this format:

🌾 *Crop Disease Detected*
State the disease name and confidence clearly.

🔍 *Symptoms*
Explain 2-3 key symptoms in simple words.

💊 *Treatment*
Give step-by-step treatment with exact medicine names and dosage.

🛡️ *Prevention*
Give 2-3 prevention tips.

⛅ *Spread Risk (7 days)*
{risk_level} - Explain why and what the farmer should do urgently.
"""

    return call_gemini(prompt)


def generate_healthy_response(
    crop_name: str,
    confidence: float,
    lang: str = "telugu"
) -> str:
    if lang == "telugu":
        return (
            f"✅ *మీ పంట ఆరోగ్యంగా ఉంది!*\n\n"
            f"🌾 పంట: {crop_name}\n"
            f"నమ్మకం: {confidence:.0f}%\n\n"
            f"మీ పంటలో ఎటువంటి వ్యాధి లక్షణాలు కనిపించలేదు. "
            f"ప్రతి వారం పంటను పరిశీలించండి మరియు సరైన నీటి తడి ఇవ్వండి."
        )
    else:
        return (
            f"✅ *Your crop looks healthy!*\n\n"
            f"🌾 Crop: {crop_name}\n"
            f"Confidence: {confidence:.0f}%\n\n"
            f"No disease symptoms detected. "
            f"Keep monitoring weekly and maintain proper irrigation."
        )