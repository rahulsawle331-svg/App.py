import streamlit as st
import asyncio
import edge_tts
import pytesseract
from pdf2image import convert_from_bytes
from pypdf import PdfReader
from deep_translator import GoogleTranslator
from pydub import AudioSegment
import io

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
st.caption("Koi bhi language → Translate → Voice + Music + AI Assistant")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.header("⚙️ Settings")

    lang_options = {
        "Hindi": "hi",
        "English": "en",
        "Japanese": "ja",
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Korean": "ko",
        "Chinese (Simplified)": "zh-CN",
        "Arabic": "ar",
        "Portuguese": "pt",
        "Russian": "ru",
        "Italian": "it",
        "Turkish": "tr",
        "Indonesian": "id",
        "Thai": "th"
    }
    target_lang_name = st.selectbox("Translate to Language", list(lang_options.keys()), index=0)
    target_lang = lang_options[target_lang_name]

    voice_options = {
        "Hindi Female": "hi-IN-SwaraNeural",
        "Hindi Male": "hi-IN-MadhurNeural",
        "English Female": "en-US-JennyNeural",
        "English Male": "en-US-GuyNeural",
        "Japanese Female": "ja-JP-NanamiNeural",
        "Korean Female": "ko-KR-SunHiNeural",
    }
    selected_voice = st.selectbox("Voice", list(voice_options.keys()))
    voice_id = voice_options[selected_voice]

    rate = st.slider("Speed", -40, 40, 0, 5)
    pitch = st.slider("Pitch", -50, 50, 0, 5)

    st.markdown("---")
    st.subheader("🎵 Background Music")
    add_music = st.checkbox("Background Music Add Karo")
    music_file = None
    music_volume = -15
    if add_music:
        music_file = st.file_uploader("Music file upload karo (MP3)", type=["mp3", "wav"])
        music_volume = st.slider("Music Volume", -30, 0, -15)

# ---------- INPUT ----------
input_mode = st.radio("Input Type:", ["📄 PDF Upload", "✍️ Direct Text Paste"], horizontal=True)

full_text = ""
uploaded_file = None

if input_mode == "📄 PDF Upload":
    uploaded_file = st.file_uploader("PDF Upload Karo", type=["pdf"])
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name}")
        try:
            pdf_bytes = uploaded_file.read()
            uploaded_file.seek(0)
            reader = PdfReader(uploaded_file)
            normal_text = ""
            for i, page in enumerate(reader.pages):
                t = page.extract_text()
                if t:
                    normal_text += f"\n--- Page {i+1} ---\n{t}\n"
            
            if normal_text.strip():
                full_text = normal_text
            else:
                with st.spinner("OCR chal raha hai..."):
                    images = convert_from_bytes(pdf_bytes)
                    ocr_text = ""
                    for i, image in enumerate(images):
                        t = pytesseract.image_to_string(image)
                        if t.strip():
                            ocr_text += f"\n--- Page {i+1} ---\n{t}\n"
                    full_text = ocr_text
            if not full_text.strip():
                st.error("Text nahi mila.")
        except Exception as e:
            st.error(f"PDF Error: {e}")
else:
    pasted_text = st.text_area("Text yahan paste karo:", height=200)
    if pasted_text.strip():
        full_text = pasted_text

# ---------- TRANSLATION + VOICE ----------
if full_text.strip():
    st.write(f"📊 Original Characters: **{len(full_text)}**")

    with st.expander("📝 Original Text", expanded=False):
        st.text_area("Original", full_text, height=150, disabled=True)

    with st.spinner(f"{target_lang_name} me translate ho raha hai..."):
        try:
            chunk_size = 4500
            chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
            translated_chunks = []
            for chunk in chunks:
                translated = GoogleTranslator(source='auto', target=target_lang).translate(chunk)
                translated_chunks.append(translated)
            translated_text = "\n".join(translated_chunks)
        except Exception as e:
            st.error(f"Translation Error: {e}")
            translated_text = full_text

    st.success(f"✅ {target_lang_name} me translate ho gaya!")
    
    with st.expander("📝 Translated Text (Edit kar sakte ho)", expanded=True):
        translated_text = st.text_area("Translated Text", translated_text, height=250)

    text_to_speak = translated_text[:5000] if len(translated_text) > 5000 else translated_text

    if st.button("🔊 Voice Generate Karo"):
        with st.spinner("Voice ban raha hai..."):
            try:
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

                if add_music and music_file:
                    voice_audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                    bg_music = AudioSegment.from_file(music_file)
                    bg_music = bg_music + music_volume
                    
                    if len(bg_music) < len(voice_audio):
                        times = (len(voice_audio) // len(bg_music)) + 1
                        bg_music = bg_music * times
                    bg_music = bg_music[:len(voice_audio)]
                    
                    final_audio = voice_audio.overlay(bg_music)
                    buffer = io.BytesIO()
                    final_audio.export(buffer, format="mp3")
                    audio_bytes = buffer.getvalue()

                st.audio(audio_bytes, format="audio/mp3")

                filename = "voice_output.mp3"
                if uploaded_file:
                    filename = uploaded_file.name.replace(".pdf", f"_{target_lang_name}_voice.mp3")

                st.download_button("⬇️ MP3 Download", data=audio_bytes, file_name=filename, mime="audio/mp3")
                st.success("Voice Tayar Hai!")
            except Exception as e:
                st.error(f"Error: {e}")

# ---------- CHHOTA AI ASSISTANT ----------
st.markdown("---")
st.subheader("🤖 Chhota AI Assistant")

st.info("Yeh chhota AI aapko naye options aur ideas de sakta hai.")

ai_question = st.text_input("AI se kuch poocho (jaise: nayi language add karo, nayi voice chahiye, feature suggest karo)")

if st.button("AI se Jawab Lo"):
    question = ai_question.lower().strip()
    
    if any(word in question for word in ["language", "bhasha", "lang"]):
        st.success("""
**AI Suggestion - Nayi Languages:**
- Bengali (bn)
- Tamil (ta)
- Telugu (te)
- Marathi (mr)
- Gujarati (gu)
- Malayalam (ml)
- Kannada (kn)
- Punjabi (pa)

Aap chaho to main inhe code me add kar sakta hoon.
        """)
    
    elif any(word in question for word in ["voice", "awaz", "voice"]):
        st.success("""
**AI Suggestion - Nayi Voices:**
- Hindi Female (Ananya)
- English UK Female
- Spanish Female
- French Female
- Japanese Male
- Chinese Female

Bolo kaunsi voice add karni hai?
        """)
    
    elif any(word in question for word in ["feature", "option", "add", "naya"]):
        st.success("""
**AI Suggestion - Naye Features jo add ho sakte hain:**
1. Multiple characters ke liye alag-alag voice
2. Emotional voice (khush, gussa, udaas)
3. Auto chapter split
4. Voice + Subtitle download
5. Text-to-Image (character ka photo)
6. Slow mode for learning

Kaunsa feature add karna hai batao!
        """)
    
    elif question:
        st.success("""
**AI Reply:**
Samajh gaya! Aap mujhe clearly batao:
- Nayi language chahiye?
- Nayi voice chahiye?
- Naya feature chahiye?

Main uske hisaab se help karunga.
        """)
    else:
        st.warning("Pehle kuch likho phir button dabao.")

# ---------- EDITING TOOLS ----------
st.markdown("---")
st.subheader("🛠️ Manga / Comic Editing Tools")

st.markdown("""
Agar Manga/Comic edit karni ho to yeh free tools use karo:

| Tool | Best For | Link |
|------|----------|------|
| **Photopea** | Online Photoshop | [photopea.com](https://www.photopea.com) |
| **Krita** | Drawing + Comics | [krita.org](https://krita.org) |
| **MediBang Paint** | Manga making | [medibangpaint.com](https://medibangpaint.com) |
| **Ibispaint** | Mobile Editing | Play Store / App Store |
""")
