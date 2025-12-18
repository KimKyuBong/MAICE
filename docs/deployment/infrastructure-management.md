# 인프라 관리 가이드

MAICE 시스템의 인프라 서비스(nginx, redis)를 관리하는 방법을 설명합니다.

## 개요

인프라 관리 기능을 통해 배포 시 nginx나 redis를 재시작하거나 상태를 확인할 수 있습니다.

## Jenkins 파이프라인에서 사용

### 매개변수 옵션

Jenkins 파이프라인 실행 시 다음 매개변수를 설정할 수 있습니다:

#### 기본 재시작 옵션
- **RESTART_NGINX**: Nginx 컨테이너 재시작 (true/false)
- **RESTART_REDIS**: Redis 컨테이너 재시작 (true/false)

#### 고급 인프라 관리 옵션
- **INFRA_ACTION**: 인프라 관리 작업
  - `none`: 작업 없음 (기본값)
  - `restart`: 재시작
  - `start`: 시작
  - `stop`: 중지
  - `status`: 상태 확인
  - `config-check`: 설정 확인

- **INFRA_SERVICE**: 인프라 서비스 선택
  - `all`: 모든 서비스 (기본값)
  - `nginx`: Nginx만
  - `redis`: Redis만

- **SHOW_INFRA_LOGS**: 인프라 서비스 로그 확인 (true/false)

### 사용 예시

#### 1. 기본 재시작
```
RESTART_NGINX: true
RESTART_REDIS: false
```

#### 2. 고급 관리 - 모든 서비스 재시작
```
INFRA_ACTION: restart
INFRA_SERVICE: all
```

#### 3. 고급 관리 - Nginx만 상태 확인
```
INFRA_ACTION: status
INFRA_SERVICE: nginx
```

#### 4. 고급 관리 - Redis 설정 확인
```
INFRA_ACTION: config-check
INFRA_SERVICE: redis
```

#### 5. 로그 확인
```
SHOW_INFRA_LOGS: true
INFRA_SERVICE: all
```

## 직접 스크립트 사용

### 인프라 관리 스크립트

`scripts/manage_infrastructure.sh` 스크립트를 직접 사용할 수 있습니다.

#### 사용법
```bash
./scripts/manage_infrastructure.sh [옵션] [서비스]
```

#### 옵션
- `-h, --help`: 도움말 출력
- `-s, --status`: 서비스 상태 확인
- `-r, --restart`: 서비스 재시작
- `-d, --down`: 서비스 중지
- `-u, --up`: 서비스 시작
- `-l, --logs`: 서비스 로그 확인
- `-c, --config`: 설정 파일 확인/리로드

#### 서비스
- `nginx`: Nginx 웹서버
- `redis`: Redis 캐시 서버
- `all`: 모든 인프라 서비스

#### 예시

```bash
# nginx 상태 확인
./scripts/manage_infrastructure.sh -s nginx

# redis 재시작
./scripts/manage_infrastructure.sh -r redis

# 모든 서비스 시작
./scripts/manage_infrastructure.sh -u all

# nginx 중지
./scripts/manage_infrastructure.sh -d nginx

# redis 로그 확인
./scripts/manage_infrastructure.sh -l redis

# nginx 설정 확인 및 리로드
./scripts/manage_infrastructure.sh -c nginx
```

### 배포 스크립트에서 사용

Blue-Green 배포 스크립트에서도 인프라 관리 기능을 사용할 수 있습니다.

```bash
./scripts/deploy_backend_blue_green.sh backend restart nginx
./scripts/deploy_backend_blue_green.sh backend status all
./scripts/deploy_backend_blue_green.sh backend config-check redis
```

## 주의사항

1. **서비스 중지 시 주의**: 서비스를 중지하면 애플리케이션이 정상 작동하지 않을 수 있습니다.

2. **설정 확인**: `config-check` 옵션은 nginx와 redis에 대해서만 사용 가능합니다.

3. **로그 확인**: 로그 확인 시 최근 50줄이 기본으로 표시됩니다.

4. **권한**: 스크립트 실행 권한이 필요합니다 (`chmod +x`).

## 문제 해결

### 일반적인 문제

1. **스크립트 실행 권한 없음**
   ```bash
   chmod +x scripts/manage_infrastructure.sh
   ```

2. **Docker Compose 파일 없음**
   - `docker-compose.prod.yml` 파일이 현재 디렉토리에 있는지 확인

3. **컨테이너가 실행되지 않음**
   - Docker 서비스가 실행 중인지 확인
   - 필요한 이미지가 있는지 확인

### 로그 확인

문제 발생 시 다음 명령어로 로그를 확인할 수 있습니다:

```bash
# 모든 서비스 로그 확인
./scripts/manage_infrastructure.sh -l all

# 특정 서비스 로그 확인
./scripts/manage_infrastructure.sh -l nginx
./scripts/manage_infrastructure.sh -l redis
```

## 자동화

Jenkins 파이프라인에서 인프라 관리 기능을 자동화할 수 있습니다:

1. **정기적인 상태 확인**: `INFRA_ACTION: status`
2. **배포 전 서비스 재시작**: `INFRA_ACTION: restart`
3. **설정 변경 후 확인**: `INFRA_ACTION: config-check`
4. **문제 발생 시 로그 확인**: `SHOW_INFRA_LOGS: true`

이를 통해 인프라 서비스의 안정성과 가용성을 높일 수 있습니다.
