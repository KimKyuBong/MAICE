pipeline {
    agent {
        label 'build-agent'  // 기본 에이전트: build-agent (빌드 작업용)
    }

    environment {
        // 기본 설정
        PROJECT_NAME = 'maice'
        BUILD_NUMBER = "${env.BUILD_NUMBER}"
        // GIT_COMMIT_SHORT는 각 단계에서 설정

        // 이미지 이름
        BACKEND_IMAGE = "${PROJECT_NAME}-back"
        AGENT_IMAGE = "${PROJECT_NAME}-agent"

        // 배포 환경
        DEPLOY_ENV = "${params.DEPLOY_ENV ?: 'development'}"

        // 데이터베이스 설정 (외부 DB 사용)
        // DB_HOST는 withCredentials에서 설정됨
        DB_PORT = "5432"
        DB_USER = "postgres"
        DB_PASSWORD = "postgres"
        // DATABASE_URL과 AGENT_DATABASE_URL은 withCredentials에서 설정됨

        // 빌드 관련 환경 변수
        OPENAI_CHAT_MODEL = "gpt-5-mini"
        ORCHESTRATOR_MODE = "decentralized"
        FORCE_NON_STREAMING = "1"
        AUTO_PROMOTE_AFTER_CLARIFICATION = "0"
        OPENAI_EMBED_MODEL = "text-embedding-3-small"
        REDIS_URL = "redis://redis:6379"

        // Registry 설정 (실제 값은 withCredentials에서 설정)
        // REGISTRY_HOST와 REGISTRY_PORT는 withCredentials에서 설정됨

        // 서버 정보
        KB_WEB_HOST = 'kb-web'
        KB_WEB_USER = 'hwansi'
        KB_WEB_PATH = '/home/hwansi/server/maicesystem'
    }

    parameters {
        choice(
            name: 'DEPLOY_ENV',
            choices: ['development', 'staging', 'production'],
            description: '배포 환경 선택'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: '테스트 건너뛰기'
        )
        booleanParam(
            name: 'FORCE_REBUILD',
            defaultValue: false,
            description: '강제 재빌드 (캐시 무시)'
        )
        booleanParam(
            name: 'RESTART_NGINX',
            defaultValue: false,
            description: 'Nginx 컨테이너 재시작'
        )
        booleanParam(
            name: 'RESTART_REDIS',
            defaultValue: false,
            description: 'Redis 컨테이너 재시작'
        )
        choice(
            name: 'INFRA_ACTION',
            choices: ['none', 'restart', 'start', 'stop', 'status', 'config-check'],
            description: '인프라 관리 작업 (none: 작업 없음, restart: 재시작, start: 시작, stop: 중지, status: 상태확인, config-check: 설정확인)'
        )
        choice(
            name: 'INFRA_SERVICE',
            choices: ['all', 'nginx', 'redis'],
            description: '인프라 서비스 선택 (all: 모든 서비스, nginx: Nginx만, redis: Redis만)'
        )
        booleanParam(
            name: 'SHOW_INFRA_LOGS',
            defaultValue: false,
            description: '인프라 서비스 로그 확인'
        )
        // 환경변수는 Jenkins Credentials를 통해 관리됩니다.
        // DB_HOST, REGISTRY_HOST, REGISTRY_PORT는 Credentials에서 설정하세요.
    }

    stages {
        stage('Build All') {
            steps {
                echo "🚀 전체 빌드 및 배포 시작..."

                script {
                    // Git 상태 확인 (SCM에서 자동 체크아웃된 상태)
                    sh """
                        echo "현재 Git 상태:"
                        git status --short
                        echo "현재 브랜치: \$(git rev-parse --abbrev-ref HEAD)"
                        echo "현재 커밋: \$(git rev-parse --short HEAD)"
                        echo "최근 커밋 로그:"
                        git log --oneline -3
                    """

                    env.GIT_COMMIT = sh(script: "git rev-parse HEAD", returnStdout: true).trim()
                    env.GIT_COMMIT_SHORT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.GIT_BRANCH = sh(script: "git rev-parse --abbrev-ref HEAD", returnStdout: true).trim()
                    env.GIT_AUTHOR = sh(script: "git log -1 --pretty=format:'%an'", returnStdout: true).trim()

                    echo "📋 빌드 정보:"
                    echo "  - 브랜치: ${env.GIT_BRANCH}"
                    echo "  - 커밋: ${env.GIT_COMMIT_SHORT}"
                    echo "  - 작성자: ${env.GIT_AUTHOR}"
                    echo "  - 배포 환경: ${env.DEPLOY_ENV}"
                    
                    // 변경된 파일 확인하여 빌드 필요 여부 판단
                    echo "🔍 변경된 파일 분석 중..."
                    
                    def changedFiles = ""
                    try {
                        // 최근 10개 커밋까지 확인하여 누락된 변경사항 없이 감지
                        changedFiles = sh(script: "git diff --name-only HEAD~10 HEAD 2>/dev/null || echo ''", returnStdout: true).trim()
                        
                        if (changedFiles.isEmpty()) {
                            echo "⚠️ HEAD~10 비교로 변경사항 없음, HEAD~1로 재확인"
                            changedFiles = sh(script: "git diff --name-only HEAD~1 HEAD 2>/dev/null || echo ''", returnStdout: true).trim()
                        }
                        
                        // 마지막 확인: 마지막 빌드 이후부터
                        if (changedFiles.isEmpty()) {
                            echo "⚠️ HEAD~1로도 변경사항 없음, 최근 20개 커밋까지 확인"
                            changedFiles = sh(script: "git diff --name-only HEAD~20 HEAD 2>/dev/null || echo ''", returnStdout: true).trim()
                        }
                        
                    } catch (Exception e) {
                        echo "⚠️ 변경 파일 확인 실패, 전체 빌드 진행"
                        changedFiles = "front/ back/ agent/"
                    }
                    
                    echo "변경된 파일 목록:"
                    echo changedFiles
                    
                    // 강제 재빌드 옵션이 켜져있으면 모두 빌드
                    if (params.FORCE_REBUILD) {
                        env.BUILD_FRONTEND = 'true'
                        env.BUILD_BACKEND = 'true'
                        env.BUILD_AGENT = 'true'
                        echo "🔨 강제 재빌드: 모든 서비스 빌드"
                    } else {
                        // 변경 파일 기반 빌드 필요 여부 판단
                        // front/, nginx/, docker-compose.yml 등으로 확장
                        env.BUILD_FRONTEND = (changedFiles.contains('front/') || 
                                             changedFiles.contains('nginx/') ||
                                             changedFiles.contains('docker-compose.yml') ||
                                             changedFiles.contains('docker-compose.prod.yml') ||
                                             changedFiles.contains('.build-trigger')) ? 'true' : 'false'
                        env.BUILD_BACKEND = (changedFiles.contains('back/') || 
                                           changedFiles.contains('docker-compose.yml') ||
                                           changedFiles.contains('docker-compose.prod.yml')) ? 'true' : 'false'
                        env.BUILD_AGENT = (changedFiles.contains('agent/') || 
                                         changedFiles.contains('docker-compose.yml') ||
                                         changedFiles.contains('docker-compose.prod.yml')) ? 'true' : 'false'
                        
                        echo "📊 빌드 필요 여부:"
                        echo "  - 프론트엔드: ${env.BUILD_FRONTEND}"
                        echo "  - 백엔드: ${env.BUILD_BACKEND}"
                        echo "  - 에이전트: ${env.BUILD_AGENT}"
                    }
                }
            }
        }

        stage('Parallel Build & Deploy Setup') {
            parallel {
                stage('Database Setup') {
                    steps {
                        echo "🗄️ 데이터베이스 설정 및 마이그레이션 실행..."

                        script {
                            try {
                                withCredentials([string(credentialsId: 'DB_HOST', variable: 'DB_HOST')]) {
                                    env.DB_HOST = DB_HOST
                                    env.DATABASE_URL = "postgresql://postgres:postgres@" +
                                                       "${DB_HOST}:5432/maice_web"
                                    env.AGENT_DATABASE_URL = "postgresql://postgres:postgres@" +
                                                             "${DB_HOST}:5432/maice_agent"

                                    echo "✅ DB_HOST 크레덴셜에서 가져옴: ${DB_HOST}"
                                    echo "✅ DATABASE_URL 설정: " + env.DATABASE_URL
                                    echo "✅ AGENT_DATABASE_URL 설정: " + env.AGENT_DATABASE_URL
                                }
                            } catch (Exception e) {
                                echo "❌ DB_HOST 크레덴셜을 찾을 수 없습니다: ${e.getMessage()}"
                                echo "⚠️ 기본값 localhost 사용"
                                env.DB_HOST = "localhost"
                                env.DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/maice_web"
                                env.AGENT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/maice_agent"
                            }
                        }

                        // PostgreSQL 클라이언트 설치 (충돌 방지)
                        sh """
                            echo "📦 PostgreSQL 클라이언트 설치 중..."

                            # 이미 설치되어 있는지 확인
                            if command -v psql >/dev/null 2>&1; then
                                echo "✅ psql이 이미 설치되어 있습니다"
                                psql --version
                            else
                                echo "psql이 설치되지 않음, 설치 진행..."

                                # apt 잠금 파일 정리
                                sudo rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* 2>/dev/null || true

                                # PostgreSQL 클라이언트 설치 (단순화)
                                sudo apt-get update -qq && sudo apt-get install -y postgresql-client || {
                                    echo "❌ PostgreSQL 클라이언트 설치 실패"
                                    echo "대안: Docker를 사용한 PostgreSQL 클라이언트 실행"
                                    exit 1
                                }

                                # 설치 확인
                                if command -v psql >/dev/null 2>&1; then
                                    echo "✅ psql 설치 완료"
                                    psql --version
                                else
                                    echo "❌ psql 설치 후에도 명령어를 찾을 수 없음"
                                    exit 1
                                fi
                            fi
                        """

                        sh """
                            chmod +x scripts/database_setup.sh
                            export DB_HOST="${env.DB_HOST}"
                            export DATABASE_URL="${env.DATABASE_URL}"
                            export AGENT_DATABASE_URL="${env.AGENT_DATABASE_URL}"
                            ./scripts/database_setup.sh
                        """
                    }
                }


                stage('Build & Archive Frontend') {
                    steps {
                        echo "🎨 프론트엔드 빌드 및 아티팩트 아카이브..."

                        script {
                            if (env.BUILD_FRONTEND == 'true') {
                                withCredentials([
                                string(credentialsId: 'GOOGLE_CLIENT_ID', variable: 'GOOGLE_CLIENT_ID'),
                                string(credentialsId: 'GOOGLE_REDIRECT_URI', variable: 'GOOGLE_REDIRECT_URI')
                            ]) {
                                sh """
                                    chmod +x scripts/build_frontend.sh
                                    ./scripts/build_frontend.sh
                                """

                                // 프론트엔드 빌드 결과 확인 및 아티팩트 저장
                                sh """
                                    echo "🔍 프론트엔드 빌드 결과 확인..."
                                    ls -la front/
                                    if [ -d "front/build" ]; then
                                        echo "✅ front/build 디렉토리 존재"
                                        ls -la front/build/

                                        # 빌드 결과 파일 개수 확인
                                        BUILD_FILES=\$(find front/build -type f | wc -l)
                                        echo "빌드 파일 개수: \$BUILD_FILES"

                                        if [ \$BUILD_FILES -gt 0 ]; then
                                            echo "FRONTEND_BUILD_SUCCESS=true" > frontend-build-status.txt
                                            echo "✅ 실제 빌드 결과가 있습니다"
                                        else
                                            echo "FRONTEND_BUILD_SUCCESS=false" > frontend-build-status.txt
                                            echo "⚠️ 빌드 디렉토리는 있지만 파일이 없습니다"
                                        fi
                                    else
                                        echo "FRONTEND_BUILD_SUCCESS=false" > frontend-build-status.txt
                                        echo "❌ front/build 디렉토리가 존재하지 않음"
                                        echo "front 디렉토리 내용:"
                                        ls -la front/
                                    fi
                                """

                                // 빌드 상태를 환경변수로 설정
                                def buildStatus = readFile('frontend-build-status.txt').trim()
                                if (buildStatus.contains('FRONTEND_BUILD_SUCCESS=true')) {
                                    env.FRONTEND_BUILD_SUCCESS = 'true'
                                    echo "✅ 프론트엔드 빌드 성공 - 아티팩트로 아카이브"

                                    // 빌드 결과를 Archive Artifacts로 저장 (다른 에이전트에서 접근 가능)
                                    archiveArtifacts artifacts: 'front/build/**', fingerprint: true
                                    echo "✅ 프론트엔드 빌드 결과가 아티팩트로 아카이브되었습니다"

                                } else {
                                    env.FRONTEND_BUILD_SUCCESS = 'false'
                                    echo "⚠️ 프론트엔드 빌드 실패 - 배포 건너뛰기"
                                }

                                // 빌드 상태 정보는 항상 아카이브
                                archiveArtifacts artifacts: 'frontend-build-status.txt', fingerprint: true
                                echo "✅ 프론트엔드 빌드 상태 정보가 아카이브되었습니다"

                                // 다른 에이전트로 전달을 위한 stash 저장
                                if (env.FRONTEND_BUILD_SUCCESS == 'true') {
                                    // 빌드 결과 검증 후 stash 저장
                                    sh """
                                        echo "🔍 stash 저장 전 빌드 결과 재검증..."
                                        BUILD_FILE_COUNT=\$(find front/build -type f | wc -l)
                                        if [ -d "front/build" ] && [ \$BUILD_FILE_COUNT -gt 0 ]; then
                                            echo "✅ 실제 빌드 파일이 존재합니다"
                                            echo "빌드 파일 개수: \$BUILD_FILE_COUNT"
                                            echo "빌드 디렉토리 크기: \$(du -sh front/build)"
                                        else
                                            echo "❌ 빌드 파일이 없거나 빈 디렉토리입니다"
                                            exit 1
                                        fi
                                        # 빌드 결과 크기 확인
                                        BUILD_SIZE=\$(du -sh front/build | cut -f1)
                                        echo "빌드 결과 크기: \$BUILD_SIZE"
                                    """
                                    
                                    // 배포 패키지 방식으로 단일 파일로 압축하여 stash
                                    sh """
                                        # 프론트엔드 빌드 결과를 tar.gz로 압축
                                        tar -czf frontend-build-${BUILD_NUMBER}.tar.gz -C front build
                                        echo "✅ 프론트엔드 빌드 결과 압축 완료"
                                        ls -la frontend-build-${BUILD_NUMBER}.tar.gz
                                    """
                                    
                                    // 단일 파일로 stash 저장 (환경변수 사용)
                                    def frontendTarFile = "frontend-build-${BUILD_NUMBER}.tar.gz"
                                    stash name: "frontend-build-${BUILD_NUMBER}", includes: "${frontendTarFile}"
                                    echo "✅ 프론트엔드 빌드 결과가 stash에 저장되었습니다"
                                } else {
                                    // 빌드 실패 시에도 빈 stash 생성하여 unstash 에러 방지
                                    sh 'mkdir -p empty-frontend-build'
                                    stash name: "frontend-build-${BUILD_NUMBER}", 
                                          includes: 'empty-frontend-build', 
                                          allowEmpty: true
                                    echo "⚠️ 프론트엔드 빌드 실패 - 빈 stash 생성"
                                }
                                
                                // 빌드 상태 파일도 stash로 저장
                                stash name: "frontend-status-${BUILD_NUMBER}", includes: 'frontend-build-status.txt'
                                echo "✅ 프론트엔드 빌드 상태가 stash에 저장되었습니다"
                                }
                            } else {
                                // 프론트엔드 빌드 건너뜀 - 빈 stash 생성
                                echo "⏭️  프론트엔드 빌드 건너뜀 - 변경사항 없음"
                                sh 'mkdir -p empty-frontend-build && echo "FRONTEND_BUILD_SUCCESS=false" > frontend-build-status.txt'
                                stash name: "frontend-build-${BUILD_NUMBER}", 
                                      includes: 'empty-frontend-build', 
                                      allowEmpty: true
                                stash name: "frontend-status-${BUILD_NUMBER}", includes: 'frontend-build-status.txt'
                                echo "✅ 빈 stash 생성 완료"
                            }
                        }
                    }
                }

                stage('Create Deploy Package') {
                    steps {
                        echo "📦 배포 패키지 생성 및 아티팩트 저장..."

                        script {
                            // 배포에 필요한 모든 파일을 하나의 패키지로 생성
                            sh """
                                echo "배포 패키지 생성 중..."

                                # 배포 패키지 디렉토리 생성
                                rm -rf deploy-package
                                mkdir -p deploy-package/scripts

                                # 스크립트 파일들 복사
                                cp scripts/deploy_backend_agent.sh deploy-package/scripts/
                                cp scripts/deploy_backend.sh deploy-package/scripts/
                                cp scripts/deploy_backend_blue_green.sh deploy-package/scripts/
                                cp scripts/rollback_backend.sh deploy-package/scripts/
                                cp scripts/rollback_backend_blue_green.sh deploy-package/scripts/
                                cp scripts/monitor_deployment.sh deploy-package/scripts/
                                cp scripts/traffic_control.sh deploy-package/scripts/
                                cp scripts/deploy_frontend.sh deploy-package/scripts/
                                cp scripts/validate_environment.sh deploy-package/scripts/
                                cp scripts/manage_infrastructure.sh deploy-package/scripts/
                                
                                # Docker Compose 파일들 복사
                                cp docker-compose.prod.yml deploy-package/
                                
                                # Nginx 설정 파일들 복사
                                mkdir -p deploy-package/nginx/conf.d
                                cp nginx/conf.d/maice-prod.conf deploy-package/nginx/conf.d/
                                cp nginx/nginx.conf deploy-package/nginx/ 2>/dev/null || echo "nginx.conf 없음 - 기본 설정 사용"
                                echo "✅ Nginx 설정 파일 복사 완료"
                                
                                # 프론트엔드 빌드 결과는 stash로만 전달하므로 배포 패키지에는 포함하지 않음
                                echo "ℹ️ 프론트엔드 빌드 결과는 별도 stash로 전달됩니다"
                                mkdir -p deploy-package/build
                                echo "빈 build 디렉토리 생성 완료"

                                # 실행 권한 부여
                                chmod +x deploy-package/scripts/*.sh

                                # 패키지 내용 확인
                                echo "배포 패키지 내용:"
                                find deploy-package -type f -exec ls -la {} \\;

                                # tar.gz로 압축
                                tar -czf deploy-package.tar.gz deploy-package/

                                echo "배포 패키지 생성 완료:"
                                ls -la deploy-package.tar.gz
                            """
                        }

                        // 배포 패키지를 아티팩트로 저장
                        archiveArtifacts artifacts: 'deploy-package.tar.gz', fingerprint: true
                        echo "✅ 배포 패키지가 아티팩트로 저장되었습니다"

                        // 다른 에이전트로 전달을 위한 stash 저장
                        stash name: "deploy-package-${BUILD_NUMBER}", includes: 'deploy-package.tar.gz'
                        echo "✅ 배포 패키지가 stash에 저장되었습니다"
                    }
                }

                stage('Build & Push Backend') {
                    steps {
                        echo "🏗️ 백엔드 Docker 이미지 빌드 및 Registry 푸시..."

                        script {
                            if (env.BUILD_BACKEND == 'true') {
                            withCredentials([
                                string(credentialsId: 'DB_HOST', variable: 'DB_HOST'),
                                string(credentialsId: 'REGISTRY_HOST', variable: 'REGISTRY_HOST'),
                                string(credentialsId: 'REGISTRY_PORT', variable: 'REGISTRY_PORT'),
                                string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')
                            ]) {
                                // 빌드 실행
                                sh """
                                    chmod +x scripts/build_backend.sh
                                    export DB_HOST="${DB_HOST}"
                                    export BACKEND_IMAGE="${BACKEND_IMAGE}"
                                    export BUILD_NUMBER="${BUILD_NUMBER}"
                                    export OPENAI_CHAT_MODEL="${OPENAI_CHAT_MODEL}"
                                    export ORCHESTRATOR_MODE="${ORCHESTRATOR_MODE}"
                                    export FORCE_NON_STREAMING="${FORCE_NON_STREAMING}"
                                    export AUTO_PROMOTE_AFTER_CLARIFICATION="${AUTO_PROMOTE_AFTER_CLARIFICATION}"
                                    export DATABASE_URL="postgresql://postgres:postgres@${DB_HOST}:5432/maice_web"
                                    export GEMINI_API_KEY="${GEMINI_API_KEY}"
                                    export REDIS_URL="${REDIS_URL}"
                                    export DEBUG="True"
                                    export ENVIRONMENT="${DEPLOY_ENV}"
                                    export FORCE_REBUILD="${params.FORCE_REBUILD}"
                                    ./scripts/build_backend.sh
                                """

                                // 빌드 완료 후 바로 Registry에 푸시
                                echo "📦 백엔드 이미지를 Registry에 푸시..."
                                sh """
                                    chmod +x scripts/push_to_registry.sh
                                    export IMAGE_NAME="${BACKEND_IMAGE}"
                                    export BUILD_NUMBER="${BUILD_NUMBER}"
                                    export REGISTRY_HOST="${REGISTRY_HOST}"
                                    export REGISTRY_PORT="${REGISTRY_PORT}"
                                    ./scripts/push_to_registry.sh
                                """

                                echo "✅ 백엔드 빌드 및 Registry 푸시 완료"

                                // Registry 정보를 파일로 저장하여 배포 단계로 전달
                                writeFile file: 'registry-info.txt', text: "${REGISTRY_HOST}:${REGISTRY_PORT}"
                                stash includes: 'registry-info.txt', name: 'registry-info'
                                echo "✅ Registry 정보 저장 완료: ${REGISTRY_HOST}:${REGISTRY_PORT}"
                                }
                            } else {
                                echo "⏭️  백엔드 빌드 건너뜀 - 변경사항 없음"
                                // 빌드를 건너뛴 경우에도 registry-info stash 생성 (배포 단계에서 필요)
                                withCredentials([
                                    string(credentialsId: 'REGISTRY_HOST', variable: 'REGISTRY_HOST'),
                                    string(credentialsId: 'REGISTRY_PORT', variable: 'REGISTRY_PORT')
                                ]) {
                                    writeFile file: 'registry-info.txt', text: "${REGISTRY_HOST}:${REGISTRY_PORT}"
                                    stash includes: 'registry-info.txt', name: 'registry-info'
                                    echo "✅ Registry 정보 저장 완료 (빌드 건너뜀)"
                                }
                            }
                        }
                    }
                }

                stage('Build & Push Agent') {
                    steps {
                        echo "🤖 에이전트 Docker 이미지 빌드 및 Registry 푸시..."

                        script {
                            if (env.BUILD_AGENT == 'true') {
                            withCredentials([
                                string(credentialsId: 'DB_HOST', variable: 'DB_HOST'),
                                string(credentialsId: 'REGISTRY_HOST', variable: 'REGISTRY_HOST'),
                                string(credentialsId: 'REGISTRY_PORT', variable: 'REGISTRY_PORT'),
                                string(credentialsId: 'MCP_OPENAI_BASE_URL', variable: 'MCP_OPENAI_BASE_URL'),
                                string(credentialsId: 'MCP_API_KEY', variable: 'MCP_API_KEY')
                            ]) {
                                // 빌드 실행
                                sh """
                                    chmod +x scripts/build_agent.sh
                                    export DB_HOST="${DB_HOST}"
                                    export AGENT_IMAGE="${AGENT_IMAGE}"
                                    export BUILD_NUMBER="${BUILD_NUMBER}"
                                    export OPENAI_CHAT_MODEL="${OPENAI_CHAT_MODEL}"
                                    export ORCHESTRATOR_MODE="${ORCHESTRATOR_MODE}"
                                    export FORCE_NON_STREAMING="${FORCE_NON_STREAMING}"
                                    export AUTO_PROMOTE_AFTER_CLARIFICATION="${AUTO_PROMOTE_AFTER_CLARIFICATION}"
                                    export OPENAI_EMBED_MODEL="${OPENAI_EMBED_MODEL}"
                                    export AGENT_DATABASE_URL="postgresql://postgres:postgres@${DB_HOST}:5432/maice_agent"
                                    export REDIS_URL="${REDIS_URL}"
                                    export MCP_OPENAI_BASE_URL="${MCP_OPENAI_BASE_URL}"
                                    export MCP_API_KEY="${MCP_API_KEY}"
                                    export FORCE_REBUILD="${params.FORCE_REBUILD}"
                                    ./scripts/build_agent.sh
                                """

                                // 빌드 완료 후 바로 Registry에 푸시
                                echo "📦 에이전트 이미지를 Registry에 푸시..."
                                sh """
                                    chmod +x scripts/push_to_registry.sh
                                    export IMAGE_NAME="${AGENT_IMAGE}"
                                    export BUILD_NUMBER="${BUILD_NUMBER}"
                                    export REGISTRY_HOST="${REGISTRY_HOST}"
                                    export REGISTRY_PORT="${REGISTRY_PORT}"
                                    ./scripts/push_to_registry.sh
                                """

                                echo "✅ 에이전트 빌드 및 Registry 푸시 완료"
                                }
                            } else {
                                echo "⏭️  에이전트 빌드 건너뜀 - 변경사항 없음"
                            }
                        }
                    }
                }
            }
        }

        stage('Parallel Deploy') {
            options {
                timeout(time: 20, unit: 'MINUTES')  // 20분 타임아웃 설정
            }
            steps {
                node('kb-web') {  // kb-web만 사용, 없으면 실패
                    script {
                        // 공통 환경 설정
                        echo "🔧 공통 환경 설정 시작..."

                        // 프론트엔드 배포 디렉토리 권한 설정
                        echo "📁 프론트엔드 배포 디렉토리 권한 설정 중..."
                        sh """
                            # 배포 디렉토리 생성 및 권한 설정
                            FRONT_DIR="/opt/KB-Web/workspace/MAICE/front"
                            BLUE_DIR="\$FRONT_DIR/dist-blue"
                            GREEN_DIR="\$FRONT_DIR/dist-green"
                            CURRENT_DIR="\$FRONT_DIR/dist"

                            echo "디렉토리 생성 및 권한 설정:"
                            echo "  - Blue: \$BLUE_DIR"
                            echo "  - Green: \$GREEN_DIR"
                            echo "  - Current: \$CURRENT_DIR"

                            # 디렉토리 생성 (권한이 있다면)
                            mkdir -p "\$BLUE_DIR" "\$GREEN_DIR" "\$CURRENT_DIR" 2>/dev/null || {
                                echo "⚠️ 디렉토리 생성 실패 - 권한 부족"
                                echo "💡 수동으로 다음 명령어를 실행하세요:"
                                echo "   sudo mkdir -p \$BLUE_DIR \$GREEN_DIR \$CURRENT_DIR"
                                echo "   sudo chown -R jenkins-agent:jenkins-agent \$FRONT_DIR"
                                echo "   sudo chmod -R 755 \$FRONT_DIR"
                            }

                            # 권한 확인
                            if [ -w "\$FRONT_DIR" ]; then
                                echo "✅ 프론트엔드 디렉토리 쓰기 권한 확인됨"
                            else
                                echo "❌ 프론트엔드 디렉토리 쓰기 권한 없음"
                                echo "💡 젠킨스 에이전트에 적절한 권한을 부여하세요"
                            fi
                        """

                        // 아티팩트 복원
                        echo "📥 아티팩트 복원 시작..."
                        try {
                            unstash "deploy-package-${BUILD_NUMBER}"
                            echo "✅ 배포 패키지 stash 복원 완료"
                        } catch (Exception e) {
                            echo "❌ 배포 패키지 stash 복원 실패: ${e.getMessage()}"
                            error "배포 패키지를 찾을 수 없습니다. 빌드 단계를 확인하세요."
                        }

                        try {
                            // Stash 복원 (원칙 준수: 고유한 이름으로 정확한 stash 복원)
                            def retryCount = 0
                            def maxRetries = 3
                            def stashSuccess = false

                            while (retryCount < maxRetries && !stashSuccess) {
                                try {
                                    unstash "frontend-build-${BUILD_NUMBER}"
                                    echo "✅ 프론트엔드 빌드 stash 복원 완료 (시도 ${retryCount + 1}/${maxRetries})"
                                    stashSuccess = true
                                } catch (Exception e) {
                                    retryCount++
                                    echo "⚠️ Stash 복원 실패 (시도 ${retryCount}/${maxRetries}): ${e.getMessage()}"
                                    if (retryCount < maxRetries) {
                                        echo "5초 후 재시도합니다..."
                                        sleep(5)
                                    }
                                }
                            }

                            if (!stashSuccess) {
                                throw new Exception("Stash 복원을 ${maxRetries}번 시도했지만 실패했습니다")
                            }

                            // stash된 파일들 목록 확인
                            sh """
                                echo "📋 stash 복원 후 현재 디렉토리 내용:"
                                ls -la
                                echo ""
                                echo "📋 압축된 파일 확인:"
                                # 여러 가능한 파일명 확인
                                FRONTEND_TAR_FILE=""
                                for filename in "frontend-build-${BUILD_NUMBER}.tar.gz" "frontend-${BUILD_NUMBER}.tar.gz"; do
                                    if [ -f "\$filename" ]; then
                                        FRONTEND_TAR_FILE="\$filename"
                                        echo "✅ 압축 파일 발견: \$filename"
                                        break
                                    fi
                                done
                                
                                if [ -n "\$FRONTEND_TAR_FILE" ]; then
                                    echo "압축 파일 크기: \$(du -sh \$FRONTEND_TAR_FILE)"
                                    echo "압축 파일 내용:"
                                    tar -tzf \$FRONTEND_TAR_FILE | head -10
                                    echo "... (총 \$(tar -tzf \$FRONTEND_TAR_FILE | wc -l) 개 파일)"
                                    echo ""
                                    echo "압축된 빌드 결과를 해제합니다..."
                                    tar -xzf \$FRONTEND_TAR_FILE
                                    rm -f \$FRONTEND_TAR_FILE
                                    echo "✅ 압축 해제 완료"
                                else
                                    echo "ℹ️ 압축 파일이 없습니다. 직접 복원된 것으로 보입니다."
                                fi
                                echo ""
                                echo "📋 해제/복원 후 디렉토리 구조:"
                                find . -name "build" -type d
                                find . -name "front" -type d
                            """

                            // 빌드 파일 복원 확인

                            echo "복원된 프론트엔드 빌드 파일 확인:"
                            sh """
                                echo "현재 디렉토리: \$(pwd)"
                                echo "전체 파일 목록:"
                                find . -name "build" -type d
                                echo "front/build 디렉토리 확인:"
                                if [ -d "front/build" ]; then
                                    echo "✅ front/build 디렉토리 존재"
                                    ls -la front/build/ | head -10
                                    echo "빌드 파일 개수: \$(find front/build -type f | wc -l)"
                                    echo "빌드 디렉토리 크기: \$(du -sh front/build)"

                                    # 빌드 파일 존재 여부 상세 검증
                                    if [ "\$(find front/build -type f | wc -l)" -gt 0 ]; then
                                        echo "✅ 실제 빌드 파일이 존재합니다"
                                        echo "주요 빌드 파일들:"
                                        find front/build -name "*.html" -o -name "*.js" -o -name "*.css" | head -5
                                    else
                                        echo "❌ 빌드 디렉토리는 있지만 파일이 없습니다"
                                        echo "디렉토리 구조:"
                                        find front/build -type d
                                    fi
                                else
                                    echo "❌ front/build 디렉토리 없음"
                                    echo "front 디렉토리 내용:"
                                    ls -la front/ || echo "front 디렉토리도 없음"
                                fi
                            """
                        } catch (Exception e) {
                            echo "❌ 프론트엔드 빌드 stash 복원 실패: ${e.getMessage()}"
                            echo "⚠️ 프론트엔드 빌드 결과 없이 계속 진행"

                            sh """
                                mkdir -p front/build
                                echo "빈 front/build 디렉토리 생성 완료"
                            """
                        }

                        try {
                            unstash "frontend-status-${BUILD_NUMBER}"
                            echo "✅ 프론트엔드 상태 stash 복원 완료"
                        } catch (Exception e) {
                            echo "❌ 프론트엔드 상태 stash 복원 실패: ${e.getMessage()}"
                            sh 'echo "FRONTEND_BUILD_SUCCESS=false" > frontend-build-status.txt'
                            echo "⚠️ 기본 빌드 상태 파일 생성"
                        }

                        // 배포 패키지 압축 해제
                        sh """
                            echo "현재 디렉토리: \$(pwd)"
                            echo "복원된 파일 확인:"
                            ls -la

                            # 배포 패키지 압축 해제
                            if [ -f "deploy-package.tar.gz" ]; then
                                tar -xzf deploy-package.tar.gz
                                echo "✅ 배포 패키지 압축 해제 완료"
                                ls -la deploy-package/scripts/
                                
                                # Docker Compose 파일들 복사
                                if [ -f "deploy-package/docker-compose.prod.yml" ]; then
                                    cp deploy-package/docker-compose.prod.yml .
                                    echo "✅ docker-compose.prod.yml 복사 완료"
                                fi
                                if [ -f "deploy-package/docker-compose.yml" ]; then
                                    cp deploy-package/docker-compose.yml .
                                    echo "✅ docker-compose.yml 복사 완료"
                                fi
                                
                                # Nginx 설정 파일들 복사
                                if [ -d "deploy-package/nginx" ]; then
                                    mkdir -p nginx/conf.d
                                    
                                    # 기존 설정 파일들 정리 (충돌 방지)
                                    rm -f nginx/conf.d/upstream.conf 2>/dev/null || echo "upstream.conf 없음"
                                    rm -f nginx/conf.d/maice-back-*.conf 2>/dev/null || echo "Blue-Green 설정 파일 없음"
                                    rm -f nginx/conf.d/maice.conf 2>/dev/null || echo "maice.conf 없음"
                                    rm -f nginx/conf.d/maice.conf.backup 2>/dev/null || echo "maice.conf.backup 없음"
                                    
                                    cp deploy-package/nginx/conf.d/* nginx/conf.d/ 2>/dev/null || echo "nginx conf.d 파일 없음"
                                    cp deploy-package/nginx/nginx.conf nginx/ 2>/dev/null || echo "nginx.conf 없음 - 기본 설정 사용"
                                    echo "✅ Nginx 설정 파일 복사 완료"
                                else
                                    echo "⚠️ 배포 패키지에 nginx 설정 파일이 없습니다"
                                fi
                            else
                                echo "❌ 배포 패키지 파일을 찾을 수 없습니다!"
                                exit 1
                            fi
                        """

                        // 환경 변수 설정
                        echo "🔧 환경 변수 설정 중..."

                        // DB_HOST 크레덴셜에서 가져오기
                        try {
                            withCredentials([string(credentialsId: 'DB_HOST', variable: 'DB_HOST')]) {
                                env.DB_HOST = DB_HOST
                                env.DATABASE_URL = "postgresql://postgres:postgres@" +
                                                   "${env.DB_HOST}:5432/maice_web"
                                env.AGENT_DATABASE_URL = "postgresql://postgres:postgres@" +
                                                         "${env.DB_HOST}:5432/maice_agent"
                                echo "✅ DB_HOST 크레덴셜에서 가져옴: ${env.DB_HOST}"
                            }
                        } catch (Exception e) {
                            echo "❌ DB_HOST 크레덴셜을 찾을 수 없습니다: ${e.getMessage()}"
                            echo "⚠️ 기본값 localhost 사용"
                            env.DB_HOST = "localhost"
                            env.DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/maice_web"
                            env.AGENT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/maice_agent"
                        }

                        // Registry 정보 복원
                        unstash 'registry-info'
                        def registryInfo = readFile('registry-info.txt').trim()
                        def registryParts = registryInfo.split(':')
                        env.REGISTRY_HOST = registryParts[0]
                        env.REGISTRY_PORT = registryParts[1]
                        env.REGISTRY_URL = "${env.REGISTRY_HOST}:${env.REGISTRY_PORT}"

                        // 필수 환경변수들 설정
                        try {
                            withCredentials([string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY')]) {
                                env.OPENAI_API_KEY = OPENAI_API_KEY
                                echo "✅ OPENAI_API_KEY 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ OPENAI_API_KEY가 설정되지 않음 (필수)"
                            env.OPENAI_API_KEY = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'GOOGLE_CLIENT_ID', variable: 'GOOGLE_CLIENT_ID')]) {
                                env.GOOGLE_CLIENT_ID = GOOGLE_CLIENT_ID
                                echo "✅ GOOGLE_CLIENT_ID 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ GOOGLE_CLIENT_ID가 설정되지 않음 (필수)"
                            env.GOOGLE_CLIENT_ID = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'GOOGLE_CLIENT_SECRET', variable: 'GOOGLE_CLIENT_SECRET')]) {
                                env.GOOGLE_CLIENT_SECRET = GOOGLE_CLIENT_SECRET
                                echo "✅ GOOGLE_CLIENT_SECRET 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ GOOGLE_CLIENT_SECRET이 설정되지 않음 (필수)"
                            env.GOOGLE_CLIENT_SECRET = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'ADMIN_USERNAME', variable: 'ADMIN_USERNAME')]) {
                                env.ADMIN_USERNAME = ADMIN_USERNAME
                                echo "✅ ADMIN_USERNAME 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ ADMIN_USERNAME이 설정되지 않음 (필수)"
                            env.ADMIN_USERNAME = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'ADMIN_PASSWORD', variable: 'ADMIN_PASSWORD')]) {
                                env.ADMIN_PASSWORD = ADMIN_PASSWORD
                                echo "✅ ADMIN_PASSWORD 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ ADMIN_PASSWORD가 설정되지 않음 (필수)"
                            env.ADMIN_PASSWORD = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'SESSION_SECRET_KEY', variable: 'SESSION_SECRET_KEY')]) {
                                env.SESSION_SECRET_KEY = SESSION_SECRET_KEY
                                echo "✅ SESSION_SECRET_KEY 발견됨"
                            }
                        } catch (Exception e) {
                            echo "❌ SESSION_SECRET_KEY가 설정되지 않음 (필수)"
                            env.SESSION_SECRET_KEY = ""
                        }

                        // 선택적 환경변수들
                        try {
                            withCredentials([string(credentialsId: 'ANTHROPIC_API_KEY', variable: 'ANTHROPIC_API_KEY')]) {
                                env.ANTHROPIC_API_KEY = ANTHROPIC_API_KEY
                                echo "✅ ANTHROPIC_API_KEY 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ ANTHROPIC_API_KEY가 설정되지 않음 (선택사항)"
                            env.ANTHROPIC_API_KEY = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')]) {
                                env.GEMINI_API_KEY = GEMINI_API_KEY
                                echo "✅ GEMINI_API_KEY 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ GEMINI_API_KEY가 설정되지 않음 (선택사항)"
                            env.GEMINI_API_KEY = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'GOOGLE_REDIRECT_URI', variable: 'GOOGLE_REDIRECT_URI')]) {
                                env.GOOGLE_REDIRECT_URI = GOOGLE_REDIRECT_URI
                                echo "✅ GOOGLE_REDIRECT_URI 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ GOOGLE_REDIRECT_URI가 설정되지 않음 (선택사항)"
                            env.GOOGLE_REDIRECT_URI = "https://maice.kbworks.xyz/auth/google/callback"
                        }

                        try {
                            withCredentials([string(credentialsId: 'MCP_SERVER_URL', variable: 'MCP_SERVER_URL')]) {
                                env.MCP_SERVER_URL = MCP_SERVER_URL
                                echo "✅ MCP_SERVER_URL 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ MCP_SERVER_URL이 설정되지 않음 (선택사항)"
                            env.MCP_SERVER_URL = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'MCP_OPENAI_BASE_URL', variable: 'MCP_OPENAI_BASE_URL')]) {
                                env.MCP_OPENAI_BASE_URL = MCP_OPENAI_BASE_URL
                                echo "✅ MCP_OPENAI_BASE_URL 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ MCP_OPENAI_BASE_URL이 설정되지 않음 (선택사항)"
                            env.MCP_OPENAI_BASE_URL = ""
                        }

                        try {
                            withCredentials([string(credentialsId: 'MCP_API_KEY', variable: 'MCP_API_KEY')]) {
                                env.MCP_API_KEY = MCP_API_KEY
                                echo "✅ MCP_API_KEY 발견됨"
                            }
                        } catch (Exception e) {
                            echo "⚠️ MCP_API_KEY가 설정되지 않음 (선택사항)"
                            env.MCP_API_KEY = ""
                        }

                        // LLM_PROVIDER 설정 (크레덴셜에서만 가져옴)
                        try {
                            withCredentials([string(credentialsId: 'LLM_PROVIDER', variable: 'LLM_PROVIDER')]) {
                                env.LLM_PROVIDER = LLM_PROVIDER
                                echo "✅ LLM_PROVIDER 크레덴셜 사용: ${env.LLM_PROVIDER}"
                            }
                        } catch (Exception e) {
                            echo "⚠️ LLM_PROVIDER가 설정되지 않음 (기본값: mcp)"
                            env.LLM_PROVIDER = "mcp"
                        }
                        
                        // LLM_PROVIDER 값 검증 로깅
                        echo "🔍 LLM_PROVIDER 최종 설정 확인:"
                        echo "  - env.LLM_PROVIDER: ${env.LLM_PROVIDER}"

                        // 환경 변수 검증
                        sh """
                            chmod +x deploy-package/scripts/validate_environment.sh
                            ./deploy-package/scripts/validate_environment.sh
                        """

                        // 배포 스크립트에 필요한 환경변수 설정
                        env.BACKEND_IMAGE = "${BACKEND_IMAGE}"
                        env.AGENT_IMAGE = "${AGENT_IMAGE}"
                        env.BUILD_NUMBER = "${BUILD_NUMBER}"
                        
                        // 빌드 번호 검증
                        echo "🔍 배포 환경변수 검증:"
                        echo "  - BACKEND_IMAGE: ${env.BACKEND_IMAGE}"
                        echo "  - AGENT_IMAGE: ${env.AGENT_IMAGE}"
                        echo "  - BUILD_NUMBER: ${env.BUILD_NUMBER}"
                        echo "  - REGISTRY_URL: ${env.REGISTRY_URL}"

                        echo "✅ 공통 환경 설정 완료"

                        // 인프라 관리 단계
                        echo "🏗️ 인프라 관리 작업 실행..."
                        sh """
                            echo "인프라 관리 옵션:"
                            echo "  - INFRA_ACTION: ${params.INFRA_ACTION}"
                            echo "  - INFRA_SERVICE: ${params.INFRA_SERVICE}"
                            echo "  - SHOW_INFRA_LOGS: ${params.SHOW_INFRA_LOGS}"
                            echo "  - RESTART_REDIS: ${params.RESTART_REDIS}"
                            echo "  - RESTART_NGINX: ${params.RESTART_NGINX}"

                            # 인프라 관리 스크립트 실행 권한 부여
                            chmod +x deploy-package/scripts/manage_infrastructure.sh

                            # 로그 확인 요청
                            if [ "${params.SHOW_INFRA_LOGS}" = "true" ]; then
                                echo "📋 인프라 서비스 로그 확인 중..."
                                if [ "${params.INFRA_SERVICE}" = "all" ]; then
                                    ./deploy-package/scripts/manage_infrastructure.sh -l redis
                                    echo ""
                                    ./deploy-package/scripts/manage_infrastructure.sh -l nginx
                                else
                                    ./deploy-package/scripts/manage_infrastructure.sh -l "${params.INFRA_SERVICE}"
                                fi
                            fi

                            # 인프라 관리 작업 실행
                            if [ "${params.INFRA_ACTION}" != "none" ]; then
                                echo "🔧 인프라 관리 작업 실행: ${params.INFRA_ACTION} ${params.INFRA_SERVICE}"
                                
                                case "${params.INFRA_ACTION}" in
                                    "restart")
                                        ./deploy-package/scripts/manage_infrastructure.sh -r "${params.INFRA_SERVICE}"
                                        ;;
                                    "start")
                                        ./deploy-package/scripts/manage_infrastructure.sh -u "${params.INFRA_SERVICE}"
                                        ;;
                                    "stop")
                                        ./deploy-package/scripts/manage_infrastructure.sh -d "${params.INFRA_SERVICE}"
                                        ;;
                                    "status")
                                        ./deploy-package/scripts/manage_infrastructure.sh -s "${params.INFRA_SERVICE}"
                                        ;;
                                    "config-check")
                                        if [ "${params.INFRA_SERVICE}" = "nginx" ]; then
                                            ./deploy-package/scripts/manage_infrastructure.sh -c nginx
                                        elif [ "${params.INFRA_SERVICE}" = "redis" ]; then
                                            ./deploy-package/scripts/manage_infrastructure.sh -c redis
                                        else
                                            echo "⚠️ 설정 확인은 nginx 또는 redis에 대해서만 가능합니다"
                                        fi
                                        ;;
                                    *)
                                        echo "⚠️ 알 수 없는 인프라 작업: ${params.INFRA_ACTION}"
                                        ;;
                                esac
                            fi

                            # 기존 재시작 옵션 (하위 호환성)
                            echo "🔄 기존 재시작 옵션 처리 중..."
                            
                            # Redis 컨테이너 처리
                            if [ "${params.RESTART_REDIS}" = "true" ]; then
                                echo "🔄 Redis 컨테이너 재시작 중 (기존 옵션)..."
                                ./deploy-package/scripts/manage_infrastructure.sh -r redis
                            elif ! docker ps --filter "name=redis" --format "{{.Names}}" | grep -q redis; then
                                echo "Redis 컨테이너가 없습니다. 시작 중..."
                                ./deploy-package/scripts/manage_infrastructure.sh -u redis
                            else
                                echo "✅ Redis 컨테이너가 이미 실행 중입니다"
                            fi


                            echo "✅ 인프라 관리 작업 완료"
                        """

                        // 병렬 배포 실행
                        echo "🚀 병렬 배포 시작 (백엔드, 에이전트, 프론트엔드)..."

                        parallel(
                            "Deploy Backend": {
                                if (env.BUILD_BACKEND == 'true') {
                                    echo "🏗️ 백엔드 Blue-Green 무중단 배포 시작..."
                                    script {
                                        try {
                                        sh """
                                            echo "백엔드 Blue-Green 배포 스크립트 실행 중..."
                                            echo "🔍 배포 환경변수 확인:"
                                            echo "  - BUILD_NUMBER: ${env.BUILD_NUMBER}"
                                            echo "  - BACKEND_IMAGE: ${env.BACKEND_IMAGE}"
                                            echo "  - REGISTRY_URL: ${env.REGISTRY_URL}"
                                            
                                            export DB_HOST="${env.DB_HOST}"
                                            export DB_PORT="${env.DB_PORT}"
                                            export DB_USER="${env.DB_USER}"
                                            export DB_PASSWORD="${env.DB_PASSWORD}"
                                            export DATABASE_URL="${env.DATABASE_URL}"
                                            export AGENT_DATABASE_URL="${env.AGENT_DATABASE_URL}"
                                            export REGISTRY_URL="${env.REGISTRY_URL}"
                                            export BACKEND_IMAGE="${env.BACKEND_IMAGE}"
                                            export BUILD_NUMBER="${env.BUILD_NUMBER}"
                                            export OPENAI_API_KEY="${env.OPENAI_API_KEY}"
                                            export ANTHROPIC_API_KEY="${env.ANTHROPIC_API_KEY}"
                                            export GEMINI_API_KEY="${env.GEMINI_API_KEY}"
                                            export GOOGLE_CLIENT_ID="${env.GOOGLE_CLIENT_ID}"
                                            export GOOGLE_CLIENT_SECRET="${env.GOOGLE_CLIENT_SECRET}"
                                            export GOOGLE_REDIRECT_URI="${env.GOOGLE_REDIRECT_URI}"
                                            export ADMIN_USERNAME="${env.ADMIN_USERNAME}"
                                            export ADMIN_PASSWORD="${env.ADMIN_PASSWORD}"
                                            export SESSION_SECRET_KEY="${env.SESSION_SECRET_KEY}"
                                            export MCP_SERVER_URL="${env.MCP_SERVER_URL}"
                                            chmod +x deploy-package/scripts/deploy_backend_blue_green.sh
                                            ./deploy-package/scripts/deploy_backend_blue_green.sh backend
                                        """
                                        echo "✅ 백엔드 Blue-Green 무중단 배포 완료!"
                                    } catch (Exception e) {
                                        echo "❌ 백엔드 배포 실패: ${e.getMessage()}"
                                        echo "🔄 자동 롤백 시도 중..."
                                        try {
                                            sh """
                                                chmod +x deploy-package/scripts/rollback_backend_blue_green.sh
                                                ./deploy-package/scripts/rollback_backend_blue_green.sh
                                            """
                                            echo "✅ 롤백 성공"
                                        } catch (Exception rollbackError) {
                                            echo "❌ 롤백 실패: ${rollbackError.getMessage()}"
                                            error "백엔드 배포 및 롤백 모두 실패했습니다"
                                        }
                                        error "백엔드 배포 실패로 인해 파이프라인을 중단합니다"
                                    }
                                    }
                                } else {
                                    echo "⏭️  백엔드 빌드 건너뜀 - 변경사항 없음"
                                }
                            },
                            "Deploy Agent": {
                                if (env.BUILD_AGENT == 'true') {
                                    echo "🤖 에이전트 배포 시작..."
                                    sh """
                                        echo "에이전트 배포 스크립트 실행 중..."
                                        echo "🔍 전달되는 환경변수 확인:"
                                        echo "  - LLM_PROVIDER: ${env.LLM_PROVIDER}"
                                        echo "  - AGENT_IMAGE: ${env.AGENT_IMAGE}"
                                        echo "  - BUILD_NUMBER: ${env.BUILD_NUMBER}"
                                    export DB_HOST="${env.DB_HOST}"
                                    export DB_PORT="${env.DB_PORT}"
                                    export DB_USER="${env.DB_USER}"
                                    export DB_PASSWORD="${env.DB_PASSWORD}"
                                    export DATABASE_URL="${env.DATABASE_URL}"
                                    export AGENT_DATABASE_URL="${env.AGENT_DATABASE_URL}"
                                    export REGISTRY_URL="${env.REGISTRY_URL}"
                                    export AGENT_IMAGE="${env.AGENT_IMAGE}"
                                    export BUILD_NUMBER="${env.BUILD_NUMBER}"
                                    export LLM_PROVIDER="${env.LLM_PROVIDER}"
                                    export OPENAI_API_KEY="${env.OPENAI_API_KEY}"
                                    export ANTHROPIC_API_KEY="${env.ANTHROPIC_API_KEY}"
                                    export GEMINI_KEY="${env.GEMINI_API_KEY}"
                                    export MCP_URL="${env.MCP_SERVER_URL}"
                                    export MCP_OPENAI_BASE_URL="${env.MCP_OPENAI_BASE_URL}"
                                    export MCP_API_KEY="${env.MCP_API_KEY}"
                                    echo "✅ 환경변수 export 완료"
                                    echo "  - 확인: LLM_PROVIDER=$LLM_PROVIDER"
                                    echo "  - 확인: MCP_OPENAI_BASE_URL=$MCP_OPENAI_BASE_URL"
                                    chmod +x deploy-package/scripts/deploy_backend_agent.sh
                                    ./deploy-package/scripts/deploy_backend_agent.sh agent
                                    """
                                    echo "✅ 에이전트 배포 완료!"
                                } else {
                                    echo "⏭️  에이전트 빌드 건너뜀 - 변경사항 없음"
                                }
                            },
                            "Deploy Frontend": {
                                if (env.BUILD_FRONTEND == 'true') {
                                    echo "🎨 프론트엔드 배포 시작..."

                                    // 프론트엔드 빌드 상태 확인
                                    if (fileExists('frontend-build-status.txt')) {
                                    def buildStatus = readFile('frontend-build-status.txt').trim()
                                    if (buildStatus.contains('FRONTEND_BUILD_SUCCESS=true')) {
                                        env.FRONTEND_BUILD_SUCCESS = 'true'
                                        echo "✅ 프론트엔드 빌드 성공 상태 확인"
                                    } else {
                                        env.FRONTEND_BUILD_SUCCESS = 'false'
                                        echo "⚠️ 프론트엔드 빌드 실패 상태 확인"
                                    }
                                } else {
                                    env.FRONTEND_BUILD_SUCCESS = 'false'
                                    echo "⚠️ 빌드 상태 파일을 찾을 수 없음 - 실패로 간주"
                                }

                                if (env.FRONTEND_BUILD_SUCCESS == 'true') {
                                    echo "✅ 프론트엔드 빌드가 성공했습니다. Blue-Green 배포를 진행합니다."


                                    // 빌드 결과 검증 및 복사
                                    sh """
                                        echo "🔍 빌드 결과 상세 검증 중..."

                                        # 디렉토리 존재 여부 확인
                                        if [ ! -d "front/build" ]; then
                                            echo "❌ front/build 디렉토리가 없습니다."
                                            echo "프론트엔드 배포를 건너뜁니다."
                                            exit 0
                                        fi

                                        # 빌드 파일 개수 및 크기 확인
                                        BUILD_FILES=\$(find front/build -type f | wc -l)
                                        BUILD_SIZE=\$(du -sh front/build | cut -f1)
                                        echo "빌드 파일 개수: \$BUILD_FILES"
                                        echo "빌드 디렉토리 크기: \$BUILD_SIZE"

                                        if [ \$BUILD_FILES -eq 0 ]; then
                                            echo "⚠️ 빌드 디렉토리는 있지만 파일이 없습니다."
                                            echo "디렉토리 구조 확인:"
                                            find front/build -type d
                                            echo "프론트엔드 배포를 건너뜁니다."
                                            exit 0
                                        fi

                                        # 핵심 빌드 파일 존재 여부 확인
                                        echo "핵심 빌드 파일 확인:"
                                        if [ -f "front/build/index.html" ]; then
                                            echo "✅ index.html 존재"
                                        else
                                            echo "❌ index.html 없음"
                                        fi

                                        JS_FILES=\$(find front/build -name "*.js" | wc -l)
                                        CSS_FILES=\$(find front/build -name "*.css" | wc -l)
                                        echo "JS 파일 개수: \$JS_FILES"
                                        echo "CSS 파일 개수: \$CSS_FILES"

                                        if [ \$JS_FILES -eq 0 ] && [ \$CSS_FILES -eq 0 ]; then
                                            echo "⚠️ JS/CSS 파일이 없습니다. 빌드가 제대로 되지 않았을 수 있습니다."
                                            echo "프론트엔드 배포를 건너뜁니다."
                                            exit 0
                                        fi

                                        echo "✅ 빌드 결과 검증 완료. Blue-Green 배포를 진행합니다."

                                        # 기존 build 디렉토리 정리
                                        rm -rf ./build

                                        # front/build를 build로 복사
                                        cp -r front/build ./build
                                        echo "✅ 빌드 결과를 build 디렉토리로 복사 완료"

                                        # 복사 결과 검증
                                        COPIED_FILES=\$(find ./build -type f | wc -l)
                                        echo "복사된 파일 개수: \$COPIED_FILES"

                                        if [ \$COPIED_FILES -eq \$BUILD_FILES ]; then
                                            echo "✅ 파일 복사 검증 성공"
                                        else
                                            echo "❌ 파일 복사 검증 실패 (원본: \$BUILD_FILES, 복사본: \$COPIED_FILES)"
                                            exit 1
                                        fi
                                    """

                                    // Blue-Green 배포 스크립트 실행
                                    sh """
                                        echo "Blue-Green 배포 스크립트 실행 중..."
                                        echo "🔍 프론트엔드 배포 환경변수 확인:"
                                        echo "  - BUILD_NUMBER: ${env.BUILD_NUMBER}"
                                        echo "  - FRONTEND_BUILD_SUCCESS: ${env.FRONTEND_BUILD_SUCCESS}"
                                        
                                        export BUILD_NUMBER="${env.BUILD_NUMBER}"
                                        chmod +x deploy-package/scripts/deploy_frontend.sh
                                        ./deploy-package/scripts/deploy_frontend.sh
                                    """

                                    echo "✅ 프론트엔드 Blue-Green 배포 완료!"
                                } else {
                                    echo "⚠️ 프론트엔드 빌드가 실패했습니다. 배포를 건너뜁니다."
                                    echo "빌드 상태 파일 내용:"
                                    if (fileExists('frontend-build-status.txt')) {
                                        sh 'cat frontend-build-status.txt'
                                    } else {
                                        echo "빌드 상태 파일이 존재하지 않습니다."
                                    }
                                    }
                                } else {
                                    echo "⏭️  프론트엔드 빌드 건너뜀 - 변경사항 없음"
                                }
                            }
                        )

                        echo "🎉 모든 서비스 병렬 배포 완료!"

                        // 배포 후 모니터링
                        echo "🔍 배포 후 상태 모니터링 시작..."
                        sh """
                            chmod +x deploy-package/scripts/monitor_deployment.sh
                            ./deploy-package/scripts/monitor_deployment.sh
                        """
                        echo "✅ 배포 상태 모니터링 완료"

                        // 최종 상태 확인
                        echo "🔍 최종 컨테이너 상태 확인..."
                        sh """
                            echo "실행 중인 컨테이너:"
                            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                        """
                    }
                }
            }
        }

        stage('Final Verification') {
            steps {
                echo "🔍 최종 배포 검증 및 Nginx reload..."
                
                node('kb-web') {
                    script {
                        sh """
                            echo "최종 배포 검증 시작..."
                            chmod +x deploy-package/scripts/manage_infrastructure.sh
                            
                            # Nginx reload (restart 아님 - 무중단 적용)
                            # 백엔드: upstream 전환 재확인
                            # 프론트엔드: 심볼릭 링크는 실시간 반영되지만, sendfile 캐싱 때문에 안전장치로 reload
                            # reload는 graceful하고 0.1초 미만이므로 부담 없음
                            
                            NGINX_CONTAINER=\$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
                            
                            # Nginx 컨테이너 확인
                            if [ -z "\$NGINX_CONTAINER" ]; then
                                echo "⚠️ Nginx 컨테이너가 없습니다. docker-compose로 시작합니다..."
                                cd /opt/KB-Web/workspace/MAICE
                                docker-compose -f docker-compose.prod.yml up -d nginx
                                
                                # 컨테이너 시작 대기
                                sleep 5
                                NGINX_CONTAINER=\$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
                                
                                if [ -z "\$NGINX_CONTAINER" ]; then
                                    echo "❌ Nginx 컨테이너 시작 실패"
                                    exit 1
                                fi
                                
                                echo "✅ Nginx 컨테이너 시작 완료: \$NGINX_CONTAINER"
                            fi
                            
                            # Nginx가 재시작 중이면 대기
                            echo "📋 Nginx 상태 확인 중..."
                            MAX_WAIT=30
                            WAIT_COUNT=0
                            while [ \$WAIT_COUNT -lt \$MAX_WAIT ]; do
                                NGINX_STATUS=\$(docker inspect \${NGINX_CONTAINER} --format '{{.State.Status}}' 2>/dev/null || echo "")
                                if [ "\$NGINX_STATUS" = "running" ]; then
                                    echo "✅ Nginx가 정상 실행 중입니다"
                                    break
                                elif [ "\$NGINX_STATUS" = "restarting" ]; then
                                    echo "⏳ Nginx 재시작 중... (\$((WAIT_COUNT + 1))/\${MAX_WAIT})"
                                    sleep 2
                                    WAIT_COUNT=\$((WAIT_COUNT + 1))
                                else
                                    echo "❌ Nginx 상태 이상: \${NGINX_STATUS}"
                                    if [ -n "\$NGINX_CONTAINER" ]; then
                                        docker logs \${NGINX_CONTAINER} --tail 20
                                    fi
                                    exit 1
                                fi
                            done
                            
                            if [ \$WAIT_COUNT -eq \$MAX_WAIT ]; then
                                echo "❌ Nginx가 계속 재시작 중입니다"
                                docker logs \${NGINX_CONTAINER} --tail 50
                                exit 1
                            fi
                            
                            echo "📋 Nginx 설정 확인..."
                            docker exec \${NGINX_CONTAINER} nginx -t
                            
                            echo "🔄 Nginx graceful reload (무중단)..."
                            docker exec \${NGINX_CONTAINER} nginx -s reload
                            
                            sleep 2
                            
                            # 최종 헬스체크
                            echo "🏥 최종 헬스체크..."
                            NGINX_CONTAINER=\$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
                            
                            # 백엔드 헬스체크
                            if docker exec \${NGINX_CONTAINER} wget -q -O - http://localhost/health >/dev/null 2>&1; then
                                echo "✅ 백엔드 헬스체크 통과"
                            else
                                echo "⚠️  백엔드 헬스체크 실패 - 확인 필요"
                            fi
                            
                            # 프론트엔드 헬스체크
                            if docker exec \${NGINX_CONTAINER} wget -q -O - http://localhost/ >/dev/null 2>&1; then
                                echo "✅ 프론트엔드 헬스체크 통과"
                            else
                                echo "⚠️  프론트엔드 헬스체크 실패 - 확인 필요"
                            fi
                            
                            # Nginx 상태 확인
                            echo "📊 Nginx 최종 상태:"
                            ./deploy-package/scripts/manage_infrastructure.sh -s nginx
                            
                            echo "✅ 최종 배포 검증 완료"
                        """
                    }
                }
            }
        }

        stage('Docker Cleanup') {
            steps {
                echo "🧹 Docker 레거시 이미지 정리..."

                script {
                    // 최근 5개보다 적은 이미지를 삭제
                    echo "최근 5개보다 적은 Docker 이미지를 정리합니다."

                    sh '''
                        chmod +x scripts/docker_cleanup.sh
                        ./scripts/docker_cleanup.sh
                    '''
                }
            }
        }

        stage('Registry Cleanup') {
            steps {
                echo "🗑️ Docker Registry 레거시 이미지 정리..."

                script {
                    // 최근 5개보다 적은 이미지를 삭제
                    echo "최근 5개보다 적은 Registry 이미지를 정리합니다."

                    sh '''
                        chmod +x scripts/registry_cleanup.sh
                        ./scripts/registry_cleanup.sh
                    '''
                }
            }
        }
    }

    post {
        always {
            echo "🧹 정리 작업 시작..."

            sh '''
                chmod +x scripts/cleanup_build_artifacts.sh
                ./scripts/cleanup_build_artifacts.sh
            '''

            script {
                /* 빌드 정보 저장 */
                def buildInfo = [
                    build_number: env.BUILD_NUMBER,
                    git_commit: env.GIT_COMMIT,
                    git_branch: env.GIT_BRANCH,
                    git_author: env.GIT_AUTHOR,
                    deploy_env: env.DEPLOY_ENV,
                    build_time: new Date().format('yyyy-MM-dd HH:mm:ss'),
                    jenkins_url: env.BUILD_URL
                ]

                writeFile file: 'build-info.json', text: groovy.json.JsonOutput.toJson(buildInfo)
                archiveArtifacts artifacts: 'build-info.json', fingerprint: true
            }
        }

        success {
            echo "✅ 빌드 및 배포 성공!"
        }

        failure {
            echo "❌ 빌드 또는 배포 실패!"

            script {
                echo "📧 실패 알림 전송..."
                echo "⚠️ 롤백은 수동으로 진행해주세요"
            }
        }

        unstable {
            echo "⚠️ 빌드 불안정 (일부 테스트 실패)"
        }
    }
}
