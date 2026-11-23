# 🚀 무료 24시간 웹 배포 & 매일 아침 자동 리포트 설정 가이드

맥북이 완전히 꺼져 있어도 **폰·PC에서 24시간 실시간 대시보드**를 보고, **매일 아침 7:30(한국시간)**에 텔레그램/이메일 리포트를 자동으로 받는 방법입니다. (전 과정 100% 무료 · 소요 시간 약 5분)

---

## 1단계: GitHub에 코드 올리기 (드래그 앤 드롭 1분 컷)

1. [GitHub](https://github.com/) 로그인 (계정이 없다면 무료 가입)
2. 오른쪽 상단 **`+` → `New repository`** 클릭
3. Repository name에 `stock-agent` 입력 → **`Public`** 선택 → **`Create repository`** 클릭
4. 생성된 빈 저장소 화면에서 **`uploading an existing file`** 링크 클릭
5. Finder에서 `/Users/lauren/.gemini/antigravity/scratch/stock-agent/deploy-bundle` 폴더 안의 파일들을 **전체 선택해 그대로 드래그 앤 드롭**
   - *(주의: `.github` 폴더도 포함해서 올려야 자동 알림이 동작합니다! Finder에서 `Cmd + Shift + .` 을 누르면 숨김 폴더 `.github`가 보입니다.)*
6. 아래 초록색 **`Commit changes`** 버튼 클릭!

---

## 2단계: 24시간 무료 웹 대시보드 연결 (Streamlit Community Cloud)

1. [Streamlit Community Cloud](https://share.streamlit.io/) 접속 → **`Continue with GitHub`** 로 로그인
2. **`Create app`** → **`Deploy a public app from GitHub`** 클릭
3. 아래와 같이 선택:
   - **Repository:** `내아이디/stock-agent`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. **`Deploy!`** 클릭 → 약 1~2분 후 무료 영구 주소(예: `https://내아이디-stock-agent.streamlit.app`)가 생성됩니다!
5. 폰 사파리/크롬에서 이 주소를 열어 **홈 화면에 추가**하면 앱처럼 24시간 언제든 바로 볼 수 있습니다.

---

## 3단계: 매일 아침 7:30 자동 리포트 켜기 (텔레그램 또는 이메일)

GitHub 저장소 상단 **`Settings` → 왼쪽 `Secrets and variables` → `Actions` → `New repository secret`** 에서 원하는 채널의 키를 등록하세요.

### 📱 방법 A: 텔레그램으로 받기 (가장 추천 · 1분 컷)
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` 입력 → 봇 이름 정하면 **`BOT TOKEN`** 발급
2. 새로 만든 내 봇에게 아무 메시지나 한 번 전송(예: `안녕`)
3. 브라우저에서 `https://api.telegram.org/bot여기에토큰붙여넣기/getUpdates` 접속 → `"chat":{"id": 123456789}` 숫자 복사 (이게 **`CHAT ID`**)
4. GitHub Secrets에 아래 3개 추가:
   - `TELEGRAM_BOT_TOKEN` = 발급받은 봇 토큰
   - `TELEGRAM_CHAT_ID` = 복사한 숫자 ID
   - `DASHBOARD_URL` = 2단계에서 만든 내 Streamlit 주소 *(선택)*

### 📧 방법 B: Gmail 이메일로 받기
1. [Google 계정 보안](https://myaccount.google.com/security)에서 2단계 인증 활성화 → **`앱 비밀번호`** 생성 (16자리)
2. GitHub Secrets에 아래 4개 추가:
   - `EMAIL_SENDER` = 내 Gmail 주소 (예: `myemail@gmail.com`)
   - `EMAIL_PASSWORD` = 방금 생성한 16자리 앱 비밀번호
   - `EMAIL_RECEIVER` = 받을 이메일 주소 (내 Gmail과 같아도 됨)
   - `DASHBOARD_URL` = 2단계에서 만든 내 Streamlit 주소 *(선택)*

*(텔레그램과 이메일 둘 다 등록하면 두 곳으로 동시에 발송됩니다!)*

### ✅ 즉시 테스트해 보기
GitHub 저장소 상단 **`Actions` 탭 → `Daily US Market Morning Report` → `Run workflow`** 버튼을 누르면 30초 안에 바로 테스트 알림이 도착합니다!
