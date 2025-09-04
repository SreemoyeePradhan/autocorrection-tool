# model.py
import os
import re
import json
from typing import List, Dict, Any, Tuple

import google.generativeai as genai

# Prefer stable 1.5 models, with a fallback chain.
MODEL_CANDIDATES = [
    "models/gemini-1.5-flash",
    "models/gemini-1.5-pro",
    "gemini-2.0-flash-lite",  # fallback, may not be available in all regions/APIs
]

def _configure(api_key: str):
    if not api_key:
        raise ValueError("Gemini API key missing. Set GOOGLE_API_KEY in env or Streamlit secrets.")
    genai.configure(api_key=api_key)

def _try_models(prompt: str, api_key: str, max_tokens: int = 768, temperature: float = 0.4) -> str:
    _configure(api_key)
    last_err = None
    for m in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(m)
            resp = model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "top_k": 40,
                },
            )
            if hasattr(resp, "text") and resp.text:
                return resp.text
            # Fallback parse
            return str(resp)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Gemini call failed for all models. Last error: {last_err}")

def _json_from_text(text: str) -> Any:
    """
    Robustly extract JSON object/array from an LLM response.
    """
    # Try code-fence blocks first
    fence = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if fence:
        s = fence.group(1)
        try:
            return json.loads(s)
        except Exception:
            pass
    # Try to find the first top-level {} or []
    candidates = re.findall(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    for c in candidates:
        try:
            return json.loads(c)
        except Exception:
            continue
    # Last resort: try raw
    try:
        return json.loads(text)
    except Exception:
        return None

def _domain_instructions(domain_mode: str) -> str:
    modes = {
        "General English": "Use clear, natural English suitable for general audiences.",
        "Academic Writing": "Use formal academic tone, precise vocabulary, and clear structure.",
        "Business Emails": "Use professional, concise, and polite business email style.",
        "Code Comments": "Do not change code syntax. Improve surrounding prose/comments; keep technical accuracy.",
    }
    return modes.get(domain_mode, modes["General English"])

def _style_instructions(style_mode: str) -> str:
    styles = {
        "neutral": "Keep the style neutral.",
        "casual": "Use a conversational, approachable tone.",
        "formal": "Use a formal, professional tone.",
        "persuasive": "Strengthen rhetorical clarity and persuasive impact.",
        "concise": "Reduce verbosity; keep sentences short and direct.",
    }
    return styles.get(style_mode, "Keep the style neutral.")

def build_prompt(
    text: str,
    language: str,
    domain_mode: str,
    style_mode: str,
    preserve_terms: List[str],
    dictionary_tags: List[str],
    explain: bool,
    want_translation: bool,
    n_suggestions: int,
) -> str:
    preserve_clause = ""
    if preserve_terms:
        preserve_clause = (
            "Preserve these terms exactly (spelling/casing unchanged): "
            + ", ".join(sorted(set(t.strip() for t in preserve_terms if t.strip())))
            + ".\n"
        )

    dict_clause = ""
    if dictionary_tags:
        dict_clause = (
            "Respect specialized terminology for these domains: "
            + ", ".join(dictionary_tags)
            + ". Do not 'correct' legitimate terms in these domains.\n"
        )

    lang_clause = f"Assume the text is in {language}. " if language and language.lower() != "auto" else ""

    prompt = f"""
You are an expert copy editor.

{lang_clause}{_domain_instructions(domain_mode)} {_style_instructions(style_mode)}
{preserve_clause}{dict_clause}

TASKS:
1) Correct grammar, spelling, punctuation, and fluency.
2) Keep meaning intact and avoid changing any terms listed to preserve.
3) If the text includes code in triple backticks, DO NOT modify code — only improve surrounding prose.
4) Return {n_suggestions} distinct suggestions.
5) For each suggestion, include:
   - "corrected": the full corrected text (same language as input unless told otherwise),
   - "confidence": a float from 0.0 to 1.0 for how confident you are overall,
   - "explanations": a list of objects with fields:
       * "before": the original fragment
       * "after": the corrected fragment
       * "reason": a short explanation
   - "language": the detected language name
   {"- \"translation_en\": the English translation of the corrected text" if want_translation else ""}

RESPONSE FORMAT (MANDATORY):
Return a single JSON array where each item is an object with the keys above.
Do not include any commentary outside the JSON.

TEXT TO CORRECT:
{text}
""".strip()
    return prompt

def get_gemini_analysis(
    text: str,
    api_key: str,
    preserve_terms: List[str],
    language: str = "Auto",
    domain_mode: str = "General English",
    style_mode: str = "neutral",
    dictionary_tags: List[str] = None,
    explain: bool = True,
    want_translation: bool = False,
    n_suggestions: int = 1,
    temperature: float = 0.4,
) -> List[Dict[str, Any]]:
    dictionary_tags = dictionary_tags or []
    prompt = build_prompt(
        text=text,
        language=language,
        domain_mode=domain_mode,
        style_mode=style_mode,
        preserve_terms=preserve_terms or [],
        dictionary_tags=dictionary_tags,
        explain=explain,
        want_translation=want_translation,
        n_suggestions=n_suggestions,
    )
    raw = _try_models(prompt, api_key, temperature=temperature)
    data = _json_from_text(raw)
    if not isinstance(data, list):
        # fallback: wrap as single suggestion
        data = [{"corrected": raw.strip(), "confidence": 0.7, "explanations": [], "language": language or "Auto"}]
    # sanitize
    cleaned = []
    for item in data:
        if not isinstance(item, dict):
            continue
        cleaned.append({
            "corrected": item.get("corrected", "").strip(),
            "confidence": float(item.get("confidence", 0.7)),
            "explanations": item.get("explanations", []),
            "language": item.get("language", language or "Auto"),
            "translation_en": item.get("translation_en", None),
        })
    return cleaned

def detect_language(text: str, api_key: str) -> str:
    prompt = f"Detect the language of this text and reply with language name only:\n{text}"
    raw = _try_models(prompt, api_key, temperature=0.0)
    return raw.strip()
