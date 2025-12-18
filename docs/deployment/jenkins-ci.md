# Jenkins CI/CD 파이프라인 가이드

## 📋 개요

MAICE 시스템은 Jenkins를 활용한 자동화된 CI/CD 파이프라인을 통해 지속적인 통합과 배포를 수행합니다.

## 🔧 Jenkins 설정

### 1. Jenkins Credentials 설정

다음 Credentials를 Jenkins에 등록해야 합니다:

#### API 키
```
- OPENAI_API_KEY (String) - OpenAI API 키
- GEMINI_API_KEY (String) - Google Gemini API 키
- CLOUDE_API_KEY (String) - Cloude API 키
```

#### 인증 정보
```
- ADMIN_USERNAME (String) - 관리자 사용자명
- ADMIN_PASSWORD (String) - 관리자 비밀번호
- SESSION_SECRET_KEY (String) - 세션 암호화 키
```

#### Google OAuth
```
- GOOGLE_CLIENT_ID (String) - Google OAuth 클라이언트 ID
- GOOGLE_CLIENT_SECRET (String) - Google OAuth 클라이언트 시크릿
- GOOGLE_REDIRECT_URI (String) - Google OAuth 리다이렉트 URI
```

### 2. Jenkins 파이프라인 설정

#### 파이프라인 파라미터
```groovy
parameters {
    choice(
        name: 'DEPLOY_ENV',
        choices: ['staging', 'production'],
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
        description: '강제 재빌드'
    )
}
```

## 🚀 CI/CD 파이프라인 단계

### 1. 코드 체크아웃
```groovy
stage('Checkout') {
    steps {
        checkout scm
        script {
            env.GIT_COMMIT_SHORT = sh(
                script: "git rev-parse --short HEAD",
                returnStdout: true
            ).trim()
        }
    }
}
```

### 2. 테스트 실행
```groovy
stage('Test') {
    when {
        not { params.SKIP_TESTS }
    }
    steps {
        sh 'cd back && python -m pytest tests/ -v'
        sh 'cd front && npm test'
    }
    post {
        always {
            publishTestResults testResultsPattern: '**/test-results.xml'
        }
    }
}
```

### 3. Docker 이미지 빌드
```groovy
stage('Build Docker Images') {
    steps {
        script {
            def imageTag = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
            
            // 백엔드 이미지 빌드
            sh "docker build -f back/Dockerfile -t maice-system-back:${imageTag} back/"
            
            // 에이전트 이미지 빌드
            sh "docker build -f agent/Dockerfile -t maice-system-agent:${imageTag} agent/"
            
            // 프론트엔드 빌드
            sh "cd front && npm install && npm run build"
        }
    }
}
```

### 4. 이미지 태깅 및 푸시
```groovy
stage('Tag and Push Images') {
    steps {
        script {
            def imageTag = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
            def registry = "192.168.1.107:5000"
            
            // 이미지 태깅
            sh "docker tag maice-system-back:${imageTag} ${registry}/maice-system-back:${imageTag}"
            sh "docker tag maice-system-agent:${imageTag} ${registry}/maice-system-agent:${imageTag}"
            sh "docker tag maice-system-back:${imageTag} ${registry}/maice-system-back:latest"
            sh "docker tag maice-system-agent:${imageTag} ${registry}/maice-system-agent:latest"
            
            // 레지스트리에 푸시
            sh "docker push ${registry}/maice-system-back:${imageTag}"
            sh "docker push ${registry}/maice-system-agent:${imageTag}"
            sh "docker push ${registry}/maice-system-back:latest"
            sh "docker push ${registry}/maice-system-agent:latest"
        }
    }
}
```

### 5. 배포 실행
```groovy
stage('Deploy') {
    steps {
        script {
            def imageTag = "${env.BUILD_NUMBER}-${env.GIT_COMMIT_SHORT}"
            def registry = "192.168.1.107:5000"
            
            // 배포 스크립트 실행
            sh """
                cd deploy-scripts/v5
                groovy deploy-backend-agent.groovy \\
                    --deploy-env=${params.DEPLOY_ENV} \\
                    --image-tag=${imageTag} \\
                    --registry=${registry} \\
                    --force-rebuild=${params.FORCE_REBUILD}
            """
        }
    }
}
```

### 6. 배포 후 검증
```groovy
stage('Post-Deploy Verification') {
    steps {
        script {
            // 헬스체크
            sh 'curl -f http://localhost/health'
            
            // API 테스트
            sh 'curl -f http://localhost/api/student/test'
            
            // 프론트엔드 확인
            sh 'curl -f http://localhost/'
        }
    }
}
```

## 🔄 배포 스크립트

### deploy-backend-agent.groovy
```groovy
#!/usr/bin/env groovy

@Grab('org.yaml:snakeyaml:1.17')

import groovy.transform.Field
import java.util.concurrent.TimeUnit

@Field def config = [:]

def main(args) {
    parseArguments(args)
    validateEnvironment()
    deployServices()
    verifyDeployment()
}

def parseArguments(args) {
    def cli = new CliBuilder(usage: 'deploy-backend-agent.groovy [options]')
    cli.with {
        h longOpt: 'help', 'Show usage information'
        d longOpt: 'deploy-env', args: 1, required: true, 'Deployment environment (staging/production)'
        t longOpt: 'image-tag', args: 1, required: true, 'Docker image tag'
        r longOpt: 'registry', args: 1, required: true, 'Docker registry URL'
        f longOpt: 'force-rebuild', args: 1, 'Force rebuild containers'
    }
    
    def options = cli.parse(args)
    if (options.h) {
        cli.usage()
        System.exit(0)
    }
    
    config.deployEnv = options.d
    config.imageTag = options.t
    config.registry = options.r
    config.forceRebuild = options.f ?: false
}

def validateEnvironment() {
    // 환경 변수 확인
    def requiredEnvVars = [
        'OPENAI_API_KEY',
        'GEMINI_API_KEY',
        'CLOUDE_API_KEY',
        'ADMIN_USERNAME',
        'ADMIN_PASSWORD',
        'SESSION_SECRET_KEY'
    ]
    
    requiredEnvVars.each { envVar ->
        if (!System.getenv(envVar)) {
            throw new Exception("Required environment variable ${envVar} is not set")
        }
    }
}

def deployServices() {
    echo "Starting deployment to ${config.deployEnv} environment"
    
    // 기존 서비스 중지
    sh "docker compose -f docker-compose.prod.yml down"
    
    // 새 서비스 시작
    sh "docker compose -f docker-compose.prod.yml up -d postgres redis nginx"
    
    // 백엔드 컨테이너 실행
    def backendEnvVars = [
        "DATABASE_URL=postgresql://postgres:postgres@postgres:5432/maice_web",
        "REDIS_URL=redis://redis:6379",
        "OPENAI_API_KEY=${System.getenv('OPENAI_API_KEY')}",
        "GEMINI_API_KEY=${System.getenv('GEMINI_API_KEY')}",
        "CLOUDE_API_KEY=${System.getenv('CLOUDE_API_KEY')}",
        "ADMIN_USERNAME=${System.getenv('ADMIN_USERNAME')}",
        "ADMIN_PASSWORD=${System.getenv('ADMIN_PASSWORD')}",
        "SESSION_SECRET_KEY=${System.getenv('SESSION_SECRET_KEY')}"
    ]
    
    sh """
        docker run -d --name maice-back --network maicesystem_maice_network \\
            ${backendEnvVars.collect { "-e ${it}" }.join(' ')} \\
            ${config.registry}/maice-system-back:${config.imageTag}
    """
    
    // 에이전트 컨테이너 실행
    def agentEnvVars = [
        "REDIS_URL=redis://redis:6379",
        "OPENAI_API_KEY=${System.getenv('OPENAI_API_KEY')}",
        "GEMINI_API_KEY=${System.getenv('GEMINI_API_KEY')}",
        "CLOUDE_API_KEY=${System.getenv('CLOUDE_API_KEY')}"
    ]
    
    sh """
        docker run -d --name maice-agent --network maicesystem_maice_network \\
            ${agentEnvVars.collect { "-e ${it}" }.join(' ')} \\
            ${config.registry}/maice-system-agent:${config.imageTag}
    """
}

def verifyDeployment() {
    echo "Verifying deployment..."
    
    // 헬스체크
    retry(3) {
        sh 'curl -f http://localhost/health'
    }
    
    // API 테스트
    retry(3) {
        sh 'curl -f http://localhost/api/student/test'
    }
    
    echo "Deployment verification completed successfully"
}

def retry(maxAttempts, Closure closure) {
    for (int i = 0; i < maxAttempts; i++) {
        try {
            closure()
            return
        } catch (Exception e) {
            if (i == maxAttempts - 1) throw e
            echo "Attempt ${i + 1} failed, retrying..."
            sleep(5)
        }
    }
}
```

## 📊 모니터링 및 알림

### 1. 빌드 상태 알림
```groovy
post {
    always {
        // 빌드 결과 알림
        emailext (
            subject: "MAICE Build ${env.BUILD_NUMBER} - ${currentBuild.result}",
            body: "Build ${env.BUILD_NUMBER} completed with status: ${currentBuild.result}",
            to: "dev-team@company.com"
        )
    }
    
    failure {
        // 실패 시 알림
        slackSend (
            channel: '#deployments',
            color: 'danger',
            message: "MAICE deployment failed: ${env.BUILD_URL}"
        )
    }
    
    success {
        // 성공 시 알림
        slackSend (
            channel: '#deployments',
            color: 'good',
            message: "MAICE deployed successfully to ${params.DEPLOY_ENV}: ${env.BUILD_URL}"
        )
    }
}
```

### 2. 성능 메트릭 수집
```groovy
stage('Collect Metrics') {
    steps {
        script {
            // 빌드 시간
            def buildTime = currentBuild.durationString
            
            // 이미지 크기
            def imageSize = sh(
                script: "docker images --format 'table {{.Size}}' ${registry}/maice-system-back:${imageTag}",
                returnStdout: true
            ).trim()
            
            // 메트릭 저장
            writeFile file: 'build-metrics.json', text: """
                {
                    "build_number": "${env.BUILD_NUMBER}",
                    "build_time": "${buildTime}",
                    "image_size": "${imageSize}",
                    "deploy_env": "${params.DEPLOY_ENV}",
                    "timestamp": "${new Date().toString()}"
                }
            """
            
            archiveArtifacts artifacts: 'build-metrics.json'
        }
    }
}
```

## 🔧 문제 해결

### 1. 빌드 실패
```bash
# 로그 확인
docker logs jenkins

# 디스크 공간 확인
df -h

# Docker 이미지 정리
docker system prune -f
```

### 2. 배포 실패
```bash
# 컨테이너 상태 확인
docker ps -a

# 네트워크 확인
docker network ls
docker network inspect maicesystem_maice_network

# 로그 확인
docker logs maice-back
docker logs maice-agent
```

### 3. 레지스트리 연결 문제
```bash
# 레지스트리 연결 확인
curl -f http://192.168.1.107:5000/v2/

# Docker 로그인 확인
docker login 192.168.1.107:5000
```

## 📝 모범 사례

### 1. 보안
- Credentials는 Jenkins Credentials Store에 안전하게 저장
- 민감한 정보는 환경변수로 관리
- API 키는 하드코딩 금지

### 2. 성능
- Docker 이미지 크기 최적화
- 불필요한 레이어 제거
- 멀티스테이지 빌드 활용

### 3. 안정성
- 롤백 전략 수립
- 헬스체크 구현
- 모니터링 및 알림 설정
