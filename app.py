import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import io
import xml.etree.ElementTree as ET
import urllib3
import urllib.parse
import os
import altair as alt
import streamlit.components.v1 as components  # 🛑 번역 팝업 차단용 특수 부품 추가

# 💡 회사 PC SSL 인증서 차단 경고음 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🎨 웹앱 기본 설정 (크롬 감시망을 피하기 위해 탭 제목을 완전한 한국어로 변경)
st.set_page_config(page_title="부동산 실거래가 정밀 분석기", layout="wide", page_icon="🏢")

# 🛑 [핵심 패치] 번역 팝업 강제 차단 (자바스크립트 DOM 직접 타격)
components.html(
    """
    <script>
    // 현재 창부터 부모 창(Streamlit 메인 앱)까지 거슬러 올라가며 번역 강제 차단 (CORS 에러 무시)
    let currentWindow = window;
    while (true) {
        try {
            currentWindow.document.documentElement.lang = 'ko';
            currentWindow.document.documentElement.setAttribute('translate', 'no');
            if (!currentWindow.document.querySelector('meta[name="google"]')) {
                let meta = currentWindow.document.createElement('meta');
                meta.name = 'google';
                meta.content = 'notranslate';
                currentWindow.document.head.appendChild(meta);
            }
            if (currentWindow === window.top) break;
            currentWindow = currentWindow.parent;
        } catch (e) {
            break; // 크로스 도메인 보안에 막히면 조용히 중단
        }
    }
    </script>
    """,
    height=0, width=0
)

# ==========================================
# 🔑 [보안 핵심] 하이브리드 스텔스 API 키 엔진
# ==========================================
KEY_FILE = "api_key.txt"

def get_api_key():
    try:
        if "KOREA_API_KEY" in st.secrets:
            return st.secrets["KOREA_API_KEY"], True 
    except:
        pass
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip(), False
    return "", False

def save_key_local(key):
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key.strip())

# 🚨 스마트 만료 알림 시스템
expiry_date = datetime(2028, 3, 1)
today = datetime.now()
days_left = (expiry_date - today).days

if days_left <= 30:
    st.error(f"🚨 [경고] 국토교통부 API 자료 열람기간 만료가 다가오고 있습니다! (D-{days_left}일)")
elif days_left <= 100:
    st.warning(f"💡 [안내] 국토교통부 API 인증키 만료까지 {days_left}일 남았습니다.")

# 💅 CSS 커스텀 인젝션
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #00C781; color: white; border: none; border-radius: 8px; font-weight: bold; height: 50px; }
    div.stButton > button:first-child:hover { background-color: #00A66A; color: white; }
    .header-box { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2C3E50;}
    .header-box h2 { margin: 0 0 5px 0; color: #222; font-size: 26px; font-weight: 800; }
    .header-box p { margin: 0; color: #666; font-size: 15px; }
    .category-title { font-size: 16px; font-weight: bold; color: #333; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #00C781; padding-bottom: 5px; display: inline-block; }
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #00C781 !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# 🧠 데이터베이스
SEOUL_GU_CD = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200", "광진구": "11215",
    "동대문구": "11230", "중랑구": "11260", "성북구": "11290", "강북구": "11305", "도봉구": "11320",
    "노원구": "11350", "은평구": "11380", "서대문구": "11410", "마포구": "11440", "양천구": "11470",
    "강서구": "11500", "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740"
}

SEOUL_DONG_DB = {
    "종로구": ["청운동", "신교동", "궁정동", "효자동", "누하동", "누상동", "옥인동", "삼청동", "안국동", "소격동", "화동", "사간동", "송현동", "가회동", "재동", "계동", "원서동", "훈정동", "묘동", "봉익동", "돈의동", "장사동", "관수동", "인사동", "낙원동", "종로1가", "종로2가", "종로3가", "종로4가", "종로5가", "종로6가", "이화동", "연건동", "충신동", "동숭동", "혜화동", "명륜1가", "명륜2가", "명륜3가", "명륜4가", "창신동", "숭인동", "교남동", "평동", "송월동", "홍파동", "교북동", "행촌동", "구기동", "평창동", "부암동", "홍지동", "신영동", "무악동"],
    "강남구": ["역삼동", "개포동", "청담동", "삼성동", "대치동", "신사동", "논현동", "압구정동", "세곡동", "자곡동", "율현동", "일원동", "수서동", "도곡동"],
    "서초구": ["방배동", "양재동", "우면동", "원지동", "잠원동", "반포동", "서초동", "내곡동", "염곡동", "신원동"],
    "영등포구": ["영등포동", "여의도동", "당산동1가", "당산동", "도림동", "문래동1가", "문래동", "양평동1가", "양평동", "양화동", "신길동", "대림동"],
    "송파구": ["잠실동", "신천동", "풍납동", "송파동", "석촌동", "삼전동", "가락동", "문정동", "장지동", "방이동", "오금동", "거여동", "마천동"],
    "강동구": ["명일동", "고덕동", "상일동", "길동", "둔촌동", "암사동", "성내동", "천호동", "강일동"],
    "서대문구": ["충정로2가", "합동", "미근동", "냉천동", "천연동", "옥천동", "영천동", "현저동", "북아현동", "홍제동", "대현동", "대신동", "신촌동", "봉원동", "창천동", "연희동", "홍은동", "북가좌동", "남가좌동"]
}

def get_recent_months(n=6):
    months = []
    y, m = datetime.now().year, datetime.now().month
    for _ in range(n):
        m -= 1
        if m == 0: m = 12; y -= 1
        months.append((f"{y}년 {m:02d}월", f"{y}{m:02d}"))
    return months

recent_month_data = get_recent_months(6)
month_labels = [m[0] for m in recent_month_data]
month_values = {m[0]: m[1] for m in recent_month_data}

def format_currency(amount):
    try:
        amount = int(amount)
        if amount == 0: return "0원"
        uk = amount // 100000000
        man = (amount % 100000000) // 10000
        if uk > 0 and man > 0: return f"{uk}억 {man:,}만 원"
        elif uk > 0: return f"{uk}억 원"
        else: return f"{man:,}만 원"
    except: return "계산 오류"

def get_multi_xml_text(node, tags, default=""):
    for tag in tags:
        elem = node.find(tag)
        if elem is not None and elem.text and elem.text.strip():
            return elem.text.strip()
    return default

# 🌟 메인 화면 대시보드 (영어 텍스트에 번역 금지 망토 적용)
st.markdown("""
<div class="header-box">
    <h2>🏢 <span class="notranslate" translate="no">Pro Estate Analytics</span> <span class="notranslate" translate="no" style="font-size:14px; background:#111111; color:white; padding:4px 10px; border-radius:20px; vertical-align: middle; margin-left:10px;">v6.3 Zero-Exposure Security</span></h2>
    <p>상실의시대 대표님 전용 | 엿보기(<span class="notranslate" translate="no">Shoulder Surfing</span>) 원천 차단 및 시각 보안 최적화 에디션</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2633/2633320.png", width=60)
    saved_key, is_from_cloud = get_api_key()
    
    if is_from_cloud:
        st.title("🟢 시스템 상태")
        st.success("**서버 온라인**\n\n부동산 빅데이터 관제 시스템이 정상 가동 중입니다.")
        final_api_key = saved_key
    else:
        st.title("⚙️ 관리자 설정")
        if saved_key:
            st.success("🔒 **로컬 보안 모드 작동 중**")
            api_key_input = st.text_input("마스터 API 키 변경 (선택)", value="", type="password", key="api_change_sidebar")
        else:
            st.warning("⚠️ 인증키가 없습니다.")
            api_key_input = st.text_input("국토교통부 마스터 API 키 입력", value="", type="password", key="api_first_sidebar")
            
        if api_key_input:
            save_key_local(api_key_input)
            st.success("✅ 인증키가 저장되었습니다!")
            saved_key = api_key_input
        final_api_key = saved_key
        if final_api_key: st.info("💡 로컬 오프라인 모드로 통신 중입니다.")
            
    st.divider()
    # 사이드바 하단 영어 문구에도 번역 금지 망토 적용
    st.markdown("<p class='notranslate' translate='no' style='font-size: 13px; color: #888888;'>ⓒ 2026 Developed by Mina</p>", unsafe_allow_html=True)

# 🎯 1. 검색 조건 설정
st.markdown("<div class='category-title'>🔍 1. 검색 조건 설정 (원클릭)</div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])

with col1: selected_gu = st.selectbox("📍 자치구 선택", list(SEOUL_GU_CD.keys()), key="gu_main")
with col2:
    base_dongs = SEOUL_DONG_DB.get(selected_gu, [])
    available_dongs = ["전체 (해당 구 모든 동)"] + base_dongs
    selected_dongs = st.multiselect("🏘️ 법정동 다중 선택", available_dongs, default=["전체 (해당 구 모든 동)"], key="dong_main")
with col3:
    selected_month_label = st.selectbox("📅 조회 연월 (최신순)", month_labels, key="month_main")
    target_month = month_values[selected_month_label]

# 🗂️ 2. 수집할 데이터 선택
st.markdown("<div class='category-title'>🗂️ 2. 수집할 데이터 선택</div>", unsafe_allow_html=True)
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**[주거용 매매]**")
    opt_apt_trade = st.checkbox("🏢 아파트 매매 실거래가", value=True, key="opt1")
    opt_off_trade = st.checkbox("🏢 오피스텔 매매 실거래가", key="opt2")
    opt_vil_trade = st.checkbox("🏠 연립/다세대 매매 실거래가", key="opt3")
    opt_house_trade = st.checkbox("🏡 단독/다가구 매매 실거래가", key="opt4")
with col_b:
    st.markdown("**[주거용 전월세]**")
    opt_apt_rent = st.checkbox("🏢 아파트 전월세 실거래가", key="opt5")
    opt_off_rent = st.checkbox("🏢 오피스텔 전월세 실거래가", key="opt6")
    opt_vil_rent = st.checkbox("🏠 연립/다세대 전월세 실거래가", key="opt7")
    opt_house_rent = st.checkbox("🏡 단독/다가구 전월세 실거래가", key="opt8")
with col_c:
    st.markdown("**[투자/상업/기타]**")
    opt_apt_bun = st.checkbox("🏗️ 아파트 분양권/전매", key="opt9")
    opt_biz_trade = st.checkbox("🏪 상업/업무용 부동산 매매", key="opt10")
    opt_land_trade = st.checkbox("🌍 토지 매매 실거래가", key="opt11")

st.divider()
execute_btn = st.button("🚀 위 조건으로 빅데이터 병렬 추출 및 시각화 대시보드 생성", use_container_width=True)

if execute_btn:
    if not final_api_key: st.error("🚨 마스터 키가 연결되지 않았습니다.")
    elif not selected_dongs: st.warning("⚠️ 분석할 동을 선택해주세요!")
    else:
        api_targets = []
        if opt_apt_trade: api_targets.append(("아파트 매매", "
