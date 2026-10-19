# 프라하 가족여행 가이드 앱

여행일지(정적 페이지) + 로그인 + 장소공유(리뷰/평점/즐겨찾기) + 이메일 문의 + 교통정보를 갖춘
파이썬 웹앱입니다.

## 기술 스택

- **웹 프레임워크**: [Starlette](https://www.starlette.io/) (FastAPI의 기반이 되는 ASGI 프레임워크) + Jinja2 템플릿
- **DB**: 로컬은 SQLite(파이썬 표준 `sqlite3`), 배포는 `DATABASE_URL`을 넣으면 PostgreSQL(Neon 무료)
- **사진 저장**: 로컬은 `app/static/uploads/places/`, 배포는 `CLOUDINARY_URL`을 넣으면 Cloudinary(무료)
- **인증**: PBKDF2 비밀번호 해시(표준 라이브러리) + 서명된 쿠키 세션(`itsdangerous`)
- **서버**: `uvicorn`

## 로컬 실행

```bash
cd prague-app
python3 -m venv venv && source venv/bin/activate   # 선택 사항
pip install -r requirements.txt
cp .env.example .env   # 값 채우기 (SMTP 등)
uvicorn app.main:app --reload --reload-dir app --env-file .env --port 8000
```

브라우저에서 http://localhost:8000 접속.

## 기능

| 기능 | 경로 |
|---|---|
| 여행일지 | `/journal` (`app/journal_data.py` 데이터 + `templates/journal.html`, 사진·영상은 `static/journal/media/`) |
| 회원가입 / 로그인 | `/register`, `/login` |
| 장소공유 목록 / 등록 / 상세 | `/places`, `/places/new`, `/places/{id}` |
| 리뷰/평점 | 장소 상세 페이지 내 |
| 즐겨찾기 | 장소 상세 페이지 버튼, 목록은 `/favorites` |
| 문의하기(이메일) | `/inquiry` |
| 교통정보 | `/transit` |

## 이메일 발송 설정

`.env`의 `SMTP_*` 값을 채우면 `/inquiry` 폼 제출 시 실제 이메일이 발송됩니다.
설정하지 않으면 문의는 DB에는 저장되지만 이메일은 발송되지 않습니다 (에러 없이 안내 메시지만 다르게 표시).

Gmail 사용 시:
1. 구글 계정 2단계 인증 활성화
2. "앱 비밀번호" 생성 (일반 로그인 비밀번호 아님)
3. `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=본인이메일`, `SMTP_PASSWORD=앱비밀번호`

## 배포

**추천: Render.com 또는 Railway** (무료 티어 있음)

### Render Blueprint로 배포 (가장 간단)

저장소 루트의 `render.yaml`에 서비스 설정이 들어 있습니다.

1. https://render.com 에 GitHub 계정으로 로그인
2. 대시보드에서 **New > Blueprint** → `pers1052-lab/prague` 저장소 선택
3. `SMTP_USER`, `SMTP_PASSWORD` 값 입력 (나머지는 자동 설정, `APP_SECRET_KEY`는 자동 생성)
4. **Apply** → 빌드가 끝나면 `https://prague-guide.onrender.com` 같은 주소가 생깁니다

`main` 브랜치에 푸시할 때마다 자동으로 다시 배포됩니다.
무료 플랜은 15분간 접속이 없으면 잠들고, 다음 접속 때 깨어나는 데 30초~1분 정도 걸립니다.

### 데이터가 사라지지 않게 하기 (무료 DB + 무료 사진 저장소)

Render 무료 플랜은 서버가 잠들거나 재배포될 때 디스크가 초기화됩니다. 그래서 장소, 리뷰, 회원 정보와
업로드 사진은 외부 무료 서비스에 저장해야 합니다. 두 환경변수가 없으면 예전처럼 서버 디스크에 저장됩니다.

**1. Neon (PostgreSQL DB)**
1. https://neon.tech 에 GitHub 계정으로 가입 → 프로젝트 생성 (Region은 `AWS Europe (Frankfurt)` 추천)
2. 대시보드의 **Connect** 버튼 → 연결 문자열 복사
   (`postgresql://...neon.tech/neondb?sslmode=require` 형태)
3. Render 서비스 → **Environment** → `DATABASE_URL`에 붙여넣기

**2. Cloudinary (사진)**
1. https://cloudinary.com 무료 가입
2. 대시보드(Settings > API Keys)의 **API environment variable** 복사
   (`cloudinary://<api_key>:<api_secret>@<cloud_name>` 형태)
3. Render 서비스 → **Environment** → `CLOUDINARY_URL`에 붙여넣기

저장하면 Render가 다시 배포합니다. 테이블은 서버가 처음 켜질 때 자동으로 만들어집니다.

### 수동 설정

1. 이 프로젝트를 GitHub 저장소로 푸시
2. Render/Railway에서 "New Web Service" → 저장소 연결
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. 환경변수(`APP_SECRET_KEY`, `DATABASE_URL`, `CLOUDINARY_URL`, `SMTP_*`)를 대시보드에 등록

## 참고 / 다음 단계로 고려할 것

- `/journal`은 기존에 base64로 사진·영상을 통째로 임베딩해 만든 단일 HTML(약 70MB)을 그대로 서빙합니다.
  당장 동작에는 문제가 없지만, 사진 수가 더 늘어나거나 관리자 화면에서 캡션을 직접 수정하고 싶다면
  사진을 개별 파일 + DB 레코드(Photo 테이블)로 옮기는 리팩터링을 추천합니다.
- Neon 무료 DB는 5분간 사용이 없으면 잠들어서, 오랜만의 첫 요청은 1초 안팎 더 걸릴 수 있습니다.
