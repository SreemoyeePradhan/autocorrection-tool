import streamlit as st
from model import get_corrections
from utils import LABELS, apply_theme, highlight_changes
import pyperclip

# Initialize session
if "corrected_text" not in st.session_state:
    st.session_state["corrected_text"] = ""

# Sidebar - Settings
st.sidebar.title("SETTINGS")

# Language Selection
language = st.sidebar.selectbox("LANGUAGE", list(LABELS.keys()))
labels = LABELS[language]

# Theme Toggle (Light/Dark)
theme = st.sidebar.toggle("🌗 Dark Mode", value=True)  # default to Light
apply_theme("Dark" if theme else "Light")

# Style Selection
style = st.sidebar.selectbox(labels["style"], labels["style_options"])

# Input Section
st.title("AUTOCORRECT TOOL")
user_text = st.text_area(labels["enter_text"], placeholder=labels["enter_text_placeholder"], height=200)

# Correct Button
if st.button(labels["correct_text"]):
    if not user_text.strip():
        st.warning(labels["empty_warning"])
    else:
        with st.spinner("Correcting..."):
            corrected = get_corrections(user_text, style, language)
            st.session_state["corrected_text"] = corrected

# Output Section
if st.session_state["corrected_text"]:
    st.subheader(labels["corrected_output"])
    
    # Differentiator Panel
    st.markdown(highlight_changes(user_text, st.session_state["corrected_text"]), unsafe_allow_html=True)

    # Corrected Text
    st.text_area(labels["corrected_text"], value=st.session_state["corrected_text"], height=200)

    # Copy Button
    if st.button(labels["copy_text"]):
        pyperclip.copy(st.session_state["corrected_text"])
        st.success("Copied to clipboard!!!")
