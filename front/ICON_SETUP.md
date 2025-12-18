# MAICE 아이콘 설정 가이드

## 📋 개요

MAICE 시스템의 아이콘을 등록하고 PWA로 설치 가능하게 만드는 방법입니다.

## 📁 필요한 파일

`front/static/` 디렉토리에 다음 파일들이 필요합니다:

- ✅ `favicon.svg` - 브라우저 탭 아이콘 (이미 존재)
- ⬜ `icon-192.png` - 192x192 크기 (생성 필요)
- ⬜ `icon-512.png` - 512x512 크기 (생성 필요)
- ✅ `manifest.json` - PWA 매니페스트 (이미 생성됨)

## 🛠️ 아이콘 생성 방법

### 방법 1: 온라인 도구 사용 (추천)

1. **RealFaviconGenerator** 사용 (https://realfavicongenerator.net/)
   - SVG 파일 업로드
   - 다양한 크기의 아이콘 자동 생성
   - 다운로드 후 `front/static/`에 복사

2. **PWA Builder Image Generator** 사용 (https://www.pwabuilder.com/imageGenerator)
   - SVG 파일 업로드
   - 필요한 모든 크기 자동 생성
   - 다운로드 후 적용

### 방법 2: Python 스크립트 사용

```bash
# 필수 패키지 설치
pip install cairosvg pillow

# 아이콘 생성
python scripts/generate_icons.py
```

이 스크립트는 `front/static/favicon.svg`를 기반으로 필요한 PNG 파일들을 생성합니다.

### 방법 3: 수동 생성

Illustrator, Figma 등의 디자인 툴로 아이콘을 디자인한 후:
1. 192x192 크기로 PNG 내보내기 → `icon-192.png`
2. 512x512 크기로 PNG 내보내기 → `icon-512.png`
3. `front/static/` 디렉토리에 저장

## ✅ 완료 확인

모든 파일이 준비되면:

```bash
# 프론트엔드 빌드
cd front
npm run build

# 개발 서버 실행 (확인용)
npm run dev
```

브라우저에서:
1. 개발자 도구 → Application 탭
2. Manifest 확인
3. 아이콘이 올바르게 로드되는지 확인

## 📱 PWA 설치 테스트

### 데스크톱 (Chrome)
1. 주소창 우측의 설치 버튼 클릭
2. "MAICE" 설치
3. 바탕화면 아이콘 확인

### 모바일 (iOS)
1. Safari에서 사이트 방문
2. 공유 버튼 → "홈 화면에 추가"
3. 홈 화면 아이콘 확인

### 모바일 (Android)
1. Chrome에서 사이트 방문
2. 메뉴 → "앱 설치" 또는 주소창 팝업
3. 홈 화면 아이콘 확인

## 🎨 아이콘 디자인 가이드

- **배경**: 투명 또는 브랜드 컬러 (#667eea)
- **메인 색상**: 단색(무채색) 디자인 선호
- **중앙 정렬**: 128x128 영역 안에 주요 요소 배치
- **그라데이션 지양**: 단색 색상 사용
- **가독성**: 작은 크기(16x16)에서도 명확하게 보이도록

## 📝 참고

- 아이콘은 SvelteKit 빌드 시 `static/` 폴더에서 자동으로 복사됩니다.
- `manifest.json`이 이미 생성되어 있어 아이콘 파일만 추가하면 됩니다.
- SVG 형식은 확장성이 좋지만, PNG 형식이 더 광범위하게 지원됩니다.

