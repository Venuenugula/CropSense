import json
import os
import re
from utils.gemini import call_gemini
from utils.language import get_system_prompt

KB_PATH = "rag/knowledge_base/fertilizers.json"

with open(KB_PATH) as f:
    FERTILIZER_KB = json.load(f)

def find_product(query: str) -> tuple:
    """
    Find product in KB by name match.
    Returns (product_name, product_data) or (None, None)
    """
    query_lower = query.lower().strip()
    for name, data in FERTILIZER_KB.items():
        if (name.lower() in query_lower or
            query_lower in name.lower() or
            data["telugu_name"].lower() in query_lower or
            query_lower in data["telugu_name"].lower()):
            return name, data

    # fuzzy match on brand names
    for name, data in FERTILIZER_KB.items():
        for brand in data.get("available_brands", []):
            if query_lower in brand.lower() or brand.lower() in query_lower:
                return name, data

    return None, None

def calculate_dosage(product_data: dict, acres: float,
                     severity: str) -> dict:
    """Calculate exact dosage for given acres and severity."""
    ratio = product_data["mixing_ratio"].get(
        severity, product_data["mixing_ratio"]["medium"]
    )
    liters_needed = ratio.get("liters_per_acre", 200) * acres

    if "grams_per_liter" in ratio:
        total_grams = ratio["grams_per_liter"] * liters_needed
        return {
            "product_amount": f"{total_grams:.0f} గ్రాములు / grams",
            "water_amount":   f"{liters_needed:.0f} లీటర్లు / liters",
            "mix_ratio":      f"{ratio['grams_per_liter']}g per liter",
            "unit":           "grams",
        }
    elif "ml_per_liter" in ratio:
        total_ml = ratio["ml_per_liter"] * liters_needed
        return {
            "product_amount": f"{total_ml:.0f} మి.లీ / ml",
            "water_amount":   f"{liters_needed:.0f} లీటర్లు / liters",
            "mix_ratio":      f"{ratio['ml_per_liter']}ml per liter",
            "unit":           "ml",
        }
    elif "kg_per_acre" in ratio:
        total_kg = ratio["kg_per_acre"] * acres
        return {
            "product_amount": f"{total_kg:.0f} కేజీలు / kg",
            "water_amount":   "నేలలో వేయాలి / Soil application",
            "mix_ratio":      f"{ratio['kg_per_acre']} kg per acre",
            "unit":           "kg",
        }
    return {}

def generate_fertilizer_response(
    product_name: str,
    product_data: dict,
    crop: str,
    acres: float,
    severity: str,
    lang: str = "telugu"
) -> str:
    """Generate complete advisory using Gemini."""
    dosage = calculate_dosage(product_data, acres, severity)
    system = get_system_prompt(lang)

    if lang == "telugu":
        prompt = f"""
{system}

రైతు {product_name} ({product_data['telugu_name']}) గురించి అడిగాడు.

వివరాలు:
- పంట: {crop}
- ఎకరాలు: {acres}
- తీవ్రత: {severity}
- మందు రకం: {product_data['type']}
- లక్ష్య వ్యాధులు: {', '.join(product_data['target_diseases'])}
- లెక్కించిన మోతాదు: {dosage.get('product_amount', '')} — {dosage.get('water_amount', '')}
- పిచికారీ సమయం: {product_data['application_time']}
- వర్షం జాగ్రత్త: {product_data['rain_advice']}
- పంట కోత ముందు వేచి ఉండాల్సిన రోజులు: {product_data['harvest_waiting_days']} రోజులు
- కలపకూడని మందులు: {', '.join(product_data['do_not_mix_with'])}
- జాగ్రత్తలు: {product_data['safety']}
- మార్కెట్లో దొరికే పేర్లు: {', '.join(product_data['available_brands'])}

దయచేసి తెలుగులో ఈ format లో సమాధానం ఇవ్వండి:

💊 *{product_data['telugu_name']} ({product_name}) వినియోగ మార్గదర్శి*

📦 *మోతాదు ({acres} ఎకరాలకు, {severity} తీవ్రత):*
మందు మరియు నీటి పరిమాణం స్పష్టంగా చెప్పండి.

🌿 *ఏ వ్యాధులకు పనిచేస్తుంది:*
2-3 ముఖ్యమైన వ్యాధులు చెప్పండి.

⏰ *ఎప్పుడు పిచికారీ చేయాలి:*
సమయం మరియు వర్షం జాగ్రత్త చెప్పండి.

🔄 *ఎంత తరచుగా వేయాలి:*
Frequency చెప్పండి.

⚠️ *ముఖ్యమైన జాగ్రత్తలు:*
- కలపకూడని మందులు చెప్పండి
- సురక్షత చర్యలు చెప్పండి
- పంట కోత ముందు వేచి ఉండాల్సిన రోజులు చెప్పండి

🏪 *దుకాణంలో ఈ పేర్లతో అడగండి:*
Brand names చెప్పండి.
"""
    else:
        prompt = f"""
{system}

A farmer asked about {product_name}.

Details:
- Crop: {crop}
- Acres: {acres}
- Severity: {severity}
- Product type: {product_data['type']}
- Target diseases: {', '.join(product_data['target_diseases'])}
- Calculated dosage: {dosage.get('product_amount', '')} in {dosage.get('water_amount', '')}
- Application time: {product_data['application_time']}
- Rain advice: {product_data['rain_advice']}
- Pre-harvest interval: {product_data['harvest_waiting_days']} days
- Do not mix with: {', '.join(product_data['do_not_mix_with'])}
- Safety: {product_data['safety']}
- Available brands: {', '.join(product_data['available_brands'])}

Reply in this format:

💊 *{product_name} Usage Guide*

📦 *Dosage (for {acres} acres, {severity} severity):*
State product and water amounts clearly.

🌿 *Effective against:*
List 2-3 key diseases.

⏰ *When to spray:*
Timing and rain precautions.

🔄 *How often:*
Frequency.

⚠️ *Important precautions:*
- Do not mix with
- Safety measures
- Pre-harvest interval

🏪 *Ask at shop by these names:*
Brand names.
"""
    return call_gemini(prompt)


def handle_unknown_product(query: str, lang: str = "telugu") -> str:
    """Handle products not in KB using Gemini's general knowledge."""
    system = get_system_prompt(lang)
    if lang == "telugu":
        prompt = f"""
{system}

రైతు '{query}' అనే వ్యవసాయ మందు / ఎరువు గురించి అడిగాడు.
మీకు తెలిసినంతవరకు తెలుగులో వివరించండి:
- ఇది ఏ రకమైన మందు
- ఎలా వాడాలి (సాధారణ మోతాదు)
- జాగ్రత్తలు
చివరలో చెప్పండి: "ఖచ్చితమైన మోతాదుకు దయచేసి స్థానిక వ్యవసాయ నిపుణుడిని సంప్రదించండి."
"""
    else:
        prompt = f"""
{system}

A farmer asked about '{query}' — an agricultural product.
Please explain what you know:
- What type of product it is
- General usage and dosage
- Safety precautions
End with: "For exact dosage, please consult your local agriculture officer."
"""
    return call_gemini(prompt)