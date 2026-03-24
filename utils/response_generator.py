from __future__ import annotations

from utils.gemini import call_gemini
from utils.language import get_system_prompt
from rag.retriever import retrieve_treatment


def _split_retrieval(info: dict) -> tuple[dict, dict]:
    """KB copy may include _retrieval; keep prompts clean."""
    if not info:
        return {}, {}
    meta = dict(info.get("_retrieval") or {})
    clean = {k: v for k, v in info.items() if k != "_retrieval"}
    return clean, meta


def _confidence_label(confidence: float, lang: str) -> str:
    """Human-readable certainty tier (image model + KB alignment)."""
    if lang == "telugu":
        if confidence >= 85:
            return "అధిక (~ఖచ్చితత్వం)"
        if confidence >= 70:
            return "మధ్యస్థ"
        return "మితమైన — మళ్లీ ఫోటో పంపడం మంచిది"
    if confidence >= 85:
        return "High (strong match)"
    if confidence >= 70:
        return "Medium"
    return "Moderate — consider a clearer photo if unsure"


def _action_window(severity: str, lang: str) -> str:
    sev = (severity or "").strip().lower()
    if lang == "telugu":
        if sev in ("very high", "high"):
            return "తీవ్రత ఎక్కువ అయితే 24–48 గంటల్లోపు చర్య ఉత్తమం"
        if sev == "medium":
            return "మధ్యస్థ తీవ్రత అయితే 3–5 రోజుల్లోపు చర్య ప్రయోజనకరం"
        return "ఈ వారంలో పంటను మళ్లీ పరిశీలించి అవసరమైతే చర్య తీసుకోండి"
    if sev in ("very high", "high"):
        return "For high severity, acting within 24–48 hours usually helps most"
    if sev == "medium":
        return "For medium severity, plan action within 3–5 days"
    return "Re-scout this week and act if symptoms spread"


def _alternatives_line(top_predictions: list | None, disease_key: str, lang: str) -> str:
    if not top_predictions or len(top_predictions) < 2:
        return ""
    p2 = top_predictions[1]
    name = p2["disease"].replace("___", " — ").replace("_", " ")
    c = p2.get("confidence", 0)
    if lang == "telugu":
        return f"రెండవ సంభావ్యత: {name} (~{c:.0f}%)"
    return f"Next likely: {name} (~{c:.0f}%)"


def _trust_header(
    info: dict,
    disease_key: str,
    confidence: float,
    lang: str,
    retrieval_meta: dict,
    top_predictions: list | None,
) -> str:
    clean_name_en = disease_key.replace("___", " — ").replace("_", " ")
    name_te = info.get("telugu_name") or clean_name_en
    symptoms = info.get("symptoms") or []
    symptom_pick = symptoms[:3]
    symptom_str_te = ", ".join(symptom_pick) if symptom_pick else "సూచించబడలేదు"
    symptom_str_en = ", ".join(symptom_pick) if symptom_pick else "Not listed"
    band = _confidence_label(confidence, lang)
    sev = info.get("severity", "") or ""
    window = _action_window(sev, lang)
    alt = _alternatives_line(top_predictions, disease_key, lang)
    via = retrieval_meta.get("via", "kb_direct")

    if lang == "telugu":
        lines = [
            "📌 *నిర్ధారణ సారాంశం (మీ ప్రశ్న: “ఇలా చేస్తే పంట బాగుండుతుందా?”)*",
            f"• *వ్యాధి:* {name_te} *({confidence:.0f}%)*",
            f"• *నమ్మకం:* {band}",
            f"• *ఎందుకు ఇలా అనుకుంటున్నాం:* మా గుర్తింపు + నిర్వచన గ్రంథం లో *ముఖ్య లక్షణాలు* — {symptom_str_te}",
            f"• *ఎప్పుడు చర్య:* {window}",
        ]
        if alt:
            lines.append(f"• *ఇతర సంభావ్యత:* {alt}")
        if via == "similarity":
            lines.append(
                "• ⚠️ *గమనిక:* ఈ సారి సూచన *సారూప్య శోధన* ద్వారా వచ్చింది — *తప్పుడు జంట* ఉండవచ్చు; స్థానిక కృషి అధికారితో నిర్ధారించుకోండి."
            )
        lines.append("")
        lines.append(
            "*ముఖ్యం:* AI హామీ ఇవ్వదు; *సమయానికి చర్య + స్థానిక ధృవీకరణ* ప్రమాదాన్ని తగ్గిస్తాయి."
        )
        return "\n".join(lines)

    lines = [
        '📌 *Diagnosis summary (your question: "If I follow this, is my crop safer?")*',
        f"• *Disease:* {clean_name_en} *({confidence:.0f}%)*",
        f"• *Confidence:* {band}",
        f"• *Why we think so:* model label + reference guide *typical signs* — {symptom_str_en}",
        f"• *When to act:* {window}",
    ]
    if alt:
        lines.append(f"• *Alternative to rule out:* {alt}")
    if via == "similarity":
        lines.append(
            "• ⚠️ *Note:* advice came from *similarity search* — *wrong twin* diseases possible; confirm with an agronomist."
        )
    lines.append("")
    lines.append(
        "*Important:* we cannot guarantee outcomes; *timely action + local verification* reduces risk."
    )
    return "\n".join(lines)


def _trust_footer(lang: str) -> str:
    if lang == "telugu":
        return (
            "\n\n──────────\n"
            "🤝 *మానవ ధృవీకరణ / సురక్షత*\n"
            "• ఇది *AI సాధనం* — తప్పు ఉండవచ్చు.\n"
            "• *మందు పేరు, మోతాదు, స్ప్రే విధానం* తప్పనిసరిగా *స్థానిక కృషి విస్తరణ అధికారి / KVK / లేబ్* ద్వారా నిర్ధారించుకోండి.\n"
            "• *పంట భద్రత* = ఫోటో నాణ్యత + ఫీల్డ్ స్కౌటింగ్ + లేబుల్ చదవడం.\n"
            "• ప్రాంతానికి అనుగుణ ఉత్పత్తులు మరియు నిషేధాలను పాటించండి (Telangana / India)."
        )
    return (
        "\n\n──────────\n"
        "🤝 *Human check / safety*\n"
        "• This is *AI assistance* — it can be wrong.\n"
        "• *Product names, doses, and spray timing* must be *verified* with a local agronomist, KVK, or plant clinic.\n"
        "• *Crop safety* depends on photo quality, field scouting, and label instructions.\n"
        "• Use *region-approved* products and follow local regulations (e.g. India / your state)."
    )


def generate_disease_response(
    disease_key: str,
    confidence: float,
    weather_risk: dict,
    lang: str = "telugu",
    top_predictions: list | None = None,
) -> str:
    info_raw = retrieve_treatment(disease_key)
    info, retrieval_meta = _split_retrieval(info_raw)
    if not info:
        return "వ్యాధి గుర్తించబడలేదు. దయచేసి స్పష్టమైన ఫోటో పంపండి." \
               if lang == "telugu" else \
               "Disease not identified. Please send a clearer photo."

    system = get_system_prompt(lang)
    risk_level = weather_risk.get("risk_level", "Unknown")
    risk_reason = weather_risk.get("reason", "")
    treatment_lines = " | ".join(info.get("treatment", []))
    via = retrieval_meta.get("via", "kb_direct")

    trust_block = _trust_header(
        info, disease_key, confidence, lang, retrieval_meta, top_predictions
    )

    rag_note = ""
    if lang == "telugu":
        rag_note = (
            "సూచనల మూలం: క్యూరేట్ చేసిన పంట వ్యాధి గైడ్ (నమూనా) + వాతావరణ ప్రమాదం. "
            "ఇతర మందులను కల్పించకూడదు."
            if via == "kb_direct" else
            "సూచనల మూలం: *సారూప్య శోధన* — అదనపు జాగ్రత్త; స్థానిక నిపుణుడి ధృవీకరణ తప్పనిసరి."
        )
    else:
        rag_note = (
            "Knowledge source: curated crop-disease guide (reference) + weather risk. "
            "Do not invent pesticides beyond the Treatment list."
            if via == "kb_direct" else
            "Knowledge source: *similarity retrieval* — be conservative; local expert verification is required."
        )

    if lang == "telugu":
        prompt = f"""
{system}

రైతు పంట ఫోటో విశ్లేషించబడింది. {rag_note}

దిగువ *నిజమైన డేటా* ఆధారంగా తెలుగులో జవాబు ఇవ్వండి. *చికిత్స* లో ఉన్న మందుల పేర్లను మాత్రమే ఉపయోగించండి — కొత్త పేర్లను కల్పించవద్దు.

వ్యాధి కీ: {disease_key}
నమ్మకం: {confidence:.0f}%
పంట: {info.get('crop', '')}
తీవ్రత: {info.get('severity', '')}
లక్షణాలు: {', '.join(info.get('symptoms', []))}
చికిత్స: {treatment_lines}
నివారణ: {' | '.join(info.get('prevention', []))}
వ్యాప్తి పరిస్థితులు: {', '.join(info.get('spread_conditions', []))}
7 రోజుల వ్యాప్తి ప్రమాదం: {risk_level}
కారణం: {risk_reason}

దయచేసి ఈ భాగాలతో సమాధానం ఇవ్వండి (సులభ తెలుగు):

🌾 *ఈ సలహా అర్థం*
1–2 వాక్యాల్లో: "ఈ తీవ్రతతో *సమయానికి చర్య* తీసుకుంటే ప్రమాదం తగ్గే అవకాశం ఉంటుంది" — *హామీ ఇవ్వకండి*.

🔍 *లక్షణాలు (ఫీల్డ్‌లో చూడండి)*
2–3 బిందువులు — పై లక్షణాలతో సరిపోలుతున్నాయో చెప్పండి.

💊 *చికిత్స (మోతాదు ధృవీకరణ తప్పనిసరి)*
పై "చికిత్స" లో ఉన్న *అదే* మందు పేర్లతో దశలవారీగా రాయండి; కొత్త ఉత్పత్తులు చేర్చవద్దు.

🛡️ *నివారణ*
2–3 చర్యలు.

⛅ *వ్యాప్తి ప్రమాదం (7 రోజులు)*
{risk_level} — తవ్వరగా ఏమి చేయాలి (సాధారణ మార్గదర్శకం).

చివరగా ఒక వాక్యం: *స్థానిక కృషి అధికారిని / KVK సంప్రదించి మందు సలహా ధృవీకరించుకోండి.*
"""
    else:
        prompt = f"""
{system}

A farmer's crop photo was analyzed. {rag_note}

Reply in simple English using only the *real data* below. For *Treatment*, use *only* product names from the Treatment list — do not invent new products.

Disease key: {disease_key}
Confidence: {confidence:.0f}%
Crop: {info.get('crop', '')}
Severity: {info.get('severity', '')}
Symptoms: {', '.join(info.get('symptoms', []))}
Treatment: {treatment_lines}
Prevention: {' | '.join(info.get('prevention', []))}
Spread conditions: {', '.join(info.get('spread_conditions', []))}
7-day spread risk: {risk_level}
Reason: {risk_reason}

Use these sections:

🌾 *What this means for your crop*
1–2 sentences: timely action *usually reduces risk* when severity is higher — *never* promise the crop is "safe".

🔍 *What to look for in the field*
2–3 bullets tying to the symptoms above.

💊 *Treatment (dose must be verified locally)*
Step-by-step using *only* names from the Treatment list.

🛡️ *Prevention*
2–3 tips.

⛅ *Spread risk (7 days)*
{risk_level} — practical urgency (guidance only).

End with one line: *Confirm products and doses with a local agronomist / KVK before spraying.*
"""

    body = call_gemini(prompt)
    return trust_block + "\n\n" + body + _trust_footer(lang)


def generate_healthy_response(
    crop_name: str,
    confidence: float,
    lang: str = "telugu"
) -> str:
    band = _confidence_label(confidence, lang)
    if lang == "telugu":
        return (
            f"✅ *మీ పంట ఆరోగ్యంగా కనిపిస్తోంది*\n\n"
            f"🌾 పంట: {crop_name}\n"
            f"నమ్మకం: {confidence:.0f}% ({band})\n\n"
            f"ఈ ఫోటో ఆధారంగా స్పష్టమైన వ్యాధి లక్షణాలు కనిపిలేదు. "
            f"అయినా కొన్నిసార్లు తక్కువ కోణం/నెమ్మది ప్రారంభ లక్షణాలు మిస్ అవుతాయి — "
            f"అనుమానం ఉంటే మరో కోణం ఫోటో పంపండి లేదా పొలంలో పరిశీలించండి.\n\n"
            f"ఆరోగ్యంగా పెట్టుకోవడానికి వారపు పరిశీలన మరియు సరైన తడి కొనసాగించండి."
        )
    return (
        f"✅ *Your crop looks healthy on this photo*\n\n"
        f"🌾 Crop: {crop_name}\n"
        f"Confidence: {confidence:.0f}% ({band})\n\n"
        f"No clear disease pattern was detected on this image. "
        f"Poor angles or very early symptoms can still be missed — "
        f"send another angle or scout the field if unsure.\n\n"
        f"Keep weekly monitoring and proper irrigation."
    )
