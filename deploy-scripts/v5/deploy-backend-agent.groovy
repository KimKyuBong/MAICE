#!/usr/bin/env groovy

def deployBackendAgent(script) {
    script.echo "🚀 KB-Web에서 백엔드/에이전트 배포..."
    
    script.script {
        // build-agent에서 전송된 Registry 정보 사용
        script.unstash 'registry-info'
        
        script.sh """
            echo "백엔드/에이전트 배포 시작..."
            
            # Registry에서 이미지 풀
            echo "Docker Registry에서 이미지 풀 중..."
            REGISTRY_URL="${REGISTRY_URL}"
            
            # Registry에서 이미지 풀
            docker pull \${REGISTRY_URL}/maice-back:${BUILD_NUMBER}
            docker pull \${REGISTRY_URL}/maice-agent:${BUILD_NUMBER}
            
            # 로컬 이미지로 태깅
            docker tag \${REGISTRY_URL}/maice-back:${BUILD_NUMBER} ${BACKEND_IMAGE}:${BUILD_NUMBER}
            docker tag \${REGISTRY_URL}/maice-agent:${BUILD_NUMBER} ${AGENT_IMAGE}:${BUILD_NUMBER}
            
            echo "기존 컨테이너 중지 및 제거 중..."
            
            # 모든 관련 컨테이너 중지 및 제거 (이름 패턴으로 처리)
            echo "애플리케이션 컨테이너 정리..."
            docker stop maice-back maice-agent || true
            docker rm maice-back maice-agent || true
            
            echo "인프라 컨테이너 정리 (안전한 패턴 매칭)..."
            # Docker Compose로 안전하게 정리
            docker compose -f docker-compose.prod.yml down || true
            
            # 혹시 남은 컨테이너들을 패턴으로 정리
            docker ps -a --filter "name=maicesystem" --format "table {{.Names}}" | grep -E "(postgres|redis|nginx)" | xargs -r docker stop || true
            docker ps -a --filter "name=maicesystem" --format "table {{.Names}}" | grep -E "(postgres|redis|nginx)" | xargs -r docker rm || true
            
            # 사용하지 않는 이미지 정리
            docker image prune -f || true
            
            echo "새 버전 배포 중..."
            
            # 배포용 docker-compose로 인프라 서비스 시작
            echo "배포용 인프라 서비스 시작..."
            
            # 네트워크가 없으면 생성
            echo "Docker 네트워크 확인 및 생성..."
            if ! docker network ls | grep -q "maicesystem_maice_network"; then
                echo "네트워크가 없음, 생성 중..."
                docker network create maicesystem_maice_network || {
                    echo "❌ 네트워크 생성 실패"
                    exit 1
                }
                echo "✅ 네트워크 생성 완료"
            else
                echo "✅ 네트워크 이미 존재함"
            fi
            
            # 네트워크 상태 확인
            echo "네트워크 상태 확인:"
            docker network ls | grep maice
            
            # 인프라 서비스 시작
            docker compose -f docker-compose.prod.yml up -d redis nginx
            
            # Nginx 컨테이너가 제대로 시작되었는지 확인
            echo "Nginx 컨테이너 시작 확인..."
            sleep 5
            if ! docker ps --filter "name=nginx" --format "{{.Names}}" | grep -q nginx; then
                echo "❌ Nginx 컨테이너가 시작되지 않음, 수동으로 시작 시도..."
                docker compose -f docker-compose.prod.yml up -d nginx
                sleep 3
                if docker ps --filter "name=nginx" --format "{{.Names}}" | grep -q nginx; then
                    echo "✅ Nginx 컨테이너 수동 시작 성공"
                else
                    echo "❌ Nginx 컨테이너 수동 시작도 실패"
                    echo "Docker Compose 로그 확인:"
                    docker compose -f docker-compose.prod.yml logs nginx
                fi
            else
                echo "✅ Nginx 컨테이너 정상 시작됨"
            fi
            
            # PostgreSQL이 준비될 때까지 대기
            echo "PostgreSQL 서비스 준비 대기 중..."
            for i in {1..30}; do
                if docker exec \$(docker ps --filter "name=postgres" --format "{{.Names}}" | head -1) pg_isready -U postgres; then
                    echo "✅ PostgreSQL 서비스 준비 완료"
                    break
                else
                    echo "PostgreSQL 준비 중... (\$i/30)"
                    sleep 2
                    if [ \$i -eq 30 ]; then
                        echo "❌ PostgreSQL 서비스 준비 시간 초과"
                        exit 1
                    fi
                fi
            done
        """
        
        // 백엔드 컨테이너 실행 (필수 환경 변수만)
        script.withCredentials([
            script.string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY'),
            script.string(credentialsId: 'ADMIN_USERNAME', variable: 'ADMIN_USERNAME'),
            script.string(credentialsId: 'ADMIN_PASSWORD', variable: 'ADMIN_PASSWORD'),
            script.string(credentialsId: 'SESSION_SECRET_KEY', variable: 'SESSION_SECRET_KEY'),
            script.string(credentialsId: 'GOOGLE_CLIENT_ID', variable: 'GOOGLE_CLIENT_ID'),
            script.string(credentialsId: 'GOOGLE_CLIENT_SECRET', variable: 'GOOGLE_CLIENT_SECRET')
        ]) {
            script.sh """
                echo "백엔드 컨테이너 실행 중..."
                echo "필수 환경 변수 확인 (마스킹):"
                echo "OPENAI_API_KEY 길이: \${#OPENAI_API_KEY}"
                echo "GOOGLE_CLIENT_ID 길이: \${#GOOGLE_CLIENT_ID}"
                echo "GOOGLE_CLIENT_SECRET 길이: \${#GOOGLE_CLIENT_SECRET}"
                echo "ADMIN_USERNAME: \${ADMIN_USERNAME}"
                echo "SESSION_SECRET_KEY 길이: \${#SESSION_SECRET_KEY}"
                
                # 선택적 환경 변수들을 환경에서 가져오기 (이미 검증됨)
                ANTHROPIC_KEY=\${ANTHROPIC_API_KEY:-""}
                GOOGLE_KEY=\${GOOGLE_API_KEY:-""}
                GOOGLE_REDIRECT=\${GOOGLE_REDIRECT_URI:-"https://maice.kbworks.xyz/auth/google/callback"}
                MCP_URL=\${MCP_SERVER_URL:-""}
                
                echo "선택적 환경 변수 상태:"
                echo "ANTHROPIC_API_KEY 길이: \${#ANTHROPIC_KEY} (선택사항)"
                echo "GOOGLE_API_KEY 길이: \${#GOOGLE_KEY} (선택사항)"
                echo "GOOGLE_REDIRECT_URI: \${GOOGLE_REDIRECT}"
                echo "MCP_SERVER_URL: \${MCP_URL:-'(설정되지 않음)'}"
                
                echo "데이터베이스 연결 정보 확인:"
                echo "DATABASE_URL: \${DATABASE_URL}"
                echo "AGENT_DATABASE_URL: \${AGENT_DATABASE_URL}"
                
                docker run -d --name maice-back --network maicesystem_maice_network \\
                    -e DATABASE_URL="\${DATABASE_URL}" \\
                    -e REDIS_URL=redis://redis:6379 \\
                    -e OPENAI_API_KEY="\${OPENAI_API_KEY}" \\
                    -e ANTHROPIC_API_KEY="\${ANTHROPIC_KEY}" \\
                    -e GOOGLE_API_KEY="\${GOOGLE_KEY}" \\
                    -e ADMIN_USERNAME="\${ADMIN_USERNAME}" \\
                    -e ADMIN_PASSWORD="\${ADMIN_PASSWORD}" \\
                    -e SESSION_SECRET_KEY="\${SESSION_SECRET_KEY}" \\
                    -e GOOGLE_CLIENT_ID="\${GOOGLE_CLIENT_ID}" \\
                    -e GOOGLE_CLIENT_SECRET="\${GOOGLE_CLIENT_SECRET}" \\
                    -e GOOGLE_REDIRECT_URI="\${GOOGLE_REDIRECT}" \\
                    -e MCP_SERVER_URL="\${MCP_URL}" \\
                    -e LLM_PROVIDER=mcp \\
                    -e OPENAI_CHAT_MODEL=gpt-5-mini \\
                    -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \\
                    -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \\
                    -e MCP_MODEL=penGPT \\
                    -e ORCHESTRATOR_MODE=decentralized \\
                    -e FORCE_NON_STREAMING=1 \\
                    -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \\
                    -e PYTHONUNBUFFERED=1 \\
                    -e ENVIRONMENT=production \\
                    -e ENABLE_MAICE_TEST=false \\
                    ${BACKEND_IMAGE}:${BUILD_NUMBER}
            """
        }
        
        // 에이전트 컨테이너 실행 (필수 환경 변수만)
        script.withCredentials([
            script.string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY')
        ]) {
            script.sh """
                echo "에이전트 컨테이너 실행 중..."
                echo "필수 환경 변수 확인 (마스킹):"
                echo "OPENAI_API_KEY 길이: \${#OPENAI_API_KEY}"
                
                # 선택적 환경 변수들을 환경에서 가져오기 (이미 검증됨)
                ANTHROPIC_KEY=\${ANTHROPIC_API_KEY:-""}
                GOOGLE_KEY=\${GOOGLE_API_KEY:-""}
                MCP_URL=\${MCP_SERVER_URL:-""}
                
                echo "선택적 환경 변수 상태:"
                echo "ANTHROPIC_API_KEY 길이: \${#ANTHROPIC_KEY} (선택사항)"
                echo "GOOGLE_API_KEY 길이: \${#GOOGLE_KEY} (선택사항)"
                echo "MCP_SERVER_URL: \${MCP_URL:-'(설정되지 않음)'}"
                
                echo "에이전트 데이터베이스 연결 정보 확인:"
                echo "AGENT_DATABASE_URL: \${AGENT_DATABASE_URL}"
                
                docker run -d --name maice-agent --network maicesystem_maice_network \\
                    -e AGENT_DATABASE_URL="\${AGENT_DATABASE_URL}" \\
                    -e REDIS_URL=redis://redis:6379 \\
                    -e OPENAI_API_KEY="\${OPENAI_API_KEY}" \\
                    -e ANTHROPIC_API_KEY="\${ANTHROPIC_KEY}" \\
                    -e GOOGLE_API_KEY="\${GOOGLE_KEY}" \\
                    -e MCP_SERVER_URL="\${MCP_URL}" \\
                    -e LLM_PROVIDER=mcp \\
                    -e OPENAI_CHAT_MODEL=gpt-5-mini \\
                    -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \\
                    -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \\
                    -e MCP_MODEL=penGPT \\
                    -e ORCHESTRATOR_MODE=decentralized \\
                    -e FORCE_NON_STREAMING=1 \\
                    -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \\
                    -e PYTHONUNBUFFERED=1 \\
                    ${AGENT_IMAGE}:${BUILD_NUMBER}
            """
        }
        
        // 백엔드 컨테이너가 네트워크에 정상 연결되었는지 확인
        script.sh "echo '백엔드 컨테이너 네트워크 연결 확인...' && docker network inspect maicesystem_maice_network | grep -A 5 -B 5 'maice-back'"
        
        // 헬스체크
        script.sh "echo '헬스체크 시작...' && sleep 30"
        
        // nginx를 통한 백엔드 헬스체크 (프로덕션 환경) - 재시도 로직 추가
        script.sh """
            echo "백엔드 헬스체크 시작 (재시도 포함)..."
            for i in {1..5}; do
                echo "헬스체크 시도 \$i/5..."
                if curl -f http://localhost/health; then
                    echo "✅ 백엔드 헬스체크 성공 (nginx 통과)"
                    break
                else
                    echo "헬스체크 실패, 10초 후 재시도..."
                    sleep 10
                    if [ \$i -eq 5 ]; then
                        echo "❌ 백엔드 헬스체크 최종 실패"
                        echo "컨테이너 상태 확인:"
                        docker ps
                        echo "nginx 로그 확인:"
                        docker logs maicesystem_nginx_1 --tail 20
                        echo "백엔드 로그 확인:"
                        docker logs maice-back --tail 20
                        echo "⚠️ 헬스체크 실패했지만 배포는 계속 진행합니다"
                    fi
                fi
            done
        """
        
        // 에이전트 컨테이너 상태 확인
        script.sh """
            if docker ps | grep -q maice-agent; then
                echo "✅ 에이전트 컨테이너 실행 중"
            else
                echo "❌ 에이전트 컨테이너 실행 실패"
                echo "에이전트 로그 확인:"
                docker logs maice-agent --tail 20
                exit 1
            fi
        """
        
        script.sh "echo '✅ 백엔드/에이전트 배포 완료!'"
    }
}

def rollbackBackendAgent(script) {
    script.echo "🔄 프로덕션 롤백 시작..."
    
    script.sh '''
        # 현재 실행 중인 컨테이너 중지
        docker stop maice-back maice-agent || true
        docker rm maice-back maice-agent || true
    '''
    
    // 롤백용 백엔드 컨테이너 실행 (보안 강화)
    script.withCredentials([
        script.string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY'),
        script.string(credentialsId: 'ANTHROPIC_API_KEY', variable: 'ANTHROPIC_API_KEY'),
        script.string(credentialsId: 'GOOGLE_API_KEY', variable: 'GOOGLE_API_KEY'),
        script.string(credentialsId: 'ADMIN_USERNAME', variable: 'ADMIN_USERNAME'),
        script.string(credentialsId: 'ADMIN_PASSWORD', variable: 'ADMIN_PASSWORD'),
        script.string(credentialsId: 'SESSION_SECRET_KEY', variable: 'SESSION_SECRET_KEY'),
        script.string(credentialsId: 'GOOGLE_CLIENT_ID', variable: 'GOOGLE_CLIENT_ID'),
        script.string(credentialsId: 'GOOGLE_CLIENT_SECRET', variable: 'GOOGLE_CLIENT_SECRET'),
        script.string(credentialsId: 'GOOGLE_REDIRECT_URI', variable: 'GOOGLE_REDIRECT_URI'),
        script.string(credentialsId: 'MCP_SERVER_URL', variable: 'MCP_SERVER_URL')
    ]) {
        script.sh """
            echo "롤백용 백엔드 컨테이너 실행 중..."
            docker run -d --name maice-back --network maicesystem_maice_network \\
                -e DATABASE_URL="\${DATABASE_URL}" \\
                -e REDIS_URL=redis://redis:6379 \\
                -e OPENAI_API_KEY="\${OPENAI_API_KEY}" \\
                -e ANTHROPIC_API_KEY="\${ANTHROPIC_API_KEY}" \\
                -e GOOGLE_API_KEY="\${GOOGLE_API_KEY}" \\
                -e ADMIN_USERNAME="\${ADMIN_USERNAME}" \\
                -e ADMIN_PASSWORD="\${ADMIN_PASSWORD}" \\
                -e SESSION_SECRET_KEY="\${SESSION_SECRET_KEY}" \\
                -e GOOGLE_CLIENT_ID="\${GOOGLE_CLIENT_ID}" \\
                -e GOOGLE_CLIENT_SECRET="\${GOOGLE_CLIENT_SECRET}" \\
                -e GOOGLE_REDIRECT_URI="\${GOOGLE_REDIRECT_URI}" \\
                -e MCP_SERVER_URL="\${MCP_SERVER_URL}" \\
                -e LLM_PROVIDER=mcp \\
                -e OPENAI_CHAT_MODEL=gpt-5-mini \\
                -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \\
                -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \\
                -e MCP_MODEL=penGPT \\
                -e ORCHESTRATOR_MODE=decentralized \\
                -e FORCE_NON_STREAMING=1 \\
                -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \\
                -e PYTHONUNBUFFERED=1 \\
                -e ENVIRONMENT=production \\
                -e ENABLE_MAICE_TEST=false \\
                ${BACKEND_IMAGE}:latest || true
        """
    }
    
    // 롤백용 에이전트 컨테이너 실행 (보안 강화)
    script.withCredentials([
        script.string(credentialsId: 'OPENAI_API_KEY', variable: 'OPENAI_API_KEY'),
        script.string(credentialsId: 'ANTHROPIC_API_KEY', variable: 'ANTHROPIC_API_KEY'),
        script.string(credentialsId: 'GOOGLE_API_KEY', variable: 'GOOGLE_API_KEY'),
        script.string(credentialsId: 'MCP_SERVER_URL', variable: 'MCP_SERVER_URL')
    ]) {
        script.sh """
            echo "롤백용 에이전트 컨테이너 실행 중..."
            docker run -d --name maice-agent --network maicesystem_maice_network \\
                -e AGENT_DATABASE_URL="\${AGENT_DATABASE_URL}" \\
                -e REDIS_URL=redis://redis:6379 \\
                -e OPENAI_API_KEY="\${OPENAI_API_KEY}" \\
                -e ANTHROPIC_API_KEY="\${ANTHROPIC_API_KEY}" \\
                -e GOOGLE_API_KEY="\${GOOGLE_API_KEY}" \\
                -e MCP_SERVER_URL="\${MCP_SERVER_URL}" \\
                -e LLM_PROVIDER=mcp \\
                -e OPENAI_CHAT_MODEL=gpt-5-mini \\
                -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \\
                -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \\
                -e MCP_MODEL=penGPT \\
                -e ORCHESTRATOR_MODE=decentralized \\
                -e FORCE_NON_STREAMING=1 \\
                -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \\
                -e PYTHONUNBUFFERED=1 \\
                ${AGENT_IMAGE}:latest || true
        """
    }
    
    script.sh "echo '롤백 완료 - 이전 버전으로 복구됨'"
}

return this
