import streamlit as st
import asyncio
import edge_tts
import pytesseract
from pdf2image import convert_from_bytes
from pypdf import PdfReader

st.set_page_config(
    page_title="Chapter Voice App",
    page_icon="📖",
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

st.title("📖 Chapter → Voice")
st.caption("Document upload karo ya Text paste karo → Voice generate karo")

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

# Input Mode Choose Karne Ka Option (PDF vs Text Paste)
input_mode = st.radio("Input Type Chuno:", ["📄 PDF Upload", "✍️ Direct Text Paste"], horizontal=True)

full_text = ""

if input_mode == "📄 PDF Upload":
    uploaded_file = st.file_uploader(
        "PDF Chapter Upload Karo",
        type=["pdf"]
    )

    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
        
        try:
            # Step 1: Normal Text Extract Karne Ki Koshish
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)
            
            reader = PdfReader(uploaded_file)
            normal_text = ""
            for i, page in enumerate(reader.pages):
                t = page.extract_text()
                if t:
                    normal_text += f"\n--- Page {i+1} ---\n{t}\n"
            
            # Step 2: Agar Normal Text Mil Gaya To OCR Skip Hoga
            if normal_text.strip():
                full_text = normal_text
            else:
                # Agar Normal Text Nahi Mila (Scanned PDF/Manga), To OCR Chalega
                with st.spinner("Scanned PDF detect hui hai, OCR scanning chal rahi hai..."):
                    images = convert_from_bytes(pdf_bytes)
                    ocr_text = ""
                    for i, image in enumerate(images):
                        t = pytesseract.image_to_string(image)
                        if t.strip():
                            ocr_text += f"\n--- Page {i+1} ---\n{t}\n"
                    full_text = ocr_text

            if not full_text.strip():
                st.error("Is PDF se text/OCR se kuch nahi mila.")

        except Exception as e:
            st.error(f"Error processing PDF: {e}")

else:
    # Direct Text Paste Mode
    pasted_text = st.text_area("Yahan apna Text Paste karein:", height=200, placeholder="Type or paste text here...")
    if pasted_text.strip():
        full_text = pasted_text

# Text Preview aur Voice Generation Section
if full_text.strip():
    st.write(f"📊 Total Characters: **{len(full_text)}**")
    
    with st.expander("📝 Text Preview / Edit", expanded=False):
        full_text = st.text_area("Extracted Text", full_text, height=250)
    
    text_to_speak = full_text[:5500] if len(full_text) > 5500 else full_text
    
    if st.button("🔊 Voice Generate Karo"):
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
            
            try:
                audio_bytes = asyncio.run(generate())
                
                st.audio(audio_bytes, format="audio/mp3")
                
                filename = uploaded_file.name.replace(".pdf", "_voice.mp3") if (input_mode == "📄 PDF Upload" and uploaded_file) else "pasted_text_voice.mp3"
                
                st.download_button(
                    label="⬇️ MP3 Download",
                    data=audio_bytes,
                    file_name=filename,
                    mime="audio/mp3"
                )
                st.success("Voice Tayar Hai!")
            except Exception as e:
                st.error(f"Voice generation error: {e}")
