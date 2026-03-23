from google import genai
from dotenv import load_dotenv
import os, time

load_dotenv()

def get_api_key():
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"  # or latest supported
_client = genai.Client(api_key=get_api_key())

def call_gemini(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return (response.text or "").strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                time.sleep(30 * (attempt + 1))
            else:
                raise e