import streamlit as st
import pandas as pd
import os
from fuzzywuzzy import fuzz, process
import speech_recognition as sr

# Page configuration
st.set_page_config(
    page_title="Tshangla-English Translator",
    layout="wide"
)

# Load the data
@st.cache_data
def load_data():
    try:
        # Try with openpyxl engine
        try:
            data = pd.read_excel("tshangla_english.xlsx", engine="openpyxl")
            return data
        except:
            # If openpyxl fails, try with xlrd engine
            try:
                data = pd.read_excel("tshangla_english.xlsx", engine="xlrd")
                return data
            except:
                # If Excel reading fails, try CSV
                data = pd.read_csv("tshangla_english.csv")
                return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to find the best matching phrase
def find_match(input_text, source_column, df):
    matches = process.extract(input_text, df[source_column], limit=3, scorer=fuzz.token_sort_ratio)
    return matches

# Function to check if audio file exists (with better error handling)
def get_audio_file_path(language, id_num):
    # Try different potential file paths
    potential_paths = [
        f"{language}_Audio/Audio {id_num}.mp3",  # Original format
        f"{language}_Audio/Audio {id_num}",      # Without extension
        f"{language}_Audio/{id_num}.mp3",        # Just number with extension
        f"{language}_Audio/Audio{id_num}.mp3",   # No space
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # If no matching file found, find audio files that might match
    try:
        audio_folder = f"{language}_Audio"
        files = os.listdir(audio_folder)
        # Try to find files that might match our ID
        matching_files = [f for f in files if f.startswith(f"Audio {id_num}") or 
                         f.startswith(f"Audio{id_num}") or 
                         f == f"{id_num}.mp3"]
        
        if matching_files:
            return os.path.join(audio_folder, matching_files[0])
    except:
        pass
    
    return None

# Set up custom CSS
st.markdown( """
<style>
    .main-header {
        font-size: 2.5rem;
        text-align: center;
        background-color: #3b5998;
        color: white;
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 2rem;
    }
    .language-container {
        background-color: #f0f2f5;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .language-header {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .audio-warning {
        color: #856404;
        background-color: #fff3cd;
        border-radius: 5px;
        padding: 0.5rem;
    }
    .result-container {
        margin-top: 2rem;
    }
</style> """
, unsafe_allow_html=True)

# Main app
st.markdown('<div class="main-header">Bidirectional Tshangla-English Translator</div>', unsafe_allow_html=True)

# Load data first
df = load_data()
if df is None:
    st.stop()

# Initialize session state for history
if 'history' not in st.session_state:
    st.session_state.history = []

# Initialize session state for language selection
if 'lang_is_tshangla' not in st.session_state:
    st.session_state.lang_is_tshangla = True
    
# Add a "Clear All" button to reset session state
if st.sidebar.button("Clear History"):
    st.session_state.history = []
    st.rerun()  # FIXED: Changed from st.experimental_rerun()

# Language selection with swap button
col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    # Use the session state to determine which radio button is selected
    if st.session_state.lang_is_tshangla:
        source_lang = st.radio("Source language:", ["Tshangla", "English"], index=0, horizontal=True)
    else:
        source_lang = st.radio("Source language:", ["Tshangla", "English"], index=1, horizontal=True)
with col2:
    st.write("##")
    if st.button("⇄ Swap"):
        # Toggle the language selection in session state
        st.session_state.lang_is_tshangla = not st.session_state.lang_is_tshangla
        st.rerun()  # FIXED: Changed from st.experimental_rerun()
with col3:
    target_lang = "English" if st.session_state.lang_is_tshangla else "Tshangla"
    st.write(f"Target language: **{target_lang}**")

# Initialize user input in session state if not exists
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

# Input method tabs
tab1, tab2 = st.tabs(["Text Input", "Voice Input"])

translate_button = False

with tab1:
    user_input = st.text_input(f"Enter {source_lang} text:", value=st.session_state.user_input)
    st.session_state.user_input = user_input
    
    col1, col2 = st.columns([1, 5])
    with col1:
        translate_button = st.button("Translate")
    with col2:
        if st.button("Clear Input"):
            st.session_state.user_input = ""
            st.rerun()  # FIXED: Changed from st.experimental_rerun()

with tab2:
    st.write("Click the button and speak:")
    if st.button("Start Recording"):
        with st.spinner("Listening..."):
            try:
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    st.write("Listening...")
                    r.adjust_for_ambient_noise(source)
                    audio = r.listen(source, timeout=5)
                    try:
                        user_input = r.recognize_google(audio)
                        st.session_state.voice_input = user_input
                        st.session_state.user_input = user_input
                        st.success(f"Recognized: {user_input}")
                        translate_button = True
                    except sr.UnknownValueError:
                        st.error("Could not understand audio")
                    except sr.RequestError:
                        st.error("Could not request results from speech recognition service")
            except Exception as e:
                st.error(f"Error with microphone: {e}")

# Translation logic
if 'voice_input' in st.session_state and tab2:
    user_input = st.session_state.voice_input
    translate_button = True

if st.session_state.user_input and translate_button:
    source_col = source_lang
    matches = find_match(st.session_state.user_input, source_col, df)
    
    if matches and matches[0][1] > 60:  # 60% similarity threshold
        best_match = matches[0][0]
        match_row = df[df[source_col] == best_match].iloc[0]
        match_id = match_row['ID']
        translation = match_row[target_lang]
        
        # Display translation results
        st.markdown('<div class="result-container">', unsafe_allow_html=True)
        st.success(f"Match found ({matches[0][1]}% similarity)")
        
        result_col1, result_col2 = st.columns(2)
        with result_col1:
            st.markdown(f'<div class="language-container"><div class="language-header">{source_lang}</div>', unsafe_allow_html=True)
            st.write(best_match)
            
            # Better audio file handling
            source_audio = get_audio_file_path(source_lang, match_id)
            if source_audio:
                st.audio(source_audio)
            else:
                st.markdown(f'<div class="audio-warning">Audio not available for this phrase</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
                
        with result_col2:
            st.markdown(f'<div class="language-container"><div class="language-header">{target_lang}</div>', unsafe_allow_html=True)
            st.write(translation)
            
            # Better audio file handling
            target_audio = get_audio_file_path(target_lang, match_id)
            if target_audio:
                st.audio(target_audio)
            else:
                st.markdown(f'<div class="audio-warning">Audio not available for this phrase</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
                
        # Save to history
        st.session_state.history.append({
            "source_language": source_lang,
            "source_text": best_match,
            "target_language": target_lang,
            "target_text": translation,
            "match_id": match_id
        })
        
        # Alternative matches
        with st.expander("See alternative matches"):
            for match in matches[1:]:
                match_text = match[0]
                match_row = df[df[source_col] == match_text].iloc[0]
                st.write(f"- **{match_text}** → **{match_row[target_lang]}** ({match[1]}% similarity)")
    else:
        st.error("No matching translation found. Try rephrasing your input.")

# Translation history
if st.session_state.history:
    with st.expander("Translation History"):
        for i, item in enumerate(reversed(st.session_state.history)):
            st.write(f"**{i+1}. {item['source_language']}:** {item['source_text']}")
            st.write(f"**{item['target_language']}:** {item['target_text']}")
            col1, col2 = st.columns(2)
            with col1:
                source_audio = get_audio_file_path(item['source_language'], item['match_id'])
                if source_audio:
                    st.audio(source_audio)
            with col2:
                target_audio = get_audio_file_path(item['target_language'], item['match_id'])
                if target_audio:
                    st.audio(target_audio)
            st.write("---")

# Sidebar with examples and app info
with st.sidebar:
    st.header("Sample Phrases")
    if df is not None:
        sample_count = min(5, len(df))
        samples = df.sample(sample_count)
        for _, row in samples.iterrows():
            st.write(f"**Tshangla:** {row['Tshangla']}")
            st.write(f"**English:** {row['English']}")
            st.write("---")
    
    st.header("About")
    st.write("This is a bidirectional translation app for Tshangla and English languages.")
    st.write("It uses a table-based approach with fuzzy matching to find the best translation.")
    st.write("Total entries: ", len(df) if df is not None else "Unknown")