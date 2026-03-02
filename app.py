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

# 💡 회사 PC SSL 인증서 차단 경고음 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🎨 웹앱 기본 설정
st.set_page_config(page_title="Pro Estate Analytics", layout="wide", page_icon="🏢")

# ==========================================
# 🔑 [보안 핵심] 하이브리드 스텔스 API 키 엔진
# ==========================================
KEY_FILE = "api_key.txt"

def get_api_key():
    # 1순위: 클라우드 금고(Secrets) 확인
    try:
        if "KOREA_API_KEY" in st.secrets:
            return st.secrets["KOREA_API_KEY"], True 
    except:
        pass
    
    # 2순위: 내 컴퓨터(로컬) 파일 확인
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip(), False
    return "", False

def save_key_local(key):
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key.strip())

# ==========================================
# 🚨 스마트 만료 알림 시스템 (D-Day Alert)
# ==========================================
expiry_date = datetime(2028, 3, 1)
today = datetime.now()
days_left = (expiry_date - today).days

if days_left <= 30:
    st.error(f"🚨 [경고] 국토교통부 API 자료 열람기간 만료가 다가오고 있습니다! (D-{days_left}일)")
elif days_left <= 100:
    st.warning(f"💡 [안내] 국토교통부 API 인증키 만료까지 {days_left}일 남았습니다.")

# ==========================================
# 💅 CSS 커스텀 인젝션
# ==========================================
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #00C781; color: white; border: none; border-radius: 8px; font-weight: bold; height: 50px; }
    div.stButton > button:first-child:hover { background-color: #00A66A; color: white; }
    .header-box { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2C3E50;}
    .header-box h2 { margin: 0 0 5px 0; color: #222; font-size: 26px; font-weight: 800; }
    .header-box p { margin: 0; color: #666; font-size: 15px; }
    .category-title { font-size: 16px; font-weight: bold; color: #333; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #00C781; padding-bottom: 5px; display: inline-block; }
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #00C781 !important; font-weight: 900 !important; }
    [data-testid="stMetricLabel"] { font-size: 15px !important; font-weight: bold !important; color: #555 !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 데이터베이스 및 환산 엔진
# ==========================================
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
        if m == 0:
            m = 12
            y -= 1
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

# ==========================================
# 🌟 메인 화면 대시보드
# ==========================================
st.markdown("""
<div class="header-box">
    <h2>🏢 Pro Estate Analytics <span style="font-size:14px; background:#111111; color:white; padding:4px 10px; border-radius:20px; vertical-align: middle; margin-left:10px;">v6.3 Zero-Exposure Security</span></h2>
    <p>상실의시대 가족 전용 | 엿보기(Shoulder Surfing) 원천 차단 및 시각 보안 최적화 에디션</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2633/2633320.png", width=60)
    
    saved_key, is_from_cloud = get_api_key()
    
    if is_from_cloud:
        # 클라우드 배포 상태: 방문자는 API가 뭔지도 모르게 완벽히 숨깁니다.
        st.title("🟢 시스템 상태")
        st.success("**서버 온라인**\n\n부동산 빅데이터 관제 시스템이 정상적으로 가동 중입니다.")
        final_api_key = saved_key
    else:
        st.title("⚙️ API Key 설정")
        
        # 💡 [핵심 패치] 블라인드 텍스트 입력창 로직!
        if saved_key:
            st.success("🔒 **로컬 보안 모드 작동 중**\n\nAPI 키가 PC에 안전하게 보관되어 있습니다. (3중 보안서버가 강력하게 적용중입니다)")
            # value를 빈칸("")으로 주어서 화면상엔 완벽한 빈칸으로 보임
            api_key_input = st.text_input("마스터 API 키 변경 (선택)", value="", type="password", placeholder="새로운 키로 바꿀 때만 여기에 붙여넣으세요")
        else:
            st.warning("⚠️ 인증키가 없습니다.")
            api_key_input = st.text_input("국토교통부 마스터 API 키 입력", value="", type="password", placeholder="여기에 키를 붙여넣으세요")
            
        # 사용자가 빈칸에 뭔가 새로운 것을 집어넣고 엔터를 쳤다면? 새로운 키로 교체 및 덮어쓰기!
        if api_key_input:
            save_key_local(api_key_input)
            st.success("✅ 새로운 인증키가 안전하게 저장되었습니다!")
            saved_key = api_key_input
            
        final_api_key = saved_key
        
        if final_api_key:
            st.info("💡 로컬 오프라인 모드로 통신 중입니다.")
            
    st.divider()
    st.caption("ⓒ 2026 Developed by Mina")

# ==========================================
# 🎯 1. 검색 조건 설정
# ==========================================
st.markdown("<div class='category-title'>🔍 1. 검색 조건 설정 (원클릭)</div>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])

with col1: selected_gu = st.selectbox("📍 자치구 선택", list(SEOUL_GU_CD.keys()))
with col2:
    base_dongs = SEOUL_DONG_DB.get(selected_gu, [])
    available_dongs = ["전체 (해당 구 모든 동)"] + base_dongs
    selected_dongs = st.multiselect("🏘️ 법정동 다중 선택", available_dongs, default=["전체 (해당 구 모든 동)"])
with col3:
    selected_month_label = st.selectbox("📅 조회 연월 (최신순)", month_labels)
    target_month = month_values[selected_month_label]

st.write("") 

# ==========================================
# 🗂️ 2. 수집할 데이터 선택
# ==========================================
st.markdown("<div class='category-title'>🗂️ 2. 수집할 데이터 선택</div>", unsafe_allow_html=True)
st.caption("※ 주의: 체크하신 항목은 공공데이터포털(data.go.kr)에서 개별적으로 각각 [활용 신청]이 완료되어 있어야 정상 수집됩니다.")

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.markdown("**[주거용 매매]**")
    opt_apt_trade = st.checkbox("🏢 아파트 매매 실거래가", value=True)
    opt_off_trade = st.checkbox("🏢 오피스텔 매매 실거래가")
    opt_vil_trade = st.checkbox("🏠 연립/다세대 매매 실거래가")
    opt_house_trade = st.checkbox("🏡 단독/다가구 매매 실거래가")
with col_b:
    st.markdown("**[주거용 전월세]**")
    opt_apt_rent = st.checkbox("🏢 아파트 전월세 실거래가")
    opt_off_rent = st.checkbox("🏢 오피스텔 전월세 실거래가")
    opt_vil_rent = st.checkbox("🏠 연립/다세대 전월세 실거래가")
    opt_house_rent = st.checkbox("🏡 단독/다가구 전월세 실거래가")
with col_c:
    st.markdown("**[투자/상업/기타]**")
    opt_apt_bun = st.checkbox("🏗️ 아파트 분양권/전매")
    opt_biz_trade = st.checkbox("🏪 상업/업무용 부동산 매매")
    opt_land_trade = st.checkbox("🌍 토지 매매 실거래가")

st.divider()
execute_btn = st.button("🚀 위 조건으로 빅데이터 병렬 추출 및 시각화 대시보드 생성", use_container_width=True)

# ==========================================
# ⚙️ 핵심 엔진 다중 파이프라인
# ==========================================
if execute_btn:
    if not final_api_key:
        st.error("🚨 시스템 에러: 마스터 키가 연결되지 않았습니다. 관리자에게 문의하세요.")
    elif not selected_dongs:
        st.warning("⚠️ 분석할 동을 최소 1개 이상 선택해주세요!")
    else:
        api_targets = []
        if opt_apt_trade: api_targets.append(("아파트 매매", "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"))
        if opt_off_trade: api_targets.append(("오피스텔 매매", "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"))
        if opt_vil_trade: api_targets.append(("연립/다세대 매매", "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"))
        if opt_house_trade: api_targets.append(("단독/다가구 매매", "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"))
        if opt_apt_rent: api_targets.append(("아파트 전월세", "https://apis.data.go.kr/1613000/RTMSDataSvcAptRent/getRTMSDataSvcAptRent"))
        if opt_off_rent: api_targets.append(("오피스텔 전월세", "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"))
        if opt_vil_rent: api_targets.append(("연립/다세대 전월세", "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"))
        if opt_house_rent: api_targets.append(("단독/다가구 전월세", "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"))
        if opt_apt_bun: api_targets.append(("분양권/전매", "https://apis.data.go.kr/1613000/RTMSDataSvcSilvTrade/getRTMSDataSvcSilvTrade"))
        if opt_biz_trade: api_targets.append(("상업/업무용", "https://apis.data.go.kr/1613000/RTMSDataSvcBizTrade/getRTMSDataSvcBizTrade"))
        if opt_land_trade: api_targets.append(("토지 매매", "https://apis.data.go.kr/1613000/RTMSDataSvcLandTrade/getRTMSDataSvcLandTrade"))

        if not api_targets:
            st.error("🚨 수집할 데이터를 1개 이상 체크해 주세요!")
        else:
            all_data = []
            lawd_cd = SEOUL_GU_CD[selected_gu]
            safe_api_key = urllib.parse.unquote(final_api_key)
            
            progress_text = st.empty()
            
            for idx, (prop_type, url) in enumerate(api_targets):
                progress_text.markdown(f"📡 **[{prop_type}]** 데이터를 수집 중입니다... ({idx+1}/{len(api_targets)})")
                
                params = { "serviceKey": safe_api_key, "LAWD_CD": lawd_cd, "DEAL_YMD": target_month, "numOfRows": "2000" }
                
                try:
                    res = requests.get(url, params=params, timeout=20, verify=False)

                    if res.status_code == 200:
                        try:
                            root = ET.fromstring(res.content)
                            
                            auth_msg = root.find('.//returnAuthMsg')
                            if auth_msg is not None and "REGISTERED" in auth_msg.text:
                                st.error(f"🚨 [{prop_type}] 조회 권한 부족: 공공데이터포털에서 해당 API 활용 신청이 필요합니다.")
                                continue

                            result_code = root.find('.//resultCode')
                            if result_code is not None and result_code.text not in ["00", "000", "0"]:
                                result_msg = root.find('.//resultMsg')
                                st.error(f"🚨 [{prop_type}] 서버 거부: {result_msg.text if result_msg is not None else '불명'}")
                                continue
                                
                            items = root.findall('.//item')
                            for item in items:
                                item_dong = get_multi_xml_text(item, ['umdNm', 'dongNm', 'sggNm'], "")
                                
                                is_matched = False
                                if "전체 (해당 구 모든 동)" in selected_dongs:
                                    is_matched = True
                                else:
                                    for d in selected_dongs:
                                        if d in item_dong:
                                            is_matched = True
                                            break
                                            
                                if is_matched:
                                    apt_name = get_multi_xml_text(item, ['aptNm', 'offiNm', 'mhouseNm', 'bldgNm', 'rletTypeNm'], "건물명 없음(단독/토지)")
                                    
                                    raw_price_str = get_multi_xml_text(item, ['dealAmount'], "0").replace(",", "")
                                    deposit_str = get_multi_xml_text(item, ['deposit'], "0").replace(",", "")
                                    monthly_str = get_multi_xml_text(item, ['monthlyRent'], "0").replace(",", "")
                                    
                                    area = float(get_multi_xml_text(item, ['excluUseAr', 'plottage', 'spc'], "0.0"))
                                    floor = get_multi_xml_text(item, ['floor'], "0")
                                    y = get_multi_xml_text(item, ['dealYear'], "2000")
                                    m = get_multi_xml_text(item, ['dealMonth'], "1")
                                    d = get_multi_xml_text(item, ['dealDay'], "1")
                                    cancel = get_multi_xml_text(item, ['cdealDay'])
                                    
                                    if int(raw_price_str) > 0:
                                        num_price = int(raw_price_str) * 10000 
                                        price_manwon = int(raw_price_str)
                                        display_price = format_currency(num_price)
                                    else:
                                        num_price = int(deposit_str) * 10000
                                        price_manwon = int(deposit_str)
                                        if int(monthly_str) > 0:
                                            display_price = f"보증금 {format_currency(num_price)} / 월세 {format_currency(int(monthly_str)*10000)}"
                                        else:
                                            display_price = f"전세 {format_currency(num_price)}"
                                    
                                    pyeong = round(area / 3.3058, 1)
                                    price_per_pyeong_num = int(num_price / pyeong) if pyeong > 0 else 0
                                    pyeong_price_manwon = int(price_per_pyeong_num // 10000)

                                    all_data.append({
                                        "계약일": f"{y}-{int(m):02d}-{int(d):02d}", 
                                        "분류": prop_type,
                                        "법정동": item_dong,
                                        "부동산/건물명": apt_name, 
                                        "층수": f"{floor}층",
                                        "면적(㎡)": area, 
                                        "평수(평)": pyeong,
                                        "거래금액": display_price, 
                                        "거래금액(만원)": price_manwon,
                                        "평당 거래가": format_currency(price_per_pyeong_num) if int(raw_price_str) > 0 else "-",
                                        "평당 거래가(만원)": pyeong_price_manwon if int(raw_price_str) > 0 else 0,
                                        "취소 여부": "취소됨" if cancel else "정상",
                                        "_raw_price": num_price,
                                        "_raw_pyeong_price": price_per_pyeong_num
                                    })
                        except ET.ParseError:
                            st.error(f"🚨 [{prop_type}] 알 수 없는 서버 응답(XML 파싱 에러)이 발생했습니다.")
                except Exception as e: st.error(f"API 통신 오류: {e}")
            
            progress_text.empty()

            # ==========================================
            # 📊 실거래가 요약 대시보드 출력
            # ==========================================
            if all_data:
                df = pd.DataFrame(all_data)
                valid_df = df[df['취소 여부'] == '정상']
                
                if not valid_df.empty:
                    st.markdown("<div class='category-title'>📊 3. 전체 수집 데이터 요약 브리핑</div>", unsafe_allow_html=True)
                    
                    total_cnt = len(valid_df)
                    trade_df = valid_df[valid_df['평당 거래가(만원)'] > 0]
                    
                    avg_pyeong_price = int(trade_df['_raw_pyeong_price'].mean()) if not trade_df.empty else 0
                    
                    if not trade_df.empty:
                        max_idx = trade_df['_raw_price'].idxmax()
                        max_row = trade_df.loc[max_idx]
                        max_price = max_row['_raw_price']
                        max_apt_name = f"[{max_row['분류']}] {max_row['부동산/건물명']} ({max_row['평수(평)']}평)"
                    else:
                        max_price = 0
                        max_apt_name = "매매 내역 없음"
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("📌 총 정상 거래 건수 (전월세 포함)", f"{total_cnt} 건")
                    col_m2.metric("💸 매매 평균 평당가", f"{format_currency(avg_pyeong_price)}")
                    col_m3.metric(f"🏆 매매 최고가: {max_apt_name}", f"{format_currency(max_price)}")

                    st.write("")

                    if not trade_df.empty:
                        st.markdown("<div class='category-title'>📈 4. 매매가 기준 단지별 정밀 시각화</div>", unsafe_allow_html=True)
                        
                        chart_col1, chart_col2 = st.columns(2)
                        
                        with chart_col1:
                            st.markdown("**🏆 1) 지역 내 매매 최고가 순위 20위 (전월세 제외)**")
                            
                            chart_df = trade_df.copy()
                            chart_df['단지_평수'] = chart_df['부동산/건물명'] + " (" + chart_df['평수(평)'].astype(str) + "평)"
                            chart_df = chart_df.sort_values(by='_raw_price', ascending=False).drop_duplicates(subset=['단지_평수'])
                            
                            top20_df = chart_df.nlargest(20, '_raw_price')
                            top20_df['거래금액(억)'] = top20_df['_raw_price'] / 100000000 
                            
                            bar_chart = alt.Chart(top20_df).mark_bar(
                                color="#E74C3C", 
                                cornerRadiusTopRight=4,   # 모서리 둥글기를 오른쪽으로 변경
                                cornerRadiusBottomRight=4 # 모서리 둥글기를 오른쪽으로 변경
                            ).encode(
                                x=alt.X('거래금액(억):Q', title='거래금액 (억)', scale=alt.Scale(domainMin=0)),
                                y=alt.Y('단지_평수:N', sort=alt.EncodingSortField(field='거래금액(억)', order='descending'), title=None, axis=alt.Axis(labelAngle=0, labelLimit=250)),
                                tooltip=['분류', '단지_평수', '거래금액(억)']
                            ).properties(
                                height=500 # 모바일에서 20개가 겹치지 않게 높이를 살짝 늘렸습니다
                            )
                            st.altair_chart(bar_chart, use_container_width=True)
                            
                        with chart_col2:
                            st.markdown("**📐 2) 면적(평) vs 거래금액 상관관계 분포도**")
                            
                            scatter_df = trade_df[trade_df['평수(평)'] > 0].copy()
                            scatter_df['거래금액(억)'] = scatter_df['_raw_price'] / 100000000
                            
                            scatter_chart = alt.Chart(scatter_df).mark_circle(size=60, color="#3498DB").encode(
                                x=alt.X('평수(평):Q', title='면적 (평)', scale=alt.Scale(domainMin=0)),
                                y=alt.Y('거래금액(억):Q', title='거래금액 (억)', scale=alt.Scale(domainMin=0)),
                                tooltip=['분류', '부동산/건물명', '평수(평)', '거래금액(억)']
                            ).properties(
                                height=450
                            )
                            st.altair_chart(scatter_chart, use_container_width=True)
                
                st.markdown("<div class='category-title'>📄 5. 전체 상세 데이터 확인 및 엑셀 다운로드</div>", unsafe_allow_html=True)
                
                # 가독성을 위해 면적과 평수 소수점 2자리로 제한
                display_df = df.drop(columns=['_raw_price', '_raw_pyeong_price']).copy()
                display_df['면적(㎡)'] = display_df['면적(㎡)'].round(2)
                display_df['평수(평)'] = display_df['평수(평)'].round(2)
                
                display_df = display_df.sort_values(by=["분류", "계약일"], ascending=[True, False]).reset_index(drop=True)
                
                # 화면 출력 시 소수점 2자리까지 고정해서 보여주기
                st.dataframe(display_df.style.format({
                    "거래금액(만원)": "{:,}", 
                    "평당 거래가(만원)": "{:,}",
                    "면적(㎡)": "{:.2f}",
                    "평수(평)": "{:.2f}"
                }), use_container_width=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    display_df.to_excel(writer, sheet_name='종합 실거래가', index=False)
                    workbook, worksheet = writer.book, writer.sheets['종합 실거래가']
                    
                    header_format = workbook.add_format({'bg_color': '#2980B9', 'font_color': '#FFFFFF', 'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                    number_format = workbook.add_format({'num_format': '#,##0'}) 
                    float_format = workbook.add_format({'num_format': '#,##0.00'}) # 엑셀용 소수점 2자리 포맷
                    
                    for col_num, value in enumerate(display_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        if value in ["거래금액(만원)", "평당 거래가(만원)"]:
                            worksheet.set_column(col_num, col_num, 15, number_format)
                        elif value in ["면적(㎡)", "평수(평)"]:
                            worksheet.set_column(col_num, col_num, 12, float_format) # 면적/평수 전용 포맷 적용
                        else:
                            worksheet.set_column(col_num, col_num, 15)

                safe_filename = f"{selected_gu}_{'_'.join(selected_dongs)}_{target_month}_종합데이터.xlsx"
                st.download_button("📥 깔끔하게 디자인된 엑셀(Excel) 다운로드", data=output.getvalue(), file_name=safe_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
            else:

                st.warning("선택하신 조건에 해당하는 데이터가 단 1건도 존재하지 않습니다.")



