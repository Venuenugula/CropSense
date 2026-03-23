from google import genai
from dotenv import load_dotenv
import os, time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

load_dotenv()

def get_api_key():
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")

MODEL = "gemini-2.5-flash"  # or latest supported
_client = genai.Client(api_key=get_api_key())
REQUEST_TIMEOUT_SECONDS = 25
FALLBACK_RESPONSE = (
    "⚠️ AI service is temporarily slow. "
    "Please try again in a moment with a shorter question."
)

def call_gemini(
    prompt: str,
    retries: int = 3,
    timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
) -> str:
    last_error = None
    for attempt in range(retries):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    _client.models.generate_content,
                    model=MODEL,
                    contents=prompt,
                )
                response = future.result(timeout=timeout_seconds)

            text = (response.text or "").strip()
            if not text:
                raise ValueError("Empty response from Gemini")
            return text
        except FuturesTimeoutError:
            last_error = TimeoutError(
                f"Gemini request timed out after {timeout_seconds}s"
            )
        except Exception as e:
            last_error = e
            if "429" in str(e) and attempt < retries - 1:
                time.sleep(30 * (attempt + 1))
            else:
                break

    print(f"Gemini fallback triggered: {last_error}")
    return FALLBACK_RESPONSE