# app.py
import os
import streamlit as st
from dotenv import load_dotenv

from model import get_gemini_analysis, detect_language
from utils import (
    preprocess_text, mask_code_blocks, unmask_code_blocks,
    highlight_changes, diff_pairs, apply_selected_edits,
    export_text, load_text_from_file, build_preserve_terms, tts_gtts
)

# ------------------ App Setup ------------------
load_dotenv()
st.set_page_config(page_title="Gemini Autocorrect Pro", layout="wide")
st.title("📝 Gemini Autocorrect Pro")

# ------------------ Sidebar: Theming & Settings ------------------
st.sidebar.header("⚙️ Settings")

theme = st.sidebar.selectbox("Theme", ["Light", "Dark", "Solarized"])
THEME_CSS = {
    "Light": """
    <style>
    body, .stMarkdown { color: #111; }
    .suggest { color: #b91c1c; } .insert { color: #1d4ed8; } .del { color: #6b7280; text-decoration: line-through; }
    </style>
    """,
    "Dark": """
    <style>
    body, .stMarkdown { color: #e5e7eb; background: #0b1220; }
    .suggest { color: #f87171; } .insert { color: #93c5fd; } .del { color: #9ca3af; text-decoration: line-through; }
    </style>
    """,
    "Solarized": """
    <style>
    body, .stMarkdown { color: #073642; background: #fdf6e3; }
    .suggest { color: #dc322f; } .insert { color: #268bd2; } .del { color: #586e75; text-decoration: line-through; }
    </style>
    """,
}
st.markdown(THEME_CSS[theme], unsafe_allow_html=True)

# Runtime toggles
realtime = st.sidebar.toggle("⚡ Real-time Suggestions", value=False)
show_diff = st.sidebar.toggle("🧭 Diff Viewer (side-by-side)", value=True)
show_explanations = st.sidebar.toggle("💡 Explain Corrections", value=True)
show_translation = st.sidebar.toggle("🌐 Show English Translation (if non-English)", value=True)
n_suggestions = st.sidebar.slider("Number of suggestions", 1, 3, 1)
temperature = st.sidebar.slider("Creativity (temperature)", 0.0, 1.0, 0.4, 0.1)

# Domain & style
domain_mode = st.sidebar.selectbox(
    "Domain Mode",
    ["General English", "Academic Writing", "Business Emails", "Code Comments"],
)
style_mode = st.sidebar.selectbox(
    "Rephrase Style", ["neutral", "casual", "formal", "persuasive", "concise"]
)

# Language & dictionaries
lang_option = st.sidebar.selectbox("Language", ["Auto", "English", "Spanish", "French", "German"])
dict_tags = st.sidebar.multiselect("Technical Dictionaries", ["Medical", "Legal", "Coding"])
user_terms_input = st.sidebar.text_input("Custom terms (comma-separated)", "TensorFlow, PyTorch, API")
uploaded_glossary_file = st.sidebar.file_uploader("Upload glossary (.txt)", type=["txt"])
uploaded_glossary = ""
if uploaded_glossary_file:
    uploaded_glossary = uploaded_glossary_file.read().decode("utf-8", errors="ignore")

# API key
api_key = os.getenv("GOOGLE_API_KEY", "")
if not api_key:
    api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Stored only in memory for this session.")

# ------------------ Main Editor ------------------
if "history" not in st.session_state:
    st.session_state["history"] = []
if "user_text" not in st.session_state:
    st.session_state["user_text"] = ""
if "last_suggestions" not in st.session_state:
    st.session_state["last_suggestions"] = []

st.session_state["user_text"] = st.text_area(
    "✍️ Enter text (code blocks in triple backticks ```...``` will be preserved):",
    value=st.session_state["user_text"], height=220, key="text_editor"
)

# Speech input (optional)
st.write("🎤 **Speech Input** (optional): upload audio (.wav/.flac) and we’ll transcribe if `speech_recognition` is installed.")
audio_file = st.file_uploader("Upload audio for transcription", type=["wav", "flac"], accept_multiple_files=False)
if audio_file is not None:
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)
        # Try Google's free recognizer (internet required); if fails, show message
        try:
            transcript = r.recognize_google(audio)
            st.session_state["user_text"] = (st.session_state["user_text"] + " " + transcript).strip()
            st.success("Transcription added to the editor.")
        except Exception as e:
            st.warning(f"Could not transcribe audio with Google recognizer: {e}")
    except Exception:
        st.info("Install optional dependency for STT: pip install SpeechRecognition")

# Build preserve terms list
user_terms = [t.strip() for t in user_terms_input.split(",") if t.strip()]
preserve_terms = build_preserve_terms(user_terms, dict_tags, uploaded_glossary)

# ------------------ Correction Runner ------------------
def run_analysis():
    if not api_key:
        st.error("API key is required.")
        return []

    raw_text = st.session_state["user_text"]
    if not raw_text.strip():
        return []

    # Preserve code blocks
    masked, blocks = mask_code_blocks(raw_text)
    prepped = preprocess_text(masked)

    with st.spinner("Generating suggestions..."):
        results = get_gemini_analysis(
            text=prepped,
            api_key=api_key,
            preserve_terms=preserve_terms,
            language=lang_option,
            domain_mode=domain_mode,
            style_mode=style_mode,
            dictionary_tags=dict_tags,
            explain=show_explanations,
            want_translation=show_translation,
            n_suggestions=n_suggestions,
            temperature=temperature,
        )

    # Unmask code blocks in results
    for r in results:
        r["corrected"] = unmask_code_blocks(r.get("corrected", ""), blocks)
        if r.get("translation_en"):
            r["translation_en"] = unmask_code_blocks(r["translation_en"], blocks)

    if results:
        st.session_state["last_suggestions"] = results
        st.session_state["history"].append(results[0]["corrected"])
    return results

# Trigger
results = []
if realtime and st.session_state["user_text"].strip():
    results = run_analysis()
elif st.button("✨ Get Suggestions"):
    results = run_analysis()

# ------------------ Display Suggestions & Inline Editing ------------------
if results:
    for idx, res in enumerate(results, start=1):
        corrected = res.get("corrected", "")
        confidence = res.get("confidence", 0.7)
        language_reported = res.get("language", "Auto")
        explanations = res.get("explanations", [])

        st.markdown(f"### Suggestion {idx}")
        st.progress(min(max(confidence, 0.0), 1.0), text=f"Confidence: {confidence:.2f}")

        # Diff Viewer
        if show_diff:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original**")
                st.write(st.session_state["user_text"])
            with col2:
                st.markdown("**Corrected**")
                st.markdown(highlight_changes(st.session_state["user_text"], corrected), unsafe_allow_html=True)
        else:
            st.markdown("**Preview**")
            st.markdown(highlight_changes(st.session_state["user_text"], corrected), unsafe_allow_html=True)

        # Inline Editing: accept/reject per edit
        st.markdown("**Inline Editing — accept/reject individual changes:**")
        edits = diff_pairs(st.session_state["user_text"], corrected)
        accept_mask = []
        if edits:
            for i, e in enumerate(edits, start=1):
                before = " ".join(e["before_tokens"])
                after = " ".join(e["after_tokens"])
                colA, colB, colC = st.columns([3, 3, 1])
                with colA:
                    st.markdown(f"**Before:** {before if before else '∅'}")
                with colB:
                    st.markdown(f"**After:** {after if after else '∅'}")
                with colC:
                    accept = st.checkbox("Accept", key=f"acc_{idx}_{i}", value=True)
                    accept_mask.append(accept)

            # Apply selected edits to reconstruct text
            revised = apply_selected_edits(st.session_state["user_text"], corrected, accept_mask)
        else:
            revised = corrected

        col_ok, col_copy, col_dl_txt, col_dl_docx, col_tts = st.columns([1, 1, 1, 1, 1])
        with col_ok:
            if st.button(f"✅ Apply Suggestion {idx}"):
                st.session_state["user_text"] = revised
                st.rerun()
        with col_copy:
            st.code(revised, language="text")
        with col_dl_txt:
            st.download_button("💾 Download .txt", data=export_text(revised, "txt"), file_name="corrected.txt")
        with col_dl_docx:
            try:
                st.download_button(
                    "📄 Download .docx",
                    data=export_text(revised, "docx"),
                    file_name="corrected.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            except Exception as e:
                st.info(str(e))
        with col_tts:
            tts_buf, tts_err = tts_gtts(revised)
            if tts_buf:
                st.download_button("🔊 Download TTS (mp3)", data=tts_buf, file_name="speech.mp3", mime="audio/mpeg")
            else:
                st.caption(tts_err or "TTS unavailable.")

        # Explanations
        if show_explanations and explanations:
            st.markdown("**Why these corrections?**")
            for ex in explanations:
                before = ex.get("before", "")
                after = ex.get("after", "")
                reason = ex.get("reason", "")
                st.markdown(f"- `{before}` → `{after}` — {reason}")

        # Language / Translation
        st.caption(f"Detected language: {language_reported}")
        if show_translation and res.get("translation_en"):
            st.markdown("**English translation of corrected text:**")
            st.success(res["translation_en"])

# ------------------ Batch Processing ------------------
st.markdown("---")
st.subheader("📦 Batch Processing (.txt/.docx)")
batch_file = st.file_uploader("Upload a document to correct", type=["txt", "docx"])
if batch_file is not None:
    text_in = load_text_from_file(batch_file)
    st.text_area("File preview", text_in[:5000], height=180, disabled=True)

    if st.button("🚀 Run Batch Correction"):
        if not api_key:
            st.error("API key is required.")
        else:
            segments = [seg.strip() for seg in text_in.split("\n\n") if seg.strip()]
            corrected_segments = []
            for seg in segments:
                masked, blocks = mask_code_blocks(seg)
                prepped = preprocess_text(masked)
                out = get_gemini_analysis(
                    text=prepped,
                    api_key=api_key,
                    preserve_terms=preserve_terms,
                    language=lang_option,
                    domain_mode=domain_mode,
                    style_mode=style_mode,
                    dictionary_tags=dict_tags,
                    explain=False,
                    want_translation=False,
                    n_suggestions=1,
                )
                corr = out[0]["corrected"] if out else seg
                corr = unmask_code_blocks(corr, blocks)
                corrected_segments.append(corr)
            final_doc = "\n\n".join(corrected_segments)
            st.markdown("**Batch Result (preview):**")
            st.text_area("Corrected Document", final_doc[:10000], height=240)
            st.download_button("💾 Download .txt", data=export_text(final_doc, "txt"), file_name="batch_corrected.txt")
            try:
                st.download_button(
                    "📄 Download .docx",
                    data=export_text(final_doc, "docx"),
                    file_name="batch_corrected.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            except Exception as e:
                st.info(str(e))

# ------------------ History ------------------
st.markdown("---")
st.subheader("📜 History")
if st.session_state["history"]:
    for i, h in enumerate(reversed(st.session_state["history"][-6:]), 1):
        st.markdown(f"**Version {len(st.session_state['history']) - i + 1}:**")
        st.text_area(f"v{len(st.session_state['history']) - i + 1}", h, height=100, disabled=True)
        if st.button(f"↩️ Restore v{len(st.session_state['history']) - i + 1}"):
            st.session_state["user_text"] = h
            st.rerun()
else:
    st.info("No history yet. Generate some suggestions first! 😊")
