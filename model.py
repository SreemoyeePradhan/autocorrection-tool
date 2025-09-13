import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()

# Configure Gemini API
def _configure():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("❌ Please set your GOOGLE_API_KEY environment variable.")
    genai.configure(api_key=api_key)

# Generate corrected text in selected style and language
def get_corrections(text: str, style: str, language: str) -> str:
    _configure()
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""Correct and improve the following text.
Apply a {style} style while keeping the meaning intact.
Provide the output in {language} language.

Text: {text}"""
    
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else text
