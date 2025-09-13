import streamlit as st
import difflib

# Multilingual Labels
LABELS = {
    "English": {
        "enter_text": "Enter text",
        "enter_text_placeholder": "Type or paste your text here...",
        "correct_text": "Correct Text",
        "corrected_output": "Corrected Output",
        "corrected_text": "Corrected Text",
        "copy_text": "Copy Corrected Text",
        "empty_warning": "⚠️ Please enter some text first!",
        "style": "Style",
        "style_options": ["neutral", "casual", "formal", "persuasive", "concise"],
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark"
    },
    "Hindi": {
        "enter_text": "पाठ दर्ज करें",
        "enter_text_placeholder": "यहां अपना पाठ लिखें या पेस्ट करें...",
        "correct_text": "पाठ सुधारें",
        "corrected_output": "सुधारा हुआ पाठ",
        "corrected_text": "सुधारा गया पाठ",
        "copy_text": "सुधारा हुआ पाठ कॉपी करें",
        "empty_warning": "⚠️ कृपया पहले कुछ पाठ दर्ज करें!",
        "style": "शैली",
        "style_options": ["साधारण", "अनौपचारिक", "औपचारिक", "प्रभावशाली", "संक्षिप्त"],
        "theme": "थीम",
        "light": "हल्का",
        "dark": "अंधेरा"
    },
    "Bengali": {
        "enter_text": "টেক্সট লিখুন",
        "enter_text_placeholder": "এখানে আপনার টেক্সট টাইপ বা পেস্ট করুন...",
        "correct_text": "টেক্সট সংশোধন করুন",
        "corrected_output": "সংশোধিত টেক্সট",
        "corrected_text": "সংশোধিত লেখা",
        "copy_text": "সংশোধিত লেখা কপি করুন",
        "empty_warning": "⚠️ অনুগ্রহ করে প্রথমে কিছু টেক্সট লিখুন!",
        "style": "শৈলী",
        "style_options": ["নিরপেক্ষ", "আড্ডার", "আনুষ্ঠানিক", "প্রভাবশালী", "সংক্ষিপ্ত"],
        "theme": "থিম",
        "light": "হালকা",
        "dark": "অন্ধকার"
    },
    "German": {
        "enter_text": "Text eingeben",
        "enter_text_placeholder": "Geben Sie hier Ihren Text ein...",
        "correct_text": "Text korrigieren",
        "corrected_output": "Korrigierter Text",
        "corrected_text": "Korrigierter Text",
        "copy_text": "Korrigierten Text kopieren",
        "empty_warning": "⚠️ Bitte zuerst einen Text eingeben!",
        "style": "Stil",
        "style_options": ["neutral", "locker", "formell", "überzeugend", "prägnant"],
        "theme": "Thema",
        "light": "Hell",
        "dark": "Dunkel"
    },
    "French": {
        "enter_text": "Entrez le texte",
        "enter_text_placeholder": "Tapez ou collez votre texte ici...",
        "correct_text": "Corriger le texte",
        "corrected_output": "Texte corrigé",
        "corrected_text": "Texte corrigé",
        "copy_text": "Copier le texte corrigé",
        "empty_warning": "⚠️ Veuillez d'abord entrer du texte !",
        "style": "Style",
        "style_options": ["neutre", "décontracté", "formel", "persuasif", "concis"],
        "theme": "Thème",
        "light": "Clair",
        "dark": "Sombre"
    },
    "Spanish": {
        "enter_text": "Introducir texto",
        "enter_text_placeholder": "Escriba o pegue su texto aquí...",
        "correct_text": "Corregir texto",
        "corrected_output": "Texto corregido",
        "corrected_text": "Texto corregido",
        "copy_text": "Copiar texto corregido",
        "empty_warning": "⚠️ ¡Por favor, introduzca primero algún texto!",
        "style": "Estilo",
        "style_options": ["neutral", "casual", "formal", "persuasivo", "conciso"],
        "theme": "Tema",
        "light": "Claro",
        "dark": "Oscuro"
    },
}

# Apply Theme
def apply_theme(theme="Light"):
    if theme == "Dark":
        st.markdown("""
        <style>
        body { background-color: #121212; color: #e0e0e0; }
        textarea { background-color: #1e1e1e !important; color: #ffffff !important; }
        .stButton button { background-color: #333 !important; color: #fff !important; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        body { background-color: #ffffff; color: #111; }
        textarea { background-color: #f7f7f7 !important; color: #111 !important; }
        .stButton button { background-color: #f0f0f0 !important; color: #111 !important; }
        </style>
        """, unsafe_allow_html=True)

# Highlight Changes for side-by-side differentiator (no colors)
def highlight_changes(original, corrected):
    diff_html = f"""
    <div style="display: flex; gap: 20px;">
        <div style="flex: 1;">
            <strong>Original:</strong><br>{original.replace('\n','<br>')}
        </div>
        <div style="flex: 1;">
            <strong>Corrected:</strong><br>{corrected.replace('\n','<br>')}
        </div>
    </div>
    """
    return diff_html
