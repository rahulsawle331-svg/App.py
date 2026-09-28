09.28 5:30 PM
import streamlit as st
import asyncio
import edge_tts
from pypdf import PdfReader

st.set_page_config(
    page_title="Chapter Voice App",
    page_icon="",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        height: 3.2em;
        font-size: 1.1rem;
        border-radius: 12px;
        font-weight: 600;
    }
    .stDownloadButton > button {
        width: 100%;
        height: 3.2em;
        border-radius: 12px;
        font-weight: 600;
    }
    h1 {
        text-align: center;
        font-size: 1.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.title(" Chapter → Voice")
st.caption("Ek chapter upload karo → Voice generate karo")

with st.sidebar:
    st.header("⚙️ Voice Settings")
    
    voice_options = {
        "Hindi Female (Natural)": "hi-IN-SwaraNeural",
        "Hindi Male (Natural)": "hi-IN-MadhurNeural",
        "Hindi Female 2": "hi-IN-AnanyaNeural",
        "English Female": "en-US-JennyNeural",
        "English Male": "en-US-GuyNeural",
    }
    
    selected_voice = st.selectbox("Voice", list(voice_options.keys()))
    voice_id = voice_options[selected_voice]
    
    rate = st.slider("Speed", -40, 40, 0, 5)
    pitch = st.slider("Pitch", -50, 50, 0, 5)

uploaded_file = st.file_uploader(
    "PDF Chapter Upload Karo",
    type=["pdf"]
)

if uploaded_file:
    st.success(f"✅ {uploaded_file.name}")
    
    try:
        reader = PdfReader(uploaded_file)
        full_text = ""
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text += f"\n--- Page {i+1} ---\n{text}\n"
        
        if not full_text.strip():
            st.error("Is PDF se text nahi mila (scanned image ho sakta hai)")
        else:
            st.write(f" Pages: **{len(reader.pages)}** | Characters: **{len(full_text)}**")
            
            with st.expander(" Text Preview", expanded=False):
                st.text_area("Extracted Text", full_text, height=250)
            
            text_to_speak = full_text[:5500] if len(full_text) > 5500 else full_text
            
            if st.button(" Voice Generate Karo"):
                with st.spinner("Voice bana raha hoon..."):
                    
                    async def generate():
                        communicate = edge_tts.Communicate(
                            text=text_to_speak,
                            voice=voice_id,
                            rate=f"{rate:+d}%",
                            pitch=f"{pitch:+d}Hz"
                        )
                        audio = b""
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                audio += chunk["data"]
                        return audio
                    
                    audio_bytes = asyncio.run(generate())
                    
                    st.audio(audio_bytes, format="audio/mp3")
                    
                    st.download_button(
                        label="⬇️ MP3 Download",
                        data=audio_bytes,
                        file_name=uploaded_file.name.replace(".pdf", "_voice.mp3"),
                        mime="audio/mp3"
                    )
                    st.success("Ho gaya!")
                    
    except Exception as e:
        st.error(f"Error: {e}")

else:
    st.info("Upar se PDF upload karo")
