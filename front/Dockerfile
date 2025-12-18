# 프론트엔드 빌드 전용 Dockerfile
FROM node:22-alpine AS builder

WORKDIR /app

# 의존성 파일 복사 및 설치
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

# 소스 코드 복사 및 빌드
COPY . .
RUN yarn build

# 빌드 결과물만 포함하는 최종 이미지
FROM alpine:latest

# 빌드된 정적 파일을 /build 디렉토리에 복사
COPY --from=builder /app/build /build

# 빌드 결과물 확인용 명령어
CMD ["ls", "-la", "/build"]
