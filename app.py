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
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="부동산 실거래 분석기", layout="wide")

try:
    final_api_key = st.secrets["KOREA_API_KEY"]
except:
    st.error("🚨 서버 비밀 금고에 API 키가 설정되지 않았습니다! 관리자에게 문의하세요.")
    st.stop()

# 🛡️ 풀스크린, 워터마크 숨기기
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden !important;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    [data-testid="stStatusWidget"] {visibility: hidden !important;}
    
    div.stButton > button:first-child { background-color: #3b4890; color: white; border: none; border-radius: 4px; font-weight: bold; height: 50px; }
    div.stButton > button:first-child:hover { background-color: #2a3042; color: white; }
    .header-box { background-color: #ffffff; padding: 25px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 6px solid #3b4890;}
    .header-box h2 { margin: 0 0 5px 0; color: #222; font-size: 26px; font-weight: 900; letter-spacing: -0.5px; }
    .header-box p { margin: 0; color: #666; font-size: 15px; font-weight: 500; }
    .category-title { font-size: 16px; font-weight: bold; color: #333; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #3b4890; padding-bottom: 5px; display: inline-block; }
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #e74c3c !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# 💡 검증 완료: 정확히 25개 자치구
SEOUL_GU_CD = {
    "강남구": "11680", "강동구": "11740", "강북구": "11305", "강서구": "11500", "관악구": "11620",
    "광진구": "11215", "구로구": "11530", "금천구": "11545", "노원구": "11350", "도봉구": "11320",
    "동대문구": "11230", "동작구": "11590", "마포구": "11440", "서대문구": "11410", "서초구": "11650",
    "성동구": "11200", "성북구": "11290", "송파구": "11710", "양천구": "11470", "영등포구": "11560",
    "용산구": "11170", "은평구": "11380", "종로구": "11110", "중구": "11140", "중랑구": "11260"
}

# 💡 검증 완료: 정확히 467개 법정동
SEOUL_DONG_DB = {
    "강남구": ["개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", "신사동", "압구정동", "역삼동", "율현동", "일원동", "자곡동", "청담동"],
    "강동구": ["강일동", "고덕동", "길동", "둔촌동", "명일동", "상일동", "성내동", "암사동", "천호동"],
    "강북구": ["미아동", "번동", "수유동", "우이동"],
    "강서구": ["가양동", "개화동", "공항동", "과해동", "내발산동", "등촌동", "마곡동", "방화동", "염창동", "오곡동", "오쇠동", "외발산동", "화곡동"],
    "관악구": ["남현동", "봉천동", "신림동"],
    "광진구": ["광장동", "구의동", "군자동", "능동", "자양동", "중곡동", "화양동"],
    "구로구": ["가리봉동", "개봉동", "고척동", "구로동", "궁동", "신도림동", "오류동", "온수동", "천왕동", "항동"],
    "금천구": ["가산동", "독산동", "시흥동"],
    "노원구": ["공릉동", "상계동", "월계동", "중계동", "하계동"],
    "도봉구": ["도봉동", "방학동", "쌍문동", "창동"],
    "동대문구": ["답십리동", "신설동", "용두동", "이문동", "장안동", "전농동", "제기동", "청량리동", "회기동", "휘경동"],
    "동작구": ["노량진동", "대방동", "동작동", "본동", "사당동", "상도1동", "상도동", "신대방동", "흑석동"],
    "마포구": ["공덕동", "구수동", "노고산동", "당인동", "대흥동", "도화동", "동교동", "마포동", "망원동", "상수동", "상암동", "서교동", "성산동", "신공덕동", "신수동", "신정동", "아현동", "연남동", "염리동", "용강동", "중동", "창전동", "토정동", "하중동", "합정동", "현석동"],
    "서대문구": ["남가좌동", "냉천동", "대신동", "대현동", "미근동", "봉원동", "북가좌동", "북아현동", "신촌동", "연희동", "영천동", "옥천동", "창천동", "천연동", "충정로2가", "충정로3가", "합동", "현저동", "홍은동", "홍제동"],
    "서초구": ["내곡동", "반포동", "방배동", "서초동", "신원동", "양재동", "염곡동", "우면동", "원지동", "잠원동"],
    "성동구": ["금호동1가", "금호동2가", "금호동3가", "금호동4가", "도선동", "마장동", "사근동", "상왕십리동", "성수동1가", "성수동2가", "송정동", "옥수동", "용답동", "응봉동", "하왕십리동", "행당동", "홍익동"],
    "성북구": ["길음동", "돈암동", "동선동1가", "동선동2가", "동선동3가", "동선동4가", "동선동5가", "동소문동1가", "동소문동2가", "동소문동3가", "동소문동4가", "동소문동5가", "동소문동6가", "동소문동7가", "보문동1가", "보문동2가", "보문동3가", "보문동4가", "보문동5가", "보문동6가", "보문동7가", "삼선동1가", "삼선동2가", "삼선동3가", "삼선동4가", "삼선동5가", "상월곡동", "석관동", "성북동", "성북동1가", "안암동1가", "안암동2가", "안암동3가", "안암동4가", "안암동5가", "장위동", "정릉동", "종암동", "하월곡동"],
    "송파구": ["가락동", "거여동", "마천동", "문정동", "방이동", "삼전동", "석촌동", "송파동", "신천동", "오금동", "잠실동", "장지동", "풍납동"],
    "양천구": ["목동", "신월동", "신정동"],
    "영등포구": ["당산동", "당산동1가", "당산동2가", "당산동3가", "당산동4가", "당산동5가", "당산동6가", "대림동", "도림동", "문래동1가", "문래동2가", "문래동3가", "문래동4가", "문래동5가", "문래동6가", "신길동", "양평동", "양평동1가", "양평동2가", "양평동3가", "양평동4가", "양평동5가", "양평동6가", "양화동", "여의도동", "영등포동", "영등포동1가", "영등포동2가", "영등포동3가", "영등포동4가", "영등포동5가", "영등포동6가", "영등포동7가", "영등포동8가"],
    "용산구": ["갈월동", "남영동", "도원동", "동빙고동", "동자동", "문배동", "보광동", "산천동", "서계동", "서빙고동", "신계동", "신창동", "용문동", "용산동1가", "용산동2가", "용산동3가", "용산동4가", "용산동5가", "용산동6가", "원효로1가", "원효로2가", "원효로3가", "원효로4가", "이촌동", "이태원동", "주성동", "청암동", "청파동1가", "청파동2가", "청파동3가", "한강로1가", "한강로2가", "한강로3가", "한남동", "효창동", "후암동"],
    "은평구": ["갈현동", "구산동", "녹번동", "대조동", "불광동", "수색동", "신사동", "역촌동", "응암동", "증산동", "진관동"],
    "종로구": ["가회동", "견지동", "경운동", "계동", "공평동", "관수동", "관철동", "관훈동", "교남동", "교북동", "구기동", "궁정동", "권농동", "낙원동", "내수동", "내자동", "누상동", "누하동", "당주동", "도렴동", "돈의동", "동숭동", "명륜1가", "명륜2가", "명륜3가", "명륜4가", "묘동", "무악동", "봉익동", "부암동", "사간동", "사직동", "삼청동", "서린동", "세종로", "소격동", "송월동", "송현동", "수송동", "숭인동", "신교동", "신문로1가", "신문로2가", "신영동", "안국동", "연건동", "연지동", "예지동", "옥인동", "와룡동", "운니동", "원남동", "원서동", "이화동", "익선동", "인사동", "인의동", "장사동", "재동", "적선동", "종로1가", "종로2가", "종로3가", "종로4가", "종로5가", "종로6가", "중학동", "창성동", "창신동", "청운동", "청진동", "체부동", "충신동", "통의동", "통인동", "팔판동", "평창동", "평동", "필운동", "행촌동", "혜화동", "홍지동", "홍파동", "화동", "효자동", "효제동", "훈정동"],
    "중구": ["광희동1가", "광희동2가", "남대문로1가", "남대문로2가", "남대문로3가", "남대문로4가", "남대문로5가", "남산동1가", "남산동2가", "남산동3가", "남창동", "남학동", "다동", "만리동1가", "만리동2가", "명동1가", "명동2가", "무교동", "무학동", "묵정동", "방산동", "봉래동1가", "봉래동2가", "북창동", "산림동", "삼각동", "서소문동", "소공동", "수표동", "수하동", "순화동", "신당동", "쌍림동", "예관동", "예장동", "오장동", "의주로1가", "의주로2가", "을지로1가", "을지로2가", "을지로3가", "을지로4가", "을지로5가", "을지로6가", "을지로7가", "인현동1가", "인현동2가", "입정동", "장교동", "장충동1가", "장충동2가", "저동1가", "저동2가", "정동", "주교동", "주자동", "중림동", "초동", "충무로1가", "충무로2가", "충무로3가", "충무로4가", "충무로5가", "충정로1가", "태평로1가", "태평로2가", "필동1가", "필동2가", "필동3가", "황학동", "회현동1가", "회현동2가", "회현동3가", "흥인동"],
    "중랑구": ["망우동", "면목동", "묵동", "상봉동", "신내동", "중화동"]
}

VIP_APARTMENT_DB = {
    "대치동_은마": {76.79: 101.52, 84.43: 115.0}, 
    "여의도동_시범": {60.96: 62.79, 79.24: 79.24, 118.12: 118.12, 156.99: 156.99},
    "여의도동_대교": {95.50: 100.19, 133.40: 142.14},
    "여의도동_진주": {48.26: 49.71, 63.83: 65.74, 72.82: 76.03},
    "압구정동_신현대9차": {111.38: 115.7, 152.22: 165.28, 183.41: 198.34},
    "압구정동_미성1차": {105.65: 112.4, 153.36: 165.28},
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

@st.cache_data(show_spinner=False, ttl=86400)
def get_ultimate_supply_area(api_key, lawd_cd, umd_cd, jibun, apt_name, exclu_area, prop_type, build_year, dong_name):
    if "아파트" in prop_type:
        search_key = f"{dong_name}_{apt_name.replace('아파트', '').strip()}"
        if search_key in VIP_APARTMENT_DB:
            for db_exclu, db_supply in VIP_APARTMENT_DB[search_key].items():
                if abs(db_exclu - exclu_area) < 1.0:
                    return db_supply

    try: year = int(build_year)
    except: year = 2000

    if "아파트" in prop_type:
        if year < 1980: rate = 1.03
        elif year < 1995: rate = 1.15
        elif year < 2005: rate = 1.25
        else: rate = 1.3333
    elif "오피스텔" in prop_type: rate = 2.0 
    elif "단독" in prop_type or "토지" in prop_type: rate = 1.0 
    elif "연립" in prop_type or "다세대" in prop_type: rate = 1.25 
    else: rate = 1.3333 

    fallback_area = round(exclu_area * rate, 2)
    
    if not umd_cd or not jibun or str(jibun) == "0" or "단독" in prop_type or "토지" in prop_type:
        return fallback_area

    bjd_code = f"{lawd_cd}{umd_cd.zfill(5)}"
    safe_api_key = urllib.parse.unquote(api_key)
    
    if "아파트" in prop_type:
        try:
            kapt_url = "http://apis.data.go.kr/1613000/AptBasisInfoService1/getAptList"
            params = {"serviceKey": safe_api_key, "bjdCode": bjd_code, "numOfRows": "100"}
            res = requests.get(kapt_url, params=params, timeout=2, verify=False)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall('.//item'):
                    kapt_name = get_multi_xml_text(item, ['kaptName'])
                    clean_apt = apt_name.replace("아파트", "").replace(" ", "")
                    clean_kapt = kapt_name.replace("아파트", "").replace(" ", "")
                    if clean_apt in clean_kapt or clean_kapt in clean_apt:
                        return round(exclu_area * 1.33, 2)
        except: pass

    try:
        jibun_parts = str(jibun).replace(" ", "").split('-')
        bun = jibun_parts[0].zfill(4)
        ji = jibun_parts[1].zfill(4) if len(jibun_parts) > 1 else "0000"
        
        bld_url = "https://apis.data.go.kr/1613000/BldRgstService_v2/getBldRgstExposPubuseAreaInfo"
        bld_params = {
            "serviceKey": safe_api_key, "sigunguCd": lawd_cd, "bjdongCd": umd_cd, 
            "platGbCd": "0", "bun": bun, "ji": ji, "numOfRows": "100"
        }
        bld_res = requests.get(bld_url, params=bld_params, timeout=2, verify=False)
        if bld_res.status_code == 200:
            bld_root = ET.fromstring(bld_res.content)
            items = bld_root.findall('.//item')
            common_area = 0.0
            matched = False
            for item in items:
                purps = get_multi_xml_text(item, ['etcPurpsNm', 'mainPurpsNm'], "")
                area_val = float(get_multi_xml_text(item, ['area'], "0"))
                if "주차" not in purps and "지하" not in purps:
                    if any(k in purps for k in ["계단", "복도", "현관", "승강기", "엘리베이터", "공용"]):
                        common_area += area_val
                        matched = True
            if matched and 0 < common_area <= exclu_area * 0.8:
                return round(exclu_area + common_area, 2)
    except: pass

    return fallback_area

st.markdown("""
<div class="header-box">
    <h2>🏠 부동산 실거래 분석기 <span style="font-size:14px; background:#e74c3c; color:white; padding:4px 10px; border-radius:20px; vertical-align: middle; margin-left:10px;">v11.3 전용 엔진</span></h2>
    <p>구축 아파트 평수 오기 자동 수정 및 K-apt 역산 엔진 탑재</p>
</div>
""", unsafe_allow_html=True)

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

execute_btn = st.button("위 조건으로 빅데이터 병렬 추출 및 시각화 대시보드 생성", use_container_width=True)

URL_APT_T = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
URL_OFF_T = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
URL_VIL_T = "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
URL_HOU_T = "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
URL_APT_R = "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"
URL_OFF_R = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
URL_VIL_R = "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
URL_HOU_R = "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
URL_BUN   = "https://apis.data.go.kr/1613000/RTMSDataSvcSilvTrade/getRTMSDataSvcSilvTrade"
URL_BIZ   = "https://apis.data.go.kr/1613000/RTMSDataSvcBizTrade/getRTMSDataSvcBizTrade"
URL_LND   = "https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade"

if execute_btn:
    if "last_query_time" in st.session_state:
        elapsed = time.time() - st.session_state.last_query_time
        if elapsed < 10:
            st.error(f"🚨 무리한 서버 접근을 막기 위해 10초 후 다시 조회할 수 있습니다. (남은 대기 시간: {int(10 - elapsed)}초)")
            st.stop()
            
    st.session_state.last_query_time = time.time()

    if not selected_dongs: st.warning("⚠️ 분석할 동을 선택해주세요!")
    else:
        api_targets = []
        if opt_apt_trade: api_targets.append(("아파트 매매", URL_APT_T))
        if opt_off_trade: api_targets.append(("오피스텔 매매", URL_OFF_T))
        if opt_vil_trade: api_targets.append(("연립/다세대 매매", URL_VIL_T))
        if opt_house_trade: api_targets.append(("단독/다가구 매매", URL_HOU_T))
        if opt_apt_rent: api_targets.append(("아파트 전월세", URL_APT_R))
        if opt_off_rent: api_targets.append(("오피스텔 전월세", URL_OFF_R))
        if opt_vil_rent: api_targets.append(("연립/다세대 전월세", URL_VIL_R))
        if opt_house_rent: api_targets.append(("단독/다가구 전월세", URL_HOU_R))
        if opt_apt_bun: api_targets.append(("분양권/전매", URL_BUN))
        if opt_biz_trade: api_targets.append(("상업/업무용", URL_BIZ))
        if opt_land_trade: api_targets.append(("토지 매매", URL_LND))

        if not api_targets: st.error("🚨 수집할 데이터를 체크해 주세요!")
        else:
            all_data = []
            lawd_cd = SEOUL_GU_CD[selected_gu]
            
            with st.status("⏳ **대용량 부동산 빅데이터를 추출하는 중입니다...** (1~2분 소요)", expanded=True) as status:
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                for idx, (prop_type, url) in enumerate(api_targets):
                    progress_text.markdown(f"📡 **[{prop_type}]** 백그라운드 엔진 가동 중... ({idx+1}/{len(api_targets)})")
                    try:
                        res = requests.get(url, params={"serviceKey": urllib.parse.unquote(final_api_key), "LAWD_CD": lawd_cd, "DEAL_YMD": target_month, "numOfRows": "2000"}, timeout=20, verify=False)
                        if res.status_code == 200:
                            root = ET.fromstring(res.content)
                            items = root.findall('.//item')
                            for item in items:
                                item_dong = get_multi_xml_text(item, ['umdNm', 'dongNm', 'sggNm'], "")
                                if "전체 (해당 구 모든 동)" in selected_dongs or any(d in item_dong for d in selected_dongs):
                                    apt_name = get_multi_xml_text(item, ['aptNm', 'offiNm', 'mhouseNm', 'bldgNm', 'rletTypeNm'], "건물명 없음")
                                    
                                    # 💡 미나의 철통 방어막 1: 숫자 변환 에러가 나도 절대 스킵되지 않도록 보호!
                                    raw_p = get_multi_xml_text(item, ['dealAmount'], "0").replace(",", "").strip()
                                    dep_p = get_multi_xml_text(item, ['deposit'], "0").replace(",", "").strip()
                                    mon_p = get_multi_xml_text(item, ['monthlyRent', 'rentAmt'], "0").replace(",", "").strip()
                                    
                                    try: raw_p_int = int(raw_p) if raw_p else 0
                                    except: raw_p_int = 0
                                    try: dep_p_int = int(dep_p) if dep_p else 0
                                    except: dep_p_int = 0
                                    try: mon_p_int = int(mon_p) if mon_p else 0
                                    except: mon_p_int = 0
                                    
                                    umd_cd = get_multi_xml_text(item, ['umdCd', 'bjdongCd'], "")
                                    jibun = get_multi_xml_text(item, ['jibun'], "")
                                    build_year = get_multi_xml_text(item, ['buildYear'], "2000")
                                    
                                    # 💡 미나의 철통 방어막 2: 토지, 상가 등 '거래면적(dealArea)' 태그 누락까지 방어!
                                    area_raw = get_multi_xml_text(item, ['excluUseAr', 'plottage', 'spc', 'dealArea'], "0.0")
                                    try: area_exc = float(area_raw)
                                    except: area_exc = 0.0
                                    py_exc = round(area_exc / 3.3058, 2) 
                                    
                                    supply_area = get_ultimate_supply_area(final_api_key, lawd_cd, umd_cd, jibun, apt_name, area_exc, prop_type, build_year, item_dong)
                                    py_sup = round(supply_area / 3.3058, 2)

                                    if raw_p_int > 0:
                                        num_p = raw_p_int * 10000; p_man = raw_p_int
                                        disp_p = format_currency(num_p)
                                    else:
                                        num_p = dep_p_int * 10000; p_man = dep_p_int
                                        disp_p = f"보증금 {format_currency(num_p)} / 월세 {mon_p_int*10000:,}원"
                                    
                                    p_per_py_exc = int(num_p / py_exc) if py_exc > 0 else 0
                                    p_per_py_sup = int(num_p / py_sup) if py_sup > 0 else 0
                                    
                                    # 💡 미나의 철통 방어막 3: 취소일자(cancelDealDay) 신규 변수명까지 호환 적용
                                    cancel_flag = get_multi_xml_text(item, ['cdealDay', 'cancelDealDay'])
                                    
                                    # 💡 미나의 철통 방어막 4: 계약일이 '11~20' 범위로 들어와도 에러 없이 깔끔하게 '11'일로 처리!
                                    deal_y = get_multi_xml_text(item, ['dealYear'])
                                    deal_m = get_multi_xml_text(item, ['dealMonth'], "1").zfill(2)
                                    raw_day = get_multi_xml_text(item, ['dealDay'], "1").replace(" ", "")
                                    deal_d = raw_day.split("~")[0].zfill(2) if "~" in raw_day else raw_day.zfill(2)
                                    
                                    all_data.append({
                                        "계약일": f"{deal_y}-{deal_m}-{deal_d}", 
                                        "분류": prop_type, "법정동": item_dong, "부동산/건물명": apt_name, "층수": f"{get_multi_xml_text(item, ['floor'])}층",
                                        
                                        "전용 면적(㎡)": round(area_exc, 2), "전용 평수(평)": py_exc, 
                                        "공급 면적(㎡)": supply_area, "공급 평수(평)": py_sup,
                                        
                                        "거래금액": disp_p, "거래금액(만원)": p_man,
                                        "평당 거래가(전용)": format_currency(p_per_py_exc) if raw_p_int > 0 else "-",
                                        "평당 거래가(공급)": format_currency(p_per_py_sup) if raw_p_int > 0 else "-",
                                        "취소 여부": "취소됨" if cancel_flag else "정상",
                                        
                                        "_raw_price": num_p, "_raw_pyeong_price": p_per_py_exc
                                    })
                    except Exception as e:
                        pass
                    
                    progress_bar.progress((idx + 1) / len(api_targets))
                    
                progress_text.empty()
                progress_bar.empty()
                status.update(label="✅ **모든 데이터 추출 및 융합이 완료되었습니다!**", state="complete", expanded=False)

            if all_data:
                df = pd.DataFrame(all_data)
                valid_df = df[df['취소 여부'] == '정상']
                if not valid_df.empty:
                    st.markdown("<div class='category-title'>📊 3. 전체 수집 데이터 요약 브리핑</div>", unsafe_allow_html=True)
                    trade_df = valid_df[valid_df['_raw_pyeong_price'] > 0]
                    avg_p = int(trade_df['_raw_pyeong_price'].mean()) if not trade_df.empty else 0
                    max_row = trade_df.loc[trade_df['_raw_price'].idxmax()] if not trade_df.empty else None
                    
                    c_m1, c_m2, c_m3 = st.columns(3)
                    c_m1.metric("📌 총 정상 거래 건수", f"{len(valid_df)} 건")
                    c_m2.metric("💸 매매 평균 평당가 (전용 기준)", f"{format_currency(avg_p)}")
                    c_m3.metric(f"🏆 매매 최고가", format_currency(max_row['_raw_price']) if max_row is not None else "-")

                    if not trade_df.empty:
                        st.markdown("<div class='category-title'>📈 4. 매매가 기준 단지별 정밀 시각화</div>", unsafe_allow_html=True)
                        ch_col1, ch_col2 = st.columns(2)
                        with ch_col1:
                            st.markdown("**🏆 1) 지역 내 매매 최고가 순위 20위 (가로형)**")
                            top20 = trade_df.copy()
                            top20['단지_평수'] = top20['부동산/건물명'] + " (" + top20['전용 평수(평)'].astype(str) + "평)"
                            top20 = top20.sort_values(by='_raw_price', ascending=False).drop_duplicates(subset=['단지_평수']).nlargest(20, '_raw_price')
                            top20['거래금액(억)'] = top20['_raw_price'] / 100000000
                            
                            bar = alt.Chart(top20).mark_bar(color="#E74C3C", cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
                                x=alt.X('거래금액(억):Q', title='거래금액 (억)'),
                                y=alt.Y('단지_평수:N', sort='-x', title=None),
                                tooltip=['단지_평수', '거래금액(억)']
                            ).properties(height=500)
                            st.altair_chart(bar, use_container_width=True)
                        with ch_col2:
                            st.markdown("**📐 2) 전용 면적(평) vs 거래금액 상관관계**")
                            sc_df = trade_df.copy(); sc_df['거래금액(억)'] = sc_df['_raw_price'] / 100000000
                            sc = alt.Chart(sc_df).mark_circle(size=60, color="#3b4890").encode(
                                x=alt.X('전용 평수(평):Q', title='전용 면적 (평)'), y=alt.Y('거래금액(억):Q', title='거래금액 (억)'),
                                tooltip=['부동산/건물명', '전용 평수(평)', '공급 평수(평)', '거래금액(억)']
                            ).properties(height=500)
                            st.altair_chart(sc, use_container_width=True)
                
                st.markdown("<div class='category-title'>📋 5. 전체 상세 데이터 확인 및 엑셀 다운로드</div>", unsafe_allow_html=True)
                
                display_df = df.drop(columns=['_raw_price', '_raw_pyeong_price']).copy()
                display_df = display_df.sort_values(by=["분류", "계약일"], ascending=[True, False]).reset_index(drop=True)
                
                st.dataframe(display_df.style.format({
                    "거래금액(만원)": "{:,}", 
                    "전용 면적(㎡)": "{:.2f}", "전용 평수(평)": "{:.2f}",
                    "공급 면적(㎡)": "{:.2f}", "공급 평수(평)": "{:.2f}"
                }), use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, sheet_name='종합 실거래가', index=False)
                    workbook, worksheet = writer.book, writer.sheets['종합 실거래가']
                    
                    header_format = workbook.add_format({
                        'bg_color': '#3b4890', 
                        'font_color': '#FFFFFF', 
                        'bold': True, 
                        'border': 1, 
                        'align': 'center', 
                        'valign': 'vcenter'
                    })
                    
                    num_fmt = workbook.add_format({'num_format': '#,##0'}) 
                    float_fmt = workbook.add_format({'num_format': '#,##0.00'}) 
                    
                    for i, col in enumerate(display_df.columns):
                        worksheet.write(0, i, col, header_format)
                        if "만원" in col: worksheet.set_column(i, i, 15, num_fmt)
                        elif "면적" in col or "평수" in col: worksheet.set_column(i, i, 15, float_fmt)
                        elif "평당" in col: worksheet.set_column(i, i, 20)
                        else: worksheet.set_column(i, i, 15)
                
                st.download_button("📥 엑셀 다운로드", data=output.getvalue(), file_name=f"{selected_gu}_부동산데이터.xlsx", type="primary")
            else: st.warning("데이터가 존재하지 않습니다.")

st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
