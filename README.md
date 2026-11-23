# US Market Stock Agent (Streamlit + HTML/CSS)

무료 실시간 미국 증시 데이터를 별도 유료 API 키 없이 연결한 주식 에이전트 웹 대시보드입니다.

## 주요 기능
1. **S&P 500 (`^GSPC`)**: 실시간 시세, 전일 대비 등락, **고점 대비 낙폭(ATH & 52주 고점)**, 고점 회복 필요 수익률, Drawdown 차트
2. **NASDAQ (`^IXIC` / `^NDX` 전환)**: 실시간 시세, 고점 대비 낙폭, **RSI(14)** & **MFI(14, 거래량 가중 자금흐름)** 게이지 및 3단 인터랙티브 차트
3. **CNN 공포·탐욕 지수 (Fear & Greed Index)**: 커스텀 SVG 다이얼 게이지, 전일/1주/1개월/1년 비교, 1년 히스토리 추이 차트
4. **주식 에이전트 실시간 진단**: RSI, MFI, 고점 대비 낙폭, 공포·탐욕 지수, VIX를 종합한 정량 브리핑 + 선택적 무료 Gemini API Q&A

## 실행 방법
```bash
cd /Users/lauren/.gemini/antigravity/scratch/stock-agent
./run.sh
```
또는 Finder에서 `StockAgent.command`를 더블 클릭하면 바로 브라우저(`http://localhost:8501`)가 열립니다.

## 어디서나 24시간 접속하고 싶다면? (무료 호스팅)
이 폴더를 GitHub 저장소에 올린 뒤 [Streamlit Community Cloud](https://share.streamlit.io/)에 연결하면 `requirements.txt`와 `app.py`만으로 모바일·PC 어디서나 무료로 상시 접속할 수 있습니다.
