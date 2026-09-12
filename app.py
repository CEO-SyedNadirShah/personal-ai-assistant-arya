# ============================================
# arya/app.py
# ARYA — Main Streamlit Chat Interface
# ============================================

import warnings
warnings.filterwarnings("ignore")

import streamlit as st
import os, tempfile

st.set_page_config(
    page_title="ARYA — Personal AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── LOAD ARYA ─────────────────────────────────
@st.cache_resource
def load_arya():
    """Initialize ARYA once and cache across reruns"""
    from main import initialize_arya
    return initialize_arya()

# ── CUSTOM CSS ────────────────────────────────
st.markdown("""
<style>
    .stApp { background: #0d0d1a; }

    .arya-header {
        background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 50%, #1a3a5c 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(102,126,234,0.3);
        text-align: center;
    }
    .arya-name {
        font-size: 3rem;
        font-weight: 900;
        background: linear-gradient(90deg, #667eea, #a78bfa, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 4px;
    }
    .arya-tagline {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 0.3rem;
    }
    .agent-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(102,126,234,0.15);
        border: 1px solid rgba(102,126,234,0.3);
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 6px;
    }
    .sidebar-section {
        background: rgba(255,255,255,0.03);
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ── INITIALIZE ────────────────────────────────
try:
    arya_graph = load_arya()
    import router
    router._arya_graph = arya_graph
    ARYA_READY = True
except Exception as e:
    ARYA_READY = False
    st.error(f"ARYA initialization failed: {e}")

from memory  import load_profile, update_profile, remember, get_memory_summary
from config  import AGENTS, ARYA_NAME, ARYA_VERSION, ARYA_DESCRIPTION
from main    import arya_multimodal


# ── SESSION STATE ─────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = "arya_streamlit"
if "upload_counter" not in st.session_state:
    st.session_state.upload_counter = 0


def _new_temp_path(filename: str) -> str:
    """Cross-platform temp path — works on Windows, Mac, Linux."""
    safe_name = filename.replace(" ", "_")
    return os.path.join(tempfile.gettempdir(), f"arya_{safe_name}")


def _reset_uploaders():
    """Force file_uploader widgets to reset by rotating their key."""
    st.session_state.upload_counter += 1


# ── SIDEBAR ───────────────────────────────────
with st.sidebar:
    profile = load_profile()

    st.markdown("""
    <div class="sidebar-section">
        <div style="color:#a78bfa;font-weight:700;font-size:0.85rem">👤 YOUR PROFILE</div>
    </div>
    """, unsafe_allow_html=True)

    user_name = st.text_input("Your name", value=profile.get("name", ""), placeholder="Enter your name...")
    if user_name and user_name != profile.get("name"):
        update_profile("name", user_name)
        remember(f"User's name is {user_name}", "fact")

    st.markdown("---")

    st.markdown("**🧠 Memory**")
    mem_summary = get_memory_summary()
    st.caption(mem_summary[:100] + "..." if len(mem_summary) > 100 else mem_summary)

    if st.button("📖 View Full Memory", use_container_width=True):
        st.switch_page("pages/2_Memory.py")

    st.markdown("---")

    st.markdown("**📎 Share with ARYA**")

    # Keys rotate after each processed upload, forcing a clean widget reset
    uploader_key_suffix = st.session_state.upload_counter

    uploaded_image = st.file_uploader(
        "Upload an image", type=["jpg", "jpeg", "png", "webp"],
        help="Share an image for ARYA to analyze",
        key=f"image_uploader_{uploader_key_suffix}"
    )
    uploaded_audio = st.file_uploader(
        "Upload audio", type=["mp3", "mp4", "wav", "m4a", "webm"],
        help="Voice note for ARYA to transcribe",
        key=f"audio_uploader_{uploader_key_suffix}"
    )

    from audio_recorder_streamlit import audio_recorder

    st.markdown("**🎙️ Record directly:**")
    recorded_audio = audio_recorder(text="", icon_size="2x")

    if recorded_audio:
        audio_path = _new_temp_path("recorded.wav")
        with open(audio_path, "wb") as f:
            f.write(recorded_audio)

    image_path = None
    audio_path = None

    if uploaded_image:
        image_path = _new_temp_path(uploaded_image.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_image.read())
        st.image(uploaded_image, caption="Image ready", use_container_width=True)

    if uploaded_audio:
        audio_path = _new_temp_path(uploaded_audio.name)
        with open(audio_path, "wb") as f:
            f.write(uploaded_audio.read())
        st.success(f"🎤 Audio ready: {uploaded_audio.name}")

    # Explicit send button for file-only submissions (no typed text)
    send_file_only = False
    if (image_path or audio_path):
        if st.button("📤 Send attachment to ARYA", use_container_width=True):
            send_file_only = True

    st.markdown("---")

    total_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("Messages this session", total_msgs)

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.markdown("**🗂️ Pages**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧠 Memory", use_container_width=True, key="nav_memory"):
            st.switch_page("pages/2_Memory.py")
    with col2:
        if st.button("⚙️ Settings", use_container_width=True, key="nav_settings"):
            st.switch_page("pages/3_Settings.py")

    st.markdown("---")
    st.caption(f"ARYA v{ARYA_VERSION} | MNE Enterprise")


# ── MAIN INTERFACE ────────────────────────────
st.markdown(f"""
<div class="arya-header">
    <div class="arya-name">◈ ARYA ◈</div>
    <div class="arya-tagline">{ARYA_DESCRIPTION}</div>
    <div style="margin-top:8px;color:#667eea;font-size:0.8rem">
        {len(AGENTS)} specialist agents · Long-term memory · Voice & Vision
    </div>
</div>
""", unsafe_allow_html=True)

if not ARYA_READY:
    st.warning("ARYA is not ready. Check your API keys and restart.")
    st.stop()

if not st.session_state.messages and not profile.get("name"):
    greeting = ("Hello! I'm ARYA, your personal AI assistant.\n\n"
                "I have six specialist agents ready to help you:\n\n"
                "🔍 **Research** · ✍️ **Write** · 📅 **Plan** · 🧮 **Analyze** · 📰 **News** · 💻 **Code**\n\n"
                "You can also share images and voice notes using the sidebar. What can I do for you today?")
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(greeting)

for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])
        if msg.get("agent"):
            agent_info = AGENTS.get(msg["agent"], {})
            st.markdown(
                f'<div class="agent-badge">{agent_info.get("emoji","🤖")} {agent_info.get("name", msg["agent"])}</div>',
                unsafe_allow_html=True
            )


# ── CHAT INPUT ────────────────────────────────
placeholder = "Ask ARYA anything..." if not (image_path or audio_path) else \
              "Add a question about the uploaded file (optional, or click Send attachment)"

from streamlit_paste_button import paste_image_button

paste_result = paste_image_button("📋 Paste image from clipboard")
if paste_result.image_data is not None:
    image_path = _new_temp_path("pasted.png")
    paste_result.image_data.save(image_path)
               
user_input = st.chat_input(placeholder)

should_process = bool(user_input) or send_file_only

if should_process:
    if not user_input and audio_path:
        display_text = "🎤 Voice message"
    elif not user_input and image_path:
        display_text = "🖼️ Image shared"
    else:
        display_text = user_input

    with st.chat_message("user", avatar="👤"):
        st.markdown(display_text)
        if image_path:
            st.image(image_path, width=200)
        if audio_path:
            st.audio(audio_path)

    st.session_state.messages.append({"role": "user", "content": display_text})

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("ARYA is thinking..."):
            result = arya_multimodal(
                text=user_input, image_path=image_path, audio_path=audio_path,
                session_id=st.session_state.session_id,
                speak=True
            )

        response   = result.get("final_response", "I couldn't process that.")
        agent_key  = result.get("agent", "")
        agent_info = AGENTS.get(agent_key, {})

        st.markdown(response)
        tts = result.get("tts")
        if tts and tts.get("success"):
            st.audio(tts["audio_bytes"], format="audio/wav", autoplay=True)
        st.markdown(
            f'<div class="agent-badge">{agent_info.get("emoji","🤖")} {agent_info.get("name","ARYA")} '
            f'· {result.get("routing_reason","")[:50]}</div>',
            unsafe_allow_html=True
        )

    st.session_state.messages.append({"role": "assistant", "content": response, "agent": agent_key})

    # Clean up temp files and reset uploaders
    for p in (image_path, audio_path):
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    _reset_uploaders()
    st.rerun()