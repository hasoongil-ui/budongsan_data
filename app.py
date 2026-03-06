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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 🎨 웹앱 기본 설정 (오재미에 쏙 들어가도록 깔끔하게!)
st.set_page_config(page_title="프로 부동산 실거래 분석기", layout="wide")

# ==========================================
# 🔑 [보안 핵심] 화면에서 키 입력창을 없애고 서버 비밀 금고(Secrets)에서 꺼내옵니다!
# ==========================================
try:
    # 💡 스트림릿 클라우드의 'Secrets' 설정에 KOREA_API_KEY 를 넣어두시면 됩니다!
    final_api_key = st.secrets["KOREA_API_KEY"]
except:
    st.error("🚨 서버 비밀 금고에 API 키가 설정되지 않았습니다! 관리자에게 문의하세요.")
    st.stop()

# 💅 CSS 커스텀 인젝션 (오재미 테마에 맞춤)
st.markdown("""
<style>
    div.stButton > button:first-child { background-color: #3b4890; color: white; border: none; border-radius: 4px; font-weight: bold; height: 50px; }
    div.stButton > button:first-child:hover { background-color: #2a3042; color: white; }
    .category-title { font-size: 16px; font-weight: bold; color: #333; margin-top: 20px; margin-bottom: 15px; border-bottom: 2px solid #3b4890; padding-bottom: 5px; display: inline-block; }
    [data-testid="stMetricValue"] { font-size: 28px !important; color: #e74c3c !important; font-weight: 900 !important; }
</style>
""", unsafe_allow_html=True)

# 🧠 데이터베이스 (대표님의 기존 완벽한 DB 유지)
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
            
            with st.status("⏳ **대용량 부동산 빅데이터를 안전하게 추출하는 중입니다...** (1~2분 소요)", expanded=True) as status:
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                for idx, (prop_type, url) in enumerate(api_targets):
                    progress_text.markdown(f"📡 **[{prop_type}]** 백그라운드 V11 얼티밋 엔진 가동 중... ({idx+1}/{len(api_targets)})")
                    try:
                        res = requests.get(url, params={"serviceKey": urllib.parse.unquote(final_api_key), "LAWD_CD": lawd_cd, "DEAL_YMD": target_month, "numOfRows": "2000"}, timeout=20, verify=False)
                        if res.status_code == 200:
                            root = ET.fromstring(res.content)
                            items = root.findall('.//item')
                            for item in items:
                                item_dong = get_multi_xml_text(item, ['umdNm', 'dongNm', 'sggNm'], "")
                                if "전체 (해당 구 모든 동)" in selected_dongs or any(d in item_dong for d in selected_dongs):
                                    apt_name = get_multi_xml_text(item, ['aptNm', 'offiNm', 'mhouseNm', 'bldgNm', 'rletTypeNm'], "건물명 없음")
                                    raw_p = get_multi_xml_text(item, ['dealAmount'], "0").replace(",", "")
                                    dep_p = get_multi_xml_text(item, ['deposit'], "0").replace(",", "")
                                    mon_p = get_multi_xml_text(item, ['monthlyRent'], "0").replace(",", "")
                                    
                                    umd_cd = get_multi_xml_text(item, ['umdCd', 'bjdongCd'], "")
                                    jibun = get_multi_xml_text(item, ['jibun'], "")
                                    build_year = get_multi_xml_text(item, ['buildYear'], "2000")
                                    
                                    area_exc = float(get_multi_xml_text(item, ['excluUseAr', 'plottage', 'spc'], "0.0"))
                                    py_exc = round(area_exc / 3.3058, 2) 
                                    
                                    supply_area = get_ultimate_supply_area(final_api_key, lawd_cd, umd_cd, jibun, apt_name, area_exc, prop_type, build_year, item_dong)
                                    py_sup = round(supply_area / 3.3058, 2)

                                    if int(raw_p) > 0:
                                        num_p = int(raw_p) * 10000; p_man = int(raw_p)
                                        disp_p = format_currency(num_p)
                                    else:
                                        num_p = int(dep_p) * 10000; p_man = int(dep_p)
                                        disp_p = f"보증금 {format_currency(num_p)} / 월세 {int(mon_p)*10000:,}원"
                                    
                                    p_per_py_exc = int(num_p / py_exc) if py_exc > 0 else 0
                                    p_per_py_sup = int(num_p / py_sup) if py_sup > 0 else 0
                                    
                                    all_data.append({
                                        "계약일": f"{get_multi_xml_text(item, ['dealYear'])}-{int(get_multi_xml_text(item, ['dealMonth'])):02d}-{int(get_multi_xml_text(item, ['dealDay'])):02d}", 
                                        "분류": prop_type, "법정동": item_dong, "부동산/건물명": apt_name, "층수": f"{get_multi_xml_text(item, ['floor'])}층",
                                        
                                        "전용 면적(㎡)": round(area_exc, 2), "전용 평수(평)": py_exc, 
                                        "공급 면적(㎡)": supply_area, "공급 평수(평)": py_sup,
                                        
                                        "거래금액": disp_p, "거래금액(만원)": p_man,
                                        "평당 거래가(전용)": format_currency(p_per_py_exc) if int(raw_p) > 0 else "-",
                                        "평당 거래가(공급)": format_currency(p_per_py_sup) if int(raw_p) > 0 else "-",
                                        "취소 여부": "취소됨" if get_multi_xml_text(item, ['cdealDay']) else "정상",
                                        
                                        "_raw_price": num_p, "_raw_pyeong_price": p_per_py_exc
                                    })
                    except: pass
                    
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
                            sc = alt.Chart(sc_df).mark_circle(size=60, color="#3498DB").encode(
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
                        'bg_color': '#2980B9', 
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
                
                st.download_button("📥 깔끔하게 디자인된 엑셀 다운로드", data=output.getvalue(), file_name=f"{selected_gu}_부동산데이터.xlsx", type="primary")
            else: st.warning("데이터가 존재하지 않습니다.")
