import google.generativeai as genai
from dotenv import load_dotenv
import os, time

load_dotenv()

def get_api_key():
    try:
        import streamlit as st
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")

genai.configure(api_key=get_api_key())

MODEL = "gemini-2.5-flash"  # or latest supported

def call_gemini(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            response = genai.GenerativeModel(MODEL).generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                time.sleep(30 * (attempt + 1))
            else:
                raise e