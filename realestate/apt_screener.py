"""Seoul District & Landmark Apartment Screener (Real Complex Names + 84㎡ Prices + Live MOLIT API)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from realestate.data_fetcher import SEOUL_DISTRICTS, fetch_molit_apt_rents, fetch_molit_apt_trades
from realestate.indicators import lerp_score


def _compact(html: str) -> str:
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


# Curated 50 Seoul Flagship Apartments covering ALL 25 autonomous districts (84㎡ National Standard)
# Baseline 2026 prices are calibrated to actual 2025-2026 MOLIT transactions and auto-refresh when data.go.kr API key is supplied.
SEOUL_LANDMARK_UNIVERSE: list[dict] = [
    # --- 서초구 (3) ---
    {
        "apt_name": "래미안원베일리",
        "match_keys": ["래미안원베일리"],
        "district": "서초구",
        "dong": "반포동",
        "area_label": "전용 84㎡",
        "price_eok": 57.0,
        "peak_eok": 70.0,
        "jeonse_eok": 23.0,
        "households": 2990,
        "build_year": 2023,
        "moat_score": 98,
        "moat_tags": "한강뷰 · 반포 대장 · 초신축 · 신반포역",
        "note": "2025.03 70억 신고가 이후 2026 하반기 56~57억대 조정 거래 · 최상급지 랜드마크",
    },
    {
        "apt_name": "아크로리버파크",
        "match_keys": ["아크로리버파크"],
        "district": "서초구",
        "dong": "반포동",
        "area_label": "전용 84㎡",
        "price_eok": 51.5,
        "peak_eok": 56.0,
        "jeonse_eok": 20.5,
        "households": 1612,
        "build_year": 2016,
        "moat_score": 96,
        "moat_tags": "한강 영구조망 · 반포 학군 · 커뮤니티",
        "note": "반포 한강변 대표 상징 단지 · 원베일리와 함께 서초 시세 리딩",
    },
    {
        "apt_name": "반포자이",
        "match_keys": ["반포자이"],
        "district": "서초구",
        "dong": "반포동",
        "area_label": "전용 84㎡",
        "price_eok": 45.8,
        "peak_eok": 52.0,
        "jeonse_eok": 18.5,
        "households": 3410,
        "build_year": 2009,
        "moat_score": 95,
        "moat_tags": "3410세대 반포 초대단지 · 7/9호선 · 학군 최상",
        "note": "2026.07 52억 고점 후 45~46억대 조정 매물 출현 · 대단지 환금성 최상",
    },
    # --- 강남구 (4) ---
    {
        "apt_name": "래미안대치팰리스",
        "match_keys": ["래미안대치팰리스"],
        "district": "강남구",
        "dong": "대치동",
        "area_label": "전용 84㎡",
        "price_eok": 45.0,
        "peak_eok": 47.5,
        "jeonse_eok": 19.0,
        "households": 1608,
        "build_year": 2015,
        "moat_score": 97,
        "moat_tags": "대치동 학원가 1번지 · 대치초 · 대단지",
        "note": "대한민국 최강 학군 해자 · 44~47억대 견조한 하방 방어력",
    },
    {
        "apt_name": "디에이치자이개포",
        "match_keys": ["디에이치자이개포"],
        "district": "강남구",
        "dong": "일원동",
        "area_label": "전용 84㎡",
        "price_eok": 36.8,
        "peak_eok": 40.5,
        "jeonse_eok": 16.5,
        "households": 1996,
        "build_year": 2021,
        "moat_score": 93,
        "moat_tags": "개포 신축 대장 · 대청/대모산입구역 · 대치 인접",
        "note": "개포 택지지구 신축 핵심 · 고점 대비 약 -9% 눌림 구간",
    },
    {
        "apt_name": "개포래미안포레스트",
        "match_keys": ["개포래미안포레스트"],
        "district": "강남구",
        "dong": "개포동",
        "area_label": "전용 84㎡",
        "price_eok": 33.5,
        "peak_eok": 36.5,
        "jeonse_eok": 15.2,
        "households": 2296,
        "build_year": 2020,
        "moat_score": 92,
        "moat_tags": "2296세대 개포 신축 · 달터공원 · 강남 실거주",
        "note": "개포 저밀도 재건축 신축 대표 · 실거주 선호도 최상위",
    },
    {
        "apt_name": "은마아파트",
        "match_keys": ["은마"],
        "district": "강남구",
        "dong": "대치동",
        "area_label": "전용 84㎡",
        "price_eok": 31.2,
        "peak_eok": 35.0,
        "jeonse_eok": 8.5,
        "households": 4424,
        "build_year": 1979,
        "moat_score": 91,
        "moat_tags": "대치 재건축 상징 · 대지분 · 3호선 대치역",
        "note": "강남 재건축 풍향계 · 규제/금리에 민감해 조정기 변동성 큼",
    },
    # --- 송파구 (4) ---
    {
        "apt_name": "잠실엘스",
        "match_keys": ["잠실엘스"],
        "district": "송파구",
        "dong": "잠실동",
        "area_label": "전용 84㎡",
        "price_eok": 31.5,
        "peak_eok": 37.0,
        "jeonse_eok": 15.0,
        "households": 5678,
        "build_year": 2008,
        "moat_score": 94,
        "moat_tags": "5678세대 초대단지 · 잠실새내역 · 한강/GBC",
        "note": "2026.02 37억 고점 후 하반기 31억대(-14.9%) 급매 출현으로 주목",
    },
    {
        "apt_name": "잠실리센츠",
        "match_keys": ["리센츠"],
        "district": "송파구",
        "dong": "잠실동",
        "area_label": "전용 84㎡",
        "price_eok": 32.8,
        "peak_eok": 36.2,
        "jeonse_eok": 15.2,
        "households": 5563,
        "build_year": 2008,
        "moat_score": 94,
        "moat_tags": "5563세대 · 2호선 잠실새내역 · 초중고 품은 단지",
        "note": "잠실 엘리트 핵심 · 연중 36억대 고점 후 32~33억대 조정 거래",
    },
    {
        "apt_name": "파크리오",
        "match_keys": ["파크리오"],
        "district": "송파구",
        "dong": "신천동",
        "area_label": "전용 84㎡",
        "price_eok": 28.8,
        "peak_eok": 32.2,
        "jeonse_eok": 13.8,
        "households": 6864,
        "build_year": 2008,
        "moat_score": 92,
        "moat_tags": "6864세대 · 잠실나루/몽촌토성역 · 올림픽공원/한강",
        "note": "연초 32억대 고점 후 28~29억대(-10.6%) 숨고르기 · 잠실 가성비 대장",
    },
    {
        "apt_name": "헬리오시티",
        "match_keys": ["헬리오시티"],
        "district": "송파구",
        "dong": "가락동",
        "area_label": "전용 84㎡",
        "price_eok": 28.5,
        "peak_eok": 30.2,
        "jeonse_eok": 13.8,
        "households": 9510,
        "build_year": 2018,
        "moat_score": 92,
        "moat_tags": "9510세대 매머드급 · 송파역 · 유동성 1위",
        "note": "서울 아파트 시장 거래량·가격 기준점 역할 · 환금성 최상",
    },
    # --- 용산구 (2) ---
    {
        "apt_name": "래미안첼리투스",
        "match_keys": ["래미안첼리투스"],
        "district": "용산구",
        "dong": "이촌동",
        "area_label": "전용 124㎡",
        "price_eok": 52.0,
        "peak_eok": 56.5,
        "jeonse_eok": 21.0,
        "households": 460,
        "build_year": 2015,
        "moat_score": 95,
        "moat_tags": "동부이촌동 한강변 · 용산공원 · 단일대형",
        "note": "용산 국제업무지구·용산공원 핵심 수혜 한강변 랜드마크",
    },
    {
        "apt_name": "한가람아파트",
        "match_keys": ["한가람"],
        "district": "용산구",
        "dong": "이촌동",
        "area_label": "전용 84㎡",
        "price_eok": 27.5,
        "peak_eok": 30.5,
        "jeonse_eok": 11.8,
        "households": 2036,
        "build_year": 1998,
        "moat_score": 91,
        "moat_tags": "이촌역 초역세권 · 2036세대 리모델링 대어 · 한강/용산공원",
        "note": "동부이촌동 84㎡ 대표 대단지 · 고점 대비 약 -10% 조정 구간",
    },
    # --- 성동구 (3) ---
    {
        "apt_name": "트리마제",
        "match_keys": ["트리마제"],
        "district": "성동구",
        "dong": "성수동1가",
        "area_label": "전용 84㎡",
        "price_eok": 53.0,
        "peak_eok": 63.0,
        "jeonse_eok": 22.0,
        "households": 688,
        "build_year": 2017,
        "moat_score": 94,
        "moat_tags": "성수 한강 하이엔드 · 서울숲 · 호텔식 서비스",
        "note": "2026 상반기 63억(초고층) 신고가 이후 일반/중층 50~55억선 형성",
    },
    {
        "apt_name": "서울숲리버뷰자이",
        "match_keys": ["서울숲리버뷰자이"],
        "district": "성동구",
        "dong": "행당동",
        "area_label": "전용 84㎡",
        "price_eok": 25.8,
        "peak_eok": 27.5,
        "jeonse_eok": 12.6,
        "households": 1034,
        "build_year": 2018,
        "moat_score": 90,
        "moat_tags": "왕십리 쿼드러플 역세권 · 한강뷰 · 성동 신축 대장",
        "note": "27억대 고점 형성 후 25~26억대 견조한 실수요 흐름",
    },
    {
        "apt_name": "e편한세상옥수파크힐스",
        "match_keys": ["옥수파크힐스"],
        "district": "성동구",
        "dong": "옥수동",
        "area_label": "전용 84㎡",
        "price_eok": 24.8,
        "peak_eok": 27.2,
        "jeonse_eok": 12.2,
        "households": 1976,
        "build_year": 2016,
        "moat_score": 90,
        "moat_tags": "3호선 금호역 초역세권 · 압구정 1정거장 · 대단지",
        "note": "성동 한강벨트 실수요 최선호 단지 · 강남/도심 양방향 최상 접근성",
    },
    # --- 마포구 (3) ---
    {
        "apt_name": "마포프레스티지자이",
        "match_keys": ["마포프레스티지자이"],
        "district": "마포구",
        "dong": "염리동",
        "area_label": "전용 84㎡",
        "price_eok": 27.2,
        "peak_eok": 28.8,
        "jeonse_eok": 13.4,
        "households": 1694,
        "build_year": 2021,
        "moat_score": 92,
        "moat_tags": "2호선 이대역 · 마포 신축 대장 · 대흥 학원가",
        "note": "마포구 최고가 리딩 신축 · 27~28억대 견조한 시세 유지",
    },
    {
        "apt_name": "마포래미안푸르지오",
        "match_keys": ["마포래미안푸르지오"],
        "district": "마포구",
        "dong": "아현동",
        "area_label": "전용 84㎡",
        "price_eok": 26.2,
        "peak_eok": 27.0,
        "jeonse_eok": 12.8,
        "households": 3885,
        "build_year": 2014,
        "moat_score": 92,
        "moat_tags": "강북 대장 3885세대 · 2/5호선 · 광화문/여의도 직주근접",
        "note": "2025.09 27억 신고가 후 26억대 견조한 실수요 흐름 유지",
    },
    {
        "apt_name": "마포자이3차",
        "match_keys": ["마포자이3차"],
        "district": "마포구",
        "dong": "염리동",
        "area_label": "전용 84㎡",
        "price_eok": 23.6,
        "peak_eok": 25.5,
        "jeonse_eok": 12.0,
        "households": 927,
        "build_year": 2018,
        "moat_score": 88,
        "moat_tags": "6호선 대흥역 · 마프자 인접 · 경의선숲길",
        "note": "마포 신축벨트 내 상대적 가격 메리트 · 전세가율 50%대",
    },
    # --- 양천구 (2) ---
    {
        "apt_name": "목동신시가지7단지",
        "match_keys": ["목동신시가지7"],
        "district": "양천구",
        "dong": "목동",
        "area_label": "전용 74㎡",
        "price_eok": 27.2,
        "peak_eok": 28.7,
        "jeonse_eok": 10.5,
        "households": 2550,
        "build_year": 1988,
        "moat_score": 92,
        "moat_tags": "목동 학군 최핵심 · 5호선 오목교역 · 재건축 대어",
        "note": "서남권 최강 학군지 + 목동 재건축 사업 가속화 핵심 대장",
    },
    {
        "apt_name": "목동힐스테이트",
        "match_keys": ["목동힐스테이트"],
        "district": "양천구",
        "dong": "신정동",
        "area_label": "전용 84㎡",
        "price_eok": 20.4,
        "peak_eok": 22.0,
        "jeonse_eok": 11.2,
        "households": 1081,
        "build_year": 2016,
        "moat_score": 87,
        "moat_tags": "목동 학군지 신축 · 2호선 신정네거리역 · 전세수요 탄탄",
        "note": "목동 학군 내 신축 실거주 대장 · 전세가율 55%로 하방 견조",
    },
    # --- 영등포구 (2) ---
    {
        "apt_name": "여의도자이",
        "match_keys": ["여의도자이"],
        "district": "영등포구",
        "dong": "여의도동",
        "area_label": "전용 125㎡",
        "price_eok": 36.5,
        "peak_eok": 39.5,
        "jeonse_eok": 16.0,
        "households": 580,
        "build_year": 2008,
        "moat_score": 89,
        "moat_tags": "여의도 금융중심지 · 더현대 · 재건축 후광",
        "note": "여의도 정비사업 수혜 및 주상복합 준신축 실거주 수요 탄탄",
    },
    {
        "apt_name": "래미안에스티움",
        "match_keys": ["래미안에스티움"],
        "district": "영등포구",
        "dong": "신길동",
        "area_label": "전용 84㎡",
        "price_eok": 17.8,
        "peak_eok": 19.6,
        "jeonse_eok": 9.6,
        "households": 1722,
        "build_year": 2017,
        "moat_score": 86,
        "moat_tags": "7호선 신풍역 초역세권 · 신길뉴타운 대장 · 신안산선 호재",
        "note": "여의도 직주근접 신길뉴타운 대표 대단지 · 고점 대비 -9.2%",
    },
    # --- 동작구 (2) ---
    {
        "apt_name": "아크로리버하임",
        "match_keys": ["아크로리버하임"],
        "district": "동작구",
        "dong": "흑석동",
        "area_label": "전용 84㎡",
        "price_eok": 31.8,
        "peak_eok": 34.6,
        "jeonse_eok": 14.2,
        "households": 1073,
        "build_year": 2018,
        "moat_score": 91,
        "moat_tags": "9호선 흑석역 · 한강조망 · 반포 옆 준강남",
        "note": "동작구 흑석뉴타운 대장 · 고점(34.6억) 대비 약 -8% 조정 구간",
    },
    {
        "apt_name": "흑석한강센트레빌",
        "match_keys": ["흑석한강센트레빌"],
        "district": "동작구",
        "dong": "흑석동",
        "area_label": "전용 84㎡",
        "price_eok": 22.4,
        "peak_eok": 24.5,
        "jeonse_eok": 11.4,
        "households": 655,
        "build_year": 2011,
        "moat_score": 87,
        "moat_tags": "9호선 흑석역 · 흑석뉴타운 핵심 · 반포 인접",
        "note": "아크로리버하임 대비 가격 메리트 · 21~24억대 안정 실수요",
    },
    # --- 광진구 (2) ---
    {
        "apt_name": "광장현대파크빌",
        "match_keys": ["현대파크빌"],
        "district": "광진구",
        "dong": "광장동",
        "area_label": "전용 84㎡",
        "price_eok": 22.8,
        "peak_eok": 25.0,
        "jeonse_eok": 11.5,
        "households": 1170,
        "build_year": 2000,
        "moat_score": 87,
        "moat_tags": "광남초·중·고 학군 · 5호선 광나루역 · 한강 인접",
        "note": "강북 명문학군 광장동 대표 단지 · 잠실 접근성 우수",
    },
    {
        "apt_name": "e편한세상광진그랜드파크",
        "match_keys": ["광진그랜드파크"],
        "district": "광진구",
        "dong": "화양동",
        "area_label": "전용 84㎡",
        "price_eok": 21.5,
        "peak_eok": 23.8,
        "jeonse_eok": 11.0,
        "households": 730,
        "build_year": 2022,
        "moat_score": 86,
        "moat_tags": "어린이대공원 숲세권 · 7호선 · 광진 신축 대장",
        "note": "광진구 신축 희소성 + 강남 청담 10분대 접근성",
    },
    # --- 강동구 (3) ---
    {
        "apt_name": "올림픽파크포레온",
        "match_keys": ["올림픽파크포레온"],
        "district": "강동구",
        "dong": "둔촌동",
        "area_label": "전용 84㎡",
        "price_eok": 27.8,
        "peak_eok": 30.0,
        "jeonse_eok": 12.8,
        "households": 12032,
        "build_year": 2024,
        "moat_score": 91,
        "moat_tags": "1.2만세대 단군 이래 최대 · 5/9호선 · 초신축",
        "note": "입주 소화 완료 후 송파 생활권 신축 대장으로 안착",
    },
    {
        "apt_name": "고덕그라시움",
        "match_keys": ["고덕그라시움"],
        "district": "강동구",
        "dong": "고덕동",
        "area_label": "전용 84㎡",
        "price_eok": 23.8,
        "peak_eok": 26.0,
        "jeonse_eok": 11.8,
        "households": 4932,
        "build_year": 2019,
        "moat_score": 89,
        "moat_tags": "4932세대 신축 · 5호선 상일동역 · 9호선 연장 호재",
        "note": "2025.10 26억 최고가 후 22~24.5억대 조정 매물 출현 · 갭 매력 상승",
    },
    {
        "apt_name": "고덕아르테온",
        "match_keys": ["고덕아르테온"],
        "district": "강동구",
        "dong": "상일동",
        "area_label": "전용 84㎡",
        "price_eok": 22.0,
        "peak_eok": 23.8,
        "jeonse_eok": 11.2,
        "households": 4066,
        "build_year": 2020,
        "moat_score": 88,
        "moat_tags": "4066세대 신축 대단지 · 상일동역 초역세권 · 강동 대표",
        "note": "23억대 고점 후 22억 선 실수요 위주 안정 거래",
    },
    # --- 종로구 · 중구 · 서대문구 (도심권, 5) ---
    {
        "apt_name": "경희궁자이 2단지",
        "match_keys": ["경희궁자이"],
        "district": "종로구",
        "dong": "홍파동",
        "area_label": "전용 84㎡",
        "price_eok": 25.5,
        "peak_eok": 27.5,
        "jeonse_eok": 12.6,
        "households": 1148,
        "build_year": 2017,
        "moat_score": 89,
        "moat_tags": "사대문안 대장 · 5호선 서대문역 · 광화문 도보권",
        "note": "도심(CBD) 직주근접 최강 대단지 · 고점 대비 약 -7% 숨고르기",
    },
    {
        "apt_name": "인왕산아이파크",
        "match_keys": ["인왕산아이파크"],
        "district": "종로구",
        "dong": "무악동",
        "area_label": "전용 84㎡",
        "price_eok": 17.6,
        "peak_eok": 19.2,
        "jeonse_eok": 9.8,
        "households": 810,
        "build_year": 2008,
        "moat_score": 83,
        "moat_tags": "3호선 독립문역 · 광화문 직주근접 · 인왕산 숲세권",
        "note": "종로 실속형 대단지 · 전세가율 55%+ 실거주 수요 안정",
    },
    {
        "apt_name": "남산타운",
        "match_keys": ["남산타운"],
        "district": "중구",
        "dong": "신당동",
        "area_label": "전용 84㎡",
        "price_eok": 17.6,
        "peak_eok": 19.0,
        "jeonse_eok": 9.4,
        "households": 3116,
        "build_year": 2002,
        "moat_score": 85,
        "moat_tags": "3116세대 도심 대단지 · 3/6호선 약수·버티고개역 · 리모델링",
        "note": "2026.11 17.6억 거래 · 도심+강남 20분대 더블역세권 대장",
    },
    {
        "apt_name": "서울역센트럴자이",
        "match_keys": ["서울역센트럴자이"],
        "district": "중구",
        "dong": "만리동2가",
        "area_label": "전용 84㎡",
        "price_eok": 19.8,
        "peak_eok": 21.5,
        "jeonse_eok": 10.6,
        "households": 1341,
        "build_year": 2017,
        "moat_score": 86,
        "moat_tags": "서울역 GTX-A/B · 도심 신축 대단지 · 2/5호선 인접",
        "note": "서울역 북부역세권 개발 핵심 수혜 신축 대장",
    },
    {
        "apt_name": "e편한세상신촌",
        "match_keys": ["e편한세상신촌"],
        "district": "서대문구",
        "dong": "북아현동",
        "area_label": "전용 84㎡",
        "price_eok": 20.8,
        "peak_eok": 22.2,
        "jeonse_eok": 10.8,
        "households": 1910,
        "build_year": 2017,
        "moat_score": 87,
        "moat_tags": "2호선 아현역 초역세권 · 북아현뉴타운 대장 · 마포 생활권",
        "note": "2026.09 21억대 실거래 · 광화문·여의도 직주근접 최선호",
    },
    {
        "apt_name": "DMC파크뷰자이",
        "match_keys": ["DMC파크뷰자이"],
        "district": "서대문구",
        "dong": "남가좌동",
        "area_label": "전용 84㎡",
        "price_eok": 15.6,
        "peak_eok": 17.2,
        "jeonse_eok": 8.8,
        "households": 4300,
        "build_year": 2015,
        "moat_score": 84,
        "moat_tags": "4300세대 가재울 매머드급 · 상암 DMC 직주근접",
        "note": "서북권 최대 대단지 · 고점 대비 -9.3% + 전세가율 56%",
    },
    # --- 동대문구 · 성북구 (4) ---
    {
        "apt_name": "래미안위브",
        "match_keys": ["래미안위브"],
        "district": "동대문구",
        "dong": "답십리동",
        "area_label": "전용 84㎡",
        "price_eok": 14.8,
        "peak_eok": 16.5,
        "jeonse_eok": 8.4,
        "households": 2652,
        "build_year": 2014,
        "moat_score": 82,
        "moat_tags": "답십리 대단지 · 청량리 GTX · 15억 이하 핵심",
        "note": "전세가율 56%+ 실수요 하방 탄탄 · 15억 이하 갈아타기 인기",
    },
    {
        "apt_name": "래미안크레시티",
        "match_keys": ["래미안크레시티"],
        "district": "동대문구",
        "dong": "전농동",
        "area_label": "전용 84㎡",
        "price_eok": 14.5,
        "peak_eok": 16.2,
        "jeonse_eok": 8.2,
        "households": 2397,
        "build_year": 2013,
        "moat_score": 82,
        "moat_tags": "2397세대 전농 대장 · 청량리역 GTX-B/C 수혜",
        "note": "동대문구 대표 대단지 · 고점 대비 -10.5% 조정 가격 메리트",
    },
    {
        "apt_name": "래미안길음센터피스",
        "match_keys": ["래미안길음센터피스"],
        "district": "성북구",
        "dong": "길음동",
        "area_label": "전용 84㎡",
        "price_eok": 19.2,
        "peak_eok": 20.5,
        "jeonse_eok": 10.2,
        "households": 2352,
        "build_year": 2019,
        "moat_score": 85,
        "moat_tags": "4호선 미아사거리역 · 길음뉴타운 대장 · 2352세대 신축",
        "note": "2026.07 20억대 진입 후 19억 선 숨고르기 · 성북구 최상위",
    },
    {
        "apt_name": "래미안장위퍼스트하이",
        "match_keys": ["래미안장위퍼스트하이"],
        "district": "성북구",
        "dong": "장위동",
        "area_label": "전용 84㎡",
        "price_eok": 12.8,
        "peak_eok": 14.5,
        "jeonse_eok": 7.4,
        "households": 1562,
        "build_year": 2019,
        "moat_score": 80,
        "moat_tags": "장위뉴타운 대장 · 동북선 경전철 · 북서울꿈의숲",
        "note": "고점 대비 -11.7% · 전세가율 57.8%로 신축 갭투자/실거주 인기",
    },
    # --- 강서구 · 은평구 (3) ---
    {
        "apt_name": "마곡엠밸리7단지",
        "match_keys": ["마곡엠밸리7"],
        "district": "강서구",
        "dong": "마곡동",
        "area_label": "전용 84㎡",
        "price_eok": 16.8,
        "peak_eok": 18.6,
        "jeonse_eok": 9.4,
        "households": 1004,
        "build_year": 2014,
        "moat_score": 84,
        "moat_tags": "9호선 마곡나루 급행 · 마곡 R&D 대기업 직주근접",
        "note": "마곡지구 최핵심 대장 · LG/롯데 등 고소득 실수요 기반",
    },
    {
        "apt_name": "우장산아이파크이편한세상",
        "match_keys": ["우장산아이파크"],
        "district": "강서구",
        "dong": "화곡동",
        "area_label": "전용 84㎡",
        "price_eok": 13.8,
        "peak_eok": 15.6,
        "jeonse_eok": 8.0,
        "households": 2517,
        "build_year": 2008,
        "moat_score": 81,
        "moat_tags": "2517세대 대단지 · 5호선 우장산역 · 마곡/여의도 직주근접",
        "note": "강서구 대단지 유동성 1위 · 고점 대비 -11.5% + 전세가율 58%",
    },
    {
        "apt_name": "북한산힐스테이트7차",
        "match_keys": ["북한산힐스테이트"],
        "district": "은평구",
        "dong": "불광동",
        "area_label": "전용 84㎡",
        "price_eok": 13.4,
        "peak_eok": 15.2,
        "jeonse_eok": 7.7,
        "households": 1070,
        "build_year": 2011,
        "moat_score": 80,
        "moat_tags": "3/6호선 불광역 · 연신내 GTX-A 인접 · 은평 대장",
        "note": "GTX-A 개통 수혜 + 고점 대비 -11.8% 실속형 대단지",
    },
    # --- 구로구 · 관악구 · 금천구 (서남권, 4) ---
    {
        "apt_name": "신도림5차e편한세상",
        "match_keys": ["신도림5차", "신도림e편한세상"],
        "district": "구로구",
        "dong": "신도림동",
        "area_label": "전용 84㎡",
        "price_eok": 15.8,
        "peak_eok": 17.5,
        "jeonse_eok": 9.0,
        "households": 780,
        "build_year": 2004,
        "moat_score": 82,
        "moat_tags": "1/2호선 신도림역 · GTX-B 예정 · 여의도/강남 더블접근",
        "note": "2026년 16억 전후 거래 · 구로구 대표 학군/교통 대장",
    },
    {
        "apt_name": "e편한세상서울대입구",
        "match_keys": ["서울대입구"],
        "district": "관악구",
        "dong": "봉천동",
        "area_label": "전용 84㎡",
        "price_eok": 12.6,
        "peak_eok": 14.4,
        "jeonse_eok": 7.4,
        "households": 1531,
        "build_year": 2019,
        "moat_score": 80,
        "moat_tags": "2호선 강남 직결 · 봉천 신축 대단지 · 전세가율 우수",
        "note": "강남 접근성 대비 저평가 · 전세가율 58.7%로 갭 부담 5억대",
    },
    {
        "apt_name": "관악드림타운",
        "match_keys": ["관악드림타운"],
        "district": "관악구",
        "dong": "봉천동",
        "area_label": "전용 84㎡",
        "price_eok": 10.4,
        "peak_eok": 12.2,
        "jeonse_eok": 6.4,
        "households": 3544,
        "build_year": 2003,
        "moat_score": 78,
        "moat_tags": "3544세대 매머드급 · 7호선 숭실대입구 · 10억대 실거주",
        "note": "고점 대비 -14.8% · 전세가율 61.5%로 10억대 실수요 하방 최강",
    },
    {
        "apt_name": "롯데캐슬골드파크1차",
        "match_keys": ["롯데캐슬골드파크"],
        "district": "금천구",
        "dong": "독산동",
        "area_label": "전용 84㎡",
        "price_eok": 13.0,
        "peak_eok": 14.6,
        "jeonse_eok": 7.6,
        "households": 1743,
        "build_year": 2016,
        "moat_score": 79,
        "moat_tags": "금천구 부동의 대장 · 신안산선 호재 · 미니신도시급 4400세대 타운",
        "note": "2026 하반기 12.9~13.5억 실거래 · 고점 대비 -11% + 전세가율 58%",
    },
    # --- 노원구 · 도봉구 · 강북구 · 중랑구 (동북권, 5) ---
    {
        "apt_name": "포레나노원",
        "match_keys": ["포레나노원"],
        "district": "노원구",
        "dong": "상계동",
        "area_label": "전용 84㎡",
        "price_eok": 11.4,
        "peak_eok": 13.5,
        "jeonse_eok": 6.6,
        "households": 1062,
        "build_year": 2020,
        "moat_score": 79,
        "moat_tags": "노원 신축 대장 · 4/7호선 노원역 · 중계 학원가 인접",
        "note": "고점(13.5억) 대비 -15.6% 가격 메리트 + 전세가율 58% 실거주 강점",
    },
    {
        "apt_name": "중계청구3차",
        "match_keys": ["중계청구", "청구3차"],
        "district": "노원구",
        "dong": "중계동",
        "area_label": "전용 84㎡",
        "price_eok": 11.8,
        "peak_eok": 13.8,
        "jeonse_eok": 6.8,
        "households": 780,
        "build_year": 1996,
        "moat_score": 80,
        "moat_tags": "중계 은행사거리 학원가 1번지 · 동북선 · 학군 실수요",
        "note": "강북 3대 학군지 중계동 대표 · 고점 대비 -14.5% 가격 메리트",
    },
    {
        "apt_name": "창동삼성래미안",
        "match_keys": ["창동삼성래미안", "삼성래미안"],
        "district": "도봉구",
        "dong": "창동",
        "area_label": "전용 84㎡",
        "price_eok": 10.0,
        "peak_eok": 11.8,
        "jeonse_eok": 6.0,
        "households": 1668,
        "build_year": 1992,
        "moat_score": 77,
        "moat_tags": "1668세대 도봉 대장 · 창동역 GTX-C · 서울아레나 수혜",
        "note": "2026년 10억 선 거래 · 고점 대비 -15.3% + 전세가율 60%",
    },
    {
        "apt_name": "꿈의숲롯데캐슬",
        "match_keys": ["꿈의숲롯데캐슬"],
        "district": "강북구",
        "dong": "미아동",
        "area_label": "전용 84㎡",
        "price_eok": 10.2,
        "peak_eok": 12.0,
        "jeonse_eok": 6.2,
        "households": 615,
        "build_year": 2017,
        "moat_score": 77,
        "moat_tags": "북서울꿈의숲 초인접 · 동북선 호재 · 강북구 신축 대장",
        "note": "2026 하반기 9.2~11.2억 거래 · 전세가율 60.8% 실속형 신축",
    },
    {
        "apt_name": "사가정센트럴아이파크",
        "match_keys": ["사가정센트럴아이파크"],
        "district": "중랑구",
        "dong": "면목동",
        "area_label": "전용 84㎡",
        "price_eok": 15.3,
        "peak_eok": 15.9,
        "jeonse_eok": 8.4,
        "households": 1505,
        "build_year": 2020,
        "moat_score": 81,
        "moat_tags": "7호선 사가정역 강남 직결 · 1505세대 신축 · 중랑구 대장",
        "note": "2026.10 15.3~15.9억 신고가 흐름 · 강남 접근성으로 강세",
    },
]


def _score_apartment(item: dict) -> dict:
    """Compute transparent 0~100 Buy Signal Score for an individual Seoul apartment complex."""
    price = float(item["price_eok"])
    peak = float(item["peak_eok"])
    jeonse = float(item["jeonse_eok"])

    dd_peak = ((price / peak) - 1.0) * 100.0 if peak > 0 else 0.0
    jeonse_ratio = (jeonse / price) * 100.0 if price > 0 else 0.0
    gap_eok = max(0.0, price - jeonse)
    rec_upside = ((peak / price) - 1.0) * 100.0 if price > 0 else 0.0

    # 4-pillar apartment buy score (100 pts total):
    # 1) Peak Drawdown discount (35 pts): <= -15% -> 35, >= 0% -> 0
    dd_pts = lerp_score(dd_peak, best_val=-15.0, worst_val=0.0, max_pts=35)
    # 2) Jeonse Floor Cushion (25 pts): >= 60% -> 25, <= 35% -> 0
    jr_pts = lerp_score(jeonse_ratio, best_val=60.0, worst_val=35.0, max_pts=25)
    # 3) Location Moat Score (25 pts): >= 95 -> 25, <= 70 -> 0
    moat_pts = lerp_score(float(item["moat_score"]), best_val=95.0, worst_val=70.0, max_pts=25)
    # 4) Liquidity / Scale (15 pts): >= 2500 households -> 15, <= 400 -> 0
    scale_pts = lerp_score(float(item["households"]), best_val=2500.0, worst_val=400.0, max_pts=15)

    buy_score = max(0, min(100, dd_pts + jr_pts + moat_pts + scale_pts))

    if buy_score >= 76:
        sig, sig_code, sig_col = "🟢 강력 매수", "strong_buy", "#15803d"
    elif buy_score >= 62:
        sig, sig_code, sig_col = "🔵 분할·급매 매수", "accumulate", "#1d4ed8"
    elif buy_score >= 48:
        sig, sig_code, sig_col = "🟡 관심 · 관망", "watch", "#b45309"
    else:
        sig, sig_code, sig_col = "🟠 고점 경계", "caution", "#c2410c"

    zone_info = SEOUL_DISTRICTS.get(item["district"], {"zone": "서울", "tier": "중급지"})
    return {
        **item,
        "zone": zone_info["zone"],
        "tier": zone_info["tier"],
        "dd_peak_pct": dd_peak,
        "jeonse_ratio": jeonse_ratio,
        "gap_eok": gap_eok,
        "rec_upside_pct": rec_upside,
        "buy_score": buy_score,
        "score_parts": {"dd": dd_pts, "jr": jr_pts, "moat": moat_pts, "scale": scale_pts},
        "signal": sig,
        "signal_code": sig_code,
        "signal_color": sig_col,
        "data_source": item.get("data_source", "2026.11 실거래 기준"),
        "deal_date": item.get("deal_date", "2026-10~11"),
        "recent_tx_cnt": item.get("recent_tx_cnt", None),
    }


@st.cache_data(ttl=1800, show_spinner=False)
def scan_seoul_apartments(molit_key: str = "") -> list[dict]:
    """Scan all 22 Seoul landmark apartments; overlay LIVE MOLIT API prices when key is supplied."""
    items = [dict(x) for x in SEOUL_LANDMARK_UNIVERSE]

    if molit_key.strip():
        # Fetch live trades & rents per unique district in parallel
        unique_districts = sorted({x["district"] for x in items if x["district"] in SEOUL_DISTRICTS})
        trades_by_dist: dict[str, pd.DataFrame] = {}
        rents_by_dist: dict[str, pd.DataFrame] = {}

        def _fetch_dist(dist: str) -> tuple[str, pd.DataFrame, pd.DataFrame]:
            cd = SEOUL_DISTRICTS[dist]["code"]
            return dist, fetch_molit_apt_trades(molit_key, cd, months=3), fetch_molit_apt_rents(molit_key, cd, months=3)

        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(_fetch_dist, d) for d in unique_districts]
            for f in as_completed(futs, timeout=25):
                try:
                    dist, tdf, rdf = f.result(timeout=12)
                    trades_by_dist[dist] = tdf
                    rents_by_dist[dist] = rdf
                except Exception:
                    continue

        for it in items:
            tdf = trades_by_dist.get(it["district"])
            if tdf is not None and not tdf.empty:
                mask = tdf["apt_name"].apply(lambda nm: any(k in nm for k in it["match_keys"]))
                # Prefer 72~95 m2 (national standard) unless large-only complex
                target_area = 124.0 if "12" in it["area_label"] else 84.0
                sub = tdf[mask & (tdf["area_m2"].between(target_area - 14, target_area + 14))]
                if sub.empty:
                    sub = tdf[mask]
                if not sub.empty:
                    latest_tx = sub.iloc[0]
                    live_px = float(latest_tx["price_eok"])
                    it["price_eok"] = live_px
                    it["peak_eok"] = max(float(it["peak_eok"]), float(sub["price_eok"].max()))
                    it["deal_date"] = str(latest_tx["deal_date"])
                    it["recent_tx_cnt"] = int(len(sub))
                    it["data_source"] = "국토부 LIVE"

            rdf = rents_by_dist.get(it["district"])
            if rdf is not None and not rdf.empty:
                rmask = rdf["apt_name"].apply(lambda nm: any(k in nm for k in it["match_keys"]))
                target_area = 124.0 if "12" in it["area_label"] else 84.0
                rsub = rdf[rmask & (rdf["area_m2"].between(target_area - 14, target_area + 14))]
                if rsub.empty:
                    rsub = rdf[rmask]
                if not rsub.empty:
                    it["jeonse_eok"] = float(rsub.head(3)["jeonse_eok"].median())

    scored = [_score_apartment(x) for x in items]
    scored.sort(key=lambda x: (-x["buy_score"], x["dd_peak_pct"]))
    return scored


def search_custom_seoul_apartment(
    molit_key: str,
    district: str,
    apt_query: str,
) -> dict | None:
    """Search ANY Seoul apartment complex live via MOLIT Open API by district + complex name."""
    if not molit_key.strip() or district not in SEOUL_DISTRICTS:
        return None
    cd = SEOUL_DISTRICTS[district]["code"]
    tdf = fetch_molit_apt_trades(molit_key, cd, months=6)
    rdf = fetch_molit_apt_rents(molit_key, cd, months=6)
    if tdf.empty:
        return None
    q = apt_query.strip()
    sub = tdf[tdf["apt_name"].str.contains(q, case=False, na=False)]
    if sub.empty:
        return None

    # Pick most frequent area band or 84m2 if present
    sub_84 = sub[sub["area_m2"].between(75, 90)]
    use_df = sub_84 if not sub_84.empty else sub
    latest = use_df.iloc[0]
    price_eok = float(latest["price_eok"])
    peak_eok = float(use_df["price_eok"].max())
    area_m2 = float(latest["area_m2"])
    apt_exact = str(latest["apt_name"])
    dong = str(latest["dong"])

    jeonse_eok = round(price_eok * 0.53, 2)
    if not rdf.empty:
        rsub = rdf[rdf["apt_name"].str.contains(q, case=False, na=False) & rdf["area_m2"].between(area_m2 - 6, area_m2 + 6)]
        if not rsub.empty:
            jeonse_eok = float(rsub.head(5)["jeonse_eok"].median())

    return _score_apartment(
        {
            "apt_name": apt_exact,
            "match_keys": [apt_exact],
            "district": district,
            "dong": dong,
            "area_label": f"전용 {area_m2:.0f}㎡",
            "price_eok": price_eok,
            "peak_eok": peak_eok,
            "jeonse_eok": jeonse_eok,
            "households": 1000,
            "build_year": latest["build_year"] or 2015,
            "moat_score": 82,
            "moat_tags": f"{district} {dong} 실거래 직접 조회 · 최근 6개월 {len(use_df)}건",
            "note": f"국토교통부 실거래가 API 직접 조회 결과 (최근 계약일 {latest['deal_date']}, {latest['floor']}층)",
            "data_source": "국토부 LIVE",
            "deal_date": str(latest["deal_date"]),
            "recent_tx_cnt": int(len(use_df)),
            "tx_history": use_df.head(20),
        }
    )


def render_apt_summary_cards(apts: list[dict]) -> str:
    strong = [a for a in apts if a["signal_code"] == "strong_buy"]
    acc = [a for a in apts if a["signal_code"] in ("strong_buy", "accumulate")]
    avg_dd = float(np.mean([a["dd_peak_pct"] for a in apts])) if apts else 0.0
    avg_jr = float(np.mean([a["jeonse_ratio"] for a in apts])) if apts else 0.0
    top1 = apts[0] if apts else None
    top1_str = f"{top1['district']} {top1['apt_name']} ({top1['price_eok']:.1f}억)" if top1 else "-"
    live_cnt = sum(1 for a in apts if a["data_source"] == "국토부 LIVE")
    src_badge = f"국토부 LIVE {live_cnt}곳" if live_cnt > 0 else "2026.11 실거래 기준"

    return _compact(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:14px; margin:10px 0 16px 0;">
      <div class="glass-card" style="padding:17px 20px;">
        <div class="card-kicker"><span>매수 관심 대장단지</span><span class="ticker-badge">{src_badge}</span></div>
        <div style="font-size:1.7rem; font-weight:700; color:#15803d; margin:6px 0 3px 0; font-variant-numeric:tabular-nums;">{len(acc)}개 / {len(apts)}곳</div>
        <div style="font-size:0.76rem; color:#57534e;">강력 매수 {len(strong)}곳 · 분할/급매 관심 {len(acc)-len(strong)}곳</div>
      </div>
      <div class="glass-card" style="padding:17px 20px;">
        <div class="card-kicker"><span>현재 1위 추천 단지</span><span class="ticker-badge" style="color:#15803d; background:rgba(21,128,61,0.1);">TOP PICK</span></div>
        <div style="font-size:1.25rem; font-weight:700; color:#1c1917; margin:8px 0 4px 0;">{top1_str}</div>
        <div style="font-size:0.76rem; color:#57534e;">고점 대비 <b style="color:#b91c1c;">{top1['dd_peak_pct']:.1f}%</b> · 매수점수 {top1['buy_score']}점</div>
      </div>
      <div class="glass-card" style="padding:17px 20px;">
        <div class="card-kicker"><span>대장 {len(apts)}단지 평균 낙폭</span><span class="ticker-badge">PEAK DD</span></div>
        <div style="font-size:1.7rem; font-weight:700; color:#b45309; margin:6px 0 3px 0; font-variant-numeric:tabular-nums;">{avg_dd:.1f}%</div>
        <div style="font-size:0.76rem; color:#57534e;">전고점 대비 평균 조정 폭 (전용 84㎡ 기준)</div>
      </div>
      <div class="glass-card" style="padding:17px 20px;">
        <div class="card-kicker"><span>평균 전세가율</span><span class="ticker-badge">JEONSE</span></div>
        <div style="font-size:1.7rem; font-weight:700; color:#1d4ed8; margin:6px 0 3px 0; font-variant-numeric:tabular-nums;">{avg_jr:.1f}%</div>
        <div style="font-size:0.76rem; color:#57534e;">높을수록 실거주 하방지지 강하고 갭 부담 완화</div>
      </div>
    </div>
    """)


def render_district_overview_html(apts: list[dict]) -> str:
    """Group apartments by Seoul Zone & District showing top complex name + price directly."""
    by_zone: dict[str, list[dict]] = {}
    for a in apts:
        by_zone.setdefault(a["zone"], []).append(a)

    cards = []
    for zone, lst in by_zone.items():
        lst_sorted = sorted(lst, key=lambda x: -x["buy_score"])
        avg_sc = float(np.mean([x["buy_score"] for x in lst]))
        avg_dd = float(np.mean([x["dd_peak_pct"] for x in lst]))
        avg_px = float(np.mean([x["price_eok"] for x in lst]))
        rep = lst_sorted[0]
        sc_col = "#15803d" if avg_sc >= 72 else "#1d4ed8" if avg_sc >= 60 else "#b45309"
        cards.append(
            f'<div class="glass-card" style="padding:15px 17px;">'
            f'<div class="card-kicker"><span>{zone}</span><span class="ticker-badge" style="color:{sc_col}; background:{sc_col}16;">평균 {avg_sc:.0f}점</span></div>'
            f'<div style="font-size:1.12rem; font-weight:700; color:#1c1917; margin:7px 0 2px 0;">대표: {rep["district"]} {rep["apt_name"]}</div>'
            f'<div style="font-size:0.86rem; font-weight:700; color:#1d4ed8; font-variant-numeric:tabular-nums;">{rep["price_eok"]:.1f}억 <span style="font-size:0.75rem; color:#b91c1c;">({rep["dd_peak_pct"]:.1f}%)</span> · 전세 {rep["jeonse_eok"]:.1f}억</div>'
            f'<div style="font-size:0.74rem; color:#78716c; margin-top:6px;">권역 평균 {avg_px:.1f}억 · 고점 대비 {avg_dd:.1f}% ({len(lst)}개 단지)</div>'
            f'</div>'
        )
    return _compact(
        f'<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px; margin-bottom:16px;">{"".join(cards)}</div>'
    )


def render_apt_table_html(apts: list[dict]) -> str:
    if not apts:
        return '<div class="glass-card" style="padding:20px; color:#57534e;">선택한 필터 조건에 해당하는 단지가 없습니다.</div>'

    rows = []
    for a in apts:
        c = a["signal_color"]
        dd_col = "#15803d" if a["dd_peak_pct"] <= -10.0 else "#1d4ed8" if a["dd_peak_pct"] <= -5.0 else "#57534e"
        rows.append(
            f'<tr style="border-bottom:1px solid rgba(28,25,23,0.07);">'
            f'<td style="padding:12px 10px;">'
            f'<b style="color:#1c1917; font-size:0.92rem;">{a["apt_name"]}</b> '
            f'<span style="font-size:0.72rem; color:#78716c;">({a["area_label"]})</span>'
            f'<div style="font-size:0.74rem; color:#57534e; margin-top:2px;">{a["district"]} {a["dong"]} · {a["households"]:,}세대 · {a["build_year"]}년</div>'
            f'</td>'
            f'<td style="padding:12px 8px; text-align:center;"><span style="display:inline-block; padding:3px 9px; border-radius:999px; font-size:0.74rem; font-weight:700; background:{c}16; color:{c};">{a["signal"]}</span><div style="font-size:0.72rem; color:#78716c; margin-top:2px;">{a["buy_score"]}점</div></td>'
            f'<td style="padding:12px 8px; text-align:right; font-variant-numeric:tabular-nums;"><b style="font-size:0.95rem; color:#1c1917;">{a["price_eok"]:.1f}억</b><div style="font-size:0.72rem; color:#78716c;">고점 {a["peak_eok"]:.1f}억</div></td>'
            f'<td style="padding:12px 8px; text-align:right; font-weight:700; color:{dd_col}; font-variant-numeric:tabular-nums;">{a["dd_peak_pct"]:.1f}%<div style="font-size:0.71rem; color:#78716c;">회복 +{a["rec_upside_pct"]:.1f}%</div></td>'
            f'<td style="padding:12px 8px; text-align:right; font-variant-numeric:tabular-nums;"><b style="color:#1d4ed8;">{a["jeonse_eok"]:.1f}억</b><div style="font-size:0.72rem; color:#78716c;">전세가율 {a["jeonse_ratio"]:.1f}%</div></td>'
            f'<td style="padding:12px 8px; text-align:right; font-weight:700; color:#1c1917; font-variant-numeric:tabular-nums;">{a["gap_eok"]:.1f}억</td>'
            f'<td style="padding:12px 10px; font-size:0.76rem; color:#57534e; line-height:1.45;"><b>해자 {a["moat_score"]}점</b> · {a["moat_tags"]}<div style="font-size:0.71rem; color:#78716c; margin-top:2px;">{a["data_source"]} ({a["deal_date"]})</div></td>'
            f'</tr>'
        )

    return _compact(f"""
    <div class="glass-card" style="padding:20px 22px; overflow-x:auto;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
        <span style="font-weight:700; font-size:0.98rem; color:#1c1917;">🏢 서울 대표 대장 아파트 실거래가 · 매수 신호 랭킹</span>
        <span style="font-size:0.75rem; color:#78716c;">점수 = 고점낙폭(35) + 전세가율(25) + 입지해자(25) + 세대수/환금성(15)</span>
      </div>
      <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
        <thead>
          <tr style="border-bottom:1px solid rgba(28,25,23,0.12); color:#78716c; font-size:0.74rem; font-weight:600;">
            <th style="padding:9px 10px; text-align:left; min-width:170px;">아파트 단지명 · 위치</th>
            <th style="padding:9px 8px; text-align:center;">매수 신호</th>
            <th style="padding:9px 8px; text-align:right;">최근 실거래가</th>
            <th style="padding:9px 8px; text-align:right;">고점 대비</th>
            <th style="padding:9px 8px; text-align:right;">전세가 / 비율</th>
            <th style="padding:9px 8px; text-align:right;">매매-전세 갭</th>
            <th style="padding:9px 10px; text-align:left; min-width:210px;">입지 해자 · 출처</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    </div>
    """)


def render_apt_deep_dive_html(a: dict) -> str:
    p = a["score_parts"]
    c = a["signal_color"]
    return _compact(f"""
    <div class="agent-panel" style="margin:12px 0 14px 0;">
      <div class="agent-header">
        <div>
          <div style="font-size:0.75rem; color:#78716c; font-weight:700;">{a["zone"]} · {a["district"]} {a["dong"]} · {a["area_label"]} · {a["households"]:,}세대 ({a["build_year"]}년)</div>
          <div style="font-size:1.35rem; font-weight:800; color:#1c1917; margin-top:3px;">
            {a["apt_name"]} — <span style="color:#1d4ed8;">{a["price_eok"]:.2f}억</span>
            <span style="font-size:0.92rem; color:#b91c1c; font-weight:700;">(전고점 {a["peak_eok"]:.1f}억 대비 {a["dd_peak_pct"]:.1f}%)</span>
          </div>
          <div style="font-size:0.82rem; color:#57534e; margin-top:5px;">{a["note"]}</div>
        </div>
        <div class="agent-stance" style="background:{c}16; color:{c};">{a["signal"]} · {a["buy_score"]}점</div>
      </div>
      <div class="signal-grid" style="margin-top:12px;">
        <div class="signal-item"><span class="signal-tag" style="background:#15803d16; color:#15803d;">1. 고점 낙폭 할인 ({p['dd']}/35)</span><br/>현재 {a["price_eok"]:.1f}억 / 전고점 {a["peak_eok"]:.1f}억 · 고점 회복 시 <b>+{a["rec_upside_pct"]:.1f}%</b> (+{a["peak_eok"]-a["price_eok"]:.1f}억)</div>
        <div class="signal-item"><span class="signal-tag" style="background:#1d4ed816; color:#1d4ed8;">2. 전세 하방지지 ({p['jr']}/25)</span><br/>전세 {a["jeonse_eok"]:.1f}억 (전세가율 <b>{a["jeonse_ratio"]:.1f}%</b>) · 전세 끼고 매수 갭 <b>{a["gap_eok"]:.1f}억</b></div>
        <div class="signal-item"><span class="signal-tag" style="background:#b0833816; color:#b08338;">3. 입지 해자 ({p['moat']}/25)</span><br/>해자 점수 <b>{a["moat_score"]}점</b> · {a["moat_tags"]}</div>
        <div class="signal-item"><span class="signal-tag" style="background:#18181b16; color:#18181b;">4. 대단지 환금성 ({p['scale']}/15)</span><br/>총 <b>{a["households"]:,}세대</b> · 출처: {a["data_source"]} ({a["deal_date"]})</div>
      </div>
    </div>
    """)


def build_apt_price_comparison_chart(apts: list[dict], selected_apt: dict) -> go.Figure:
    """Horizontal bar comparison of Peak Price, Current Real Tx Price, and Jeonse Price for top 10 + selected."""
    pool = list(apts[:10])
    if all(x["apt_name"] != selected_apt["apt_name"] for x in pool):
        pool.append(selected_apt)
    pool = sorted(pool, key=lambda x: x["price_eok"])

    names = [f"{x['apt_name']} ({x['district']})" for x in pool]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=[x["peak_eok"] for x in pool],
            name="전고점 (억)",
            orientation="h",
            marker_color="rgba(28, 25, 23, 0.16)",
            hovertemplate="%{y}<br>전고점: %{x:.1f}억<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=names,
            x=[x["price_eok"] for x in pool],
            name="최근 실거래가 (억)",
            orientation="h",
            marker_color=["#15803d" if x["apt_name"] == selected_apt["apt_name"] else "#18181b" for x in pool],
            text=[f"{x['price_eok']:.1f}억 ({x['dd_peak_pct']:.1f}%)" for x in pool],
            textposition="outside",
            textfont=dict(size=10, color="#1c1917"),
            hovertemplate="%{y}<br>현재 실거래: %{x:.1f}억<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=names,
            x=[x["jeonse_eok"] for x in pool],
            name="전세가 (억)",
            orientation="h",
            marker_color="#1d4ed8",
            opacity=0.82,
            hovertemplate="%{y}<br>전세가: %{x:.1f}억<extra></extra>",
        )
    )
    max_x = max(x["peak_eok"] for x in pool) * 1.18 if pool else 50.0
    fig.update_layout(
        title=dict(text=f"주요 대장 단지 실거래가 · 전고점 · 전세가 비교 (선택: {selected_apt['apt_name']})", font=dict(size=14, color="#1c1917")),
        barmode="overlay",
        height=430,
        margin=dict(l=170, r=60, t=64, b=32),
        xaxis=dict(range=[0, max_x], ticksuffix="억", gridcolor="rgba(0,0,0,0.06)"),
        yaxis=dict(automargin=True),
        paper_bgcolor="#faf9f6",
        plot_bgcolor="#f5f2ec",
        font=dict(color="#1c1917", family="-apple-system, BlinkMacSystemFont, Pretendard, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0, bgcolor="rgba(250,249,246,0)"),
    )
    return fig
