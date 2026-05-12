import os
import re
import base64
import tempfile
import streamlit as st
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="전국노래자랑",
    page_icon="🎤",
    layout="centered"
)

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "entered" not in st.session_state:
    st.session_state.entered = False
if "show_award" not in st.session_state:
    st.session_state.show_award = False
if "award_score" not in st.session_state:
    st.session_state.award_score = 0
if "award_text" not in st.session_state:
    st.session_state.award_text = ""
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None


# 배경음악 재생
def play_bgm(loop=False):
    bgm_path = Path(__file__).parent / "전국노래자랑(오프닝).mp3"
    try:
        bgm_b64 = base64.b64encode(bgm_path.read_bytes()).decode()
        loop_attr = "loop" if loop else ""
        audio_html = f"""
        <audio autoplay {loop_attr} style="display:none">
            <source src="data:audio/mp3;base64,{bgm_b64}" type="audio/mp3">
        </audio>
        """
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.warning(f"⚠️ 배경음악 로드 실패: {e}")


# 입장 화면
if not st.session_state.entered:
    logo_path = Path(__file__).parent / "전국노래자랑.svg"
    st.image(str(logo_path), width="stretch")
    st.caption("ⓒ KBS 전국노래자랑")

    st.write("")
    st.write("")
    st.write("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🎤 지원하겠습니까? 🎼", use_container_width=True):
            st.session_state.entered = True
            st.rerun()
    st.stop()


# 본 화면 진입 시 음악 재생
play_bgm(loop=False)


# 헤더
logo_path = Path(__file__).parent / "전국노래자랑.svg"
st.image(str(logo_path), width="stretch")
st.caption("ⓒ KBS 전국노래자랑")


st.components.v1.html("""
    <style>
        @keyframes float {
            0%   { transform: translateY(0px) rotate(0deg); opacity: 0.8; }
            50%  { transform: translateY(-30px) rotate(15deg); opacity: 1; }
            100% { transform: translateY(0px) rotate(0deg); opacity: 0.8; }
        }
        .icon {
            position: absolute;
            font-size: 2rem;
            animation: float linear infinite;
            user-select: none;
            pointer-events: none;
        }
        #stage {
            position: relative;
            width: 100%;
            height: 180px;
            overflow: hidden;
        }
    </style>
    <div id="stage"></div>
    <script>
        const icons = ["🎤","🎵","🎶","🎼","🎤","🎵","🎶","🎤","🎵","🎶"];
        const stage = document.getElementById("stage");
        icons.forEach((ic, i) => {
            const el = document.createElement("div");
            el.className = "icon";
            el.innerText = ic;
            el.style.left = (8 + i * 9) + "%";
            el.style.top = (20 + Math.random() * 50) + "%";
            el.style.animationDuration = (2.5 + Math.random() * 2) + "s";
            el.style.animationDelay = (Math.random() * 2) + "s";
            stage.appendChild(el);
        });
    </script>
    """, height=190)

# 테마곡 토글 버튼
bgm_path = Path(__file__).parent / "전국노래자랑(오프닝).mp3"
try:
    bgm_b64 = base64.b64encode(bgm_path.read_bytes()).decode()
    toggle_html = f"""
    <audio id="theme-audio" src="data:audio/mp3;base64,{bgm_b64}" preload="auto"></audio>
    <button id="theme-btn" onclick="toggleBGM()" style="
        background-color: rgb(255,255,255);
        color: rgb(49,51,63);
        border: 1px solid rgba(49,51,63,0.2);
        border-radius: 0.5rem;
        padding: 0.375rem 0.75rem;
        font-size: 1rem;
        font-weight: 400;
        font-family: 'Source Sans Pro', sans-serif;
        cursor: pointer;
        width: auto;
        line-height: 1.6;
        transition: background-color 0.15s, border-color 0.15s;
    " onmouseover="this.style.backgroundColor='rgb(240,242,246)'; this.style.borderColor='rgba(49,51,63,0.4)'"
       onmouseout="this.style.backgroundColor='rgb(255,255,255)'; this.style.borderColor='rgba(49,51,63,0.2)'"
    >🎺 테마곡 재생</button>
    <script>
    const audio = document.getElementById('theme-audio');
    const btn   = document.getElementById('theme-btn');
    let playing = false;

    function toggleBGM() {{
        if (playing) {{
            audio.pause();
            audio.currentTime = 0;
            btn.innerText = '🎺 테마곡 재생';
            playing = false;
        }} else {{
            audio.play();
            btn.innerText = '⏹ 정지';
            playing = true;
        }}
        audio.onended = function() {{
            btn.innerText = '🎺 테마곡 재생';
            playing = false;
        }};
    }}
    </script>
    """
    st.components.v1.html(toggle_html, height=50)
except Exception as e:
    st.warning(f"⚠️ 테마곡 로드 실패: {e}")


st.divider()

st.info("🎭 무대에 오르셨습니다! \n\n👀딩동댕 / 땡으로 심사해드립니다~")

audio_file = st.audio_input("🎙️ 마이크 버튼을 눌러 노래를 시작하세요~ 다시 누르면 심사 시작!")
audio_bytes = audio_file.read() if audio_file else None


# 오디오 처리 파이프라인
audio_id = hash(audio_bytes) if audio_bytes else None
 
if audio_bytes and audio_id != st.session_state.last_audio_id:
    st.session_state.last_audio_id = audio_id
    client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))
 
    # STT
    with st.spinner("👂 감상 중..."):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcript_result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                prompt="이것은 노래 가사입니다. This is song lyrics. これは歌の歌詞です。흥얼거림과 멜로디가 포함될 수 있습니다. 가사를 최대한 정확히 받아 적으세요."
            )
        os.unlink(tmp_path)
        transcript = transcript_result.text.strip()

 
    if transcript:
        st.session_state.chat_history.append({"role": "user", "text": transcript})
 
        # GPT-4o audio 심사
        with st.spinner("🎩 심사 중..."):
            system_prompt = """
            당신은 KBS 전국노래자랑의 사회자 故 송해 선생님입니다.
            참가자의 노래를 직접 듣고, 음정/박자/전달력을 종합해 심사합니다.

            점수 기준:
            - 음정/박자 완벽, 감정 전달까지 → 90~100점
            - 음정 맞고 박자도 괜찮음 → 70~89점
            - 흥얼거리거나 가사가 불분명 → 40~69점
            - 음정/박자 많이 틀림 → 10~39점
            - 노래가 아닌 소음/침묵 → 0점

            심사 규칙:
            - 잘 부른 경우 → 반드시 "딩동댕~!" 으로 시작
            - 틀리거나 아쉬운 경우 → 반드시 "땡~!" 으로 시작
            - 항상 100점 만점 기준 점수를 포함할 것 (예: 85점, 92점)
            - 음정, 박자, 감정 전달력을 고려해서 점수를 매길 것
            - 송해 선생님 말투 사용: "허허~", "자자~", "어이쿠!", "아이고~"
            - 반드시 "다음 참가자~! 👏" 로 마무리
            - 2~4문장 이내로 간결하게

            예시 (잘한 경우):
            "딩동댕~! 🔔 허허~ 음정도 척척, 박자도 딱딱~ 95점 드립니다! 다음 참가자~! 👏"

            예시 (아쉬운 경우):
            "땡~! 🔕 아이고~ 음정이 살짝 흔들렸지만 열정은 백점이에요! 65점 드립니다! 다음 참가자~! 👏"
            """
            audio_b64 = base64.b64encode(audio_bytes).decode()
            response = client.chat.completions.create(
                model="gpt-4o-audio-preview",
                modalities=["text"],
                messages=[
                    {"role": "system", 
                        "content": system_prompt},
                    {"role": "user", 
                        "content": [
                        {"type": "text", 
                            "text": "이 참가자의 노래를 직접 듣고 심사해주세요."},
                        {"type": "input_audio", 
                            "input_audio": {
                            "data": audio_b64,
                            "format": "wav"
                        }}
                    ]}
                ],
                max_tokens=200,
            )
            ai_text = response.choices[0].message.content.strip()
 
        if ai_text:
            st.session_state.chat_history.append({"role": "ai", "text": ai_text})
 
            # TTS
            with st.spinner("🔊 두근두근 과연 점수는...?"):
                try:
                    tts_tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    tts_path = tts_tmp.name
                    tts_tmp.close()
 
                    with client.audio.speech.with_streaming_response.create(
                        model="gpt-4o-mini-tts",
                        voice="onyx",
                        input=ai_text,
                    ) as tts_response:
                        tts_response.stream_to_file(tts_path)
 
                    with open(tts_path, "rb") as f:
                        audio_data = f.read()
                    os.unlink(tts_path)
 
                    audio_b64 = base64.b64encode(audio_data).decode()
                    autoplay_html = f"""
                    <audio autoplay style="display:none">
                        <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                    </audio>
                    """
                    st.components.v1.html(autoplay_html, height=0)
 
                except Exception as e:
                    st.warning(f"⚠️ TTS 재생 실패: {e}")


# 채팅(노래 - 심사) 내역 출력
if st.session_state.chat_history:
    st.divider()
 
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["text"])
        else:
            with st.chat_message("assistant", avatar="🎩"):
                text = msg["text"]
                if text.startswith("딩동댕~!"):
                    st.success(text)
                elif text.startswith("땡~!"):
                    st.error(text)
                else:
                    st.write(text)
 
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🥳 인기상은 누구일까? 🧑‍🎤"):
            best_score = 0
            best_text  = ""
            best_lyrics = ""
            msgs = st.session_state.chat_history
            for i, msg in enumerate(msgs):
                if msg["role"] == "ai":
                    match = re.search(r"(\d+)점", msg["text"])
                    if match:
                        score = int(match.group(1))
                        if score > best_score:
                            best_score = score
                            best_text  = msg["text"]
                            if i > 0 and msgs[i-1]["role"] == "user":
                                best_lyrics = msgs[i-1]["text"]
 
            if best_score > 0:
                st.session_state.show_award  = True
                st.session_state.award_score = best_score
                st.session_state.award_text  = best_text
                st.session_state.award_lyrics = best_lyrics
 
            st.session_state.chat_history = []
            st.rerun()

# 인기상 시상식
if st.session_state.show_award:
    st.balloons()
    st.success(f"🏆 오늘의 인기상! 최고 점수: {st.session_state.award_score}점")
    st.info(f"🎵 가사: {st.session_state.award_lyrics}") 
 
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🎊 확인", use_container_width=True):
            st.session_state.show_award = False
            st.rerun()