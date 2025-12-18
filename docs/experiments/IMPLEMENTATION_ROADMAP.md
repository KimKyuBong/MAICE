# MAICE A/B 테스트 구현 로드맵

## 📋 개요

이 문서는 MAICE 시스템 A/B 테스트 실험을 위한 기술적 구현 로드맵을 제공합니다.

---

## 🗄️ 1. 데이터베이스 스키마

### 1.1 새로운 테이블

#### experiment_participants (실험 참여자)
```sql
CREATE TABLE experiment_participants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    experiment_id INTEGER NOT NULL,  -- 실험 식별자
    group_assignment VARCHAR(10) NOT NULL,  -- 'A' or 'B'
    consent_given BOOLEAN DEFAULT FALSE,
    consent_date TIMESTAMP,
    
    -- 인구통계 정보
    grade VARCHAR(50),
    recent_math_score VARCHAR(50),
    weekly_study_hours VARCHAR(50),
    ai_experience VARCHAR(50),
    
    -- 학습 단원
    learning_unit VARCHAR(100),
    
    -- 참여 상태
    status VARCHAR(20) DEFAULT 'registered',  -- registered, active, completed, dropped
    registration_date TIMESTAMP DEFAULT NOW(),
    completion_date TIMESTAMP,
    
    -- 인센티브
    incentive_earned DECIMAL(10,2) DEFAULT 0.00,
    incentive_paid BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, experiment_id)
);

CREATE INDEX idx_exp_participants_user ON experiment_participants(user_id);
CREATE INDEX idx_exp_participants_group ON experiment_participants(experiment_id, group_assignment);
```

#### pre_post_assessments (사전-사후 평가)
```sql
CREATE TABLE pre_post_assessments (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    assessment_type VARCHAR(20) NOT NULL,  -- 'pre', 'mid', 'post', 'followup'
    
    -- 평가 점수
    total_score DECIMAL(5,2),
    basic_score DECIMAL(5,2),
    application_score DECIMAL(5,2),
    advanced_score DECIMAL(5,2),
    transfer_score DECIMAL(5,2),  -- post, followup만
    
    -- 문제별 상세 점수 (JSON)
    question_scores JSONB,
    
    -- 확신도 점수 (JSON)
    confidence_scores JSONB,
    
    -- 풀이 과정 (선택사항)
    solution_processes TEXT,
    
    -- 소요 시간
    time_taken_minutes INTEGER,
    
    -- 완료 정보
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    is_completed BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_assessments_participant ON pre_post_assessments(participant_id);
CREATE INDEX idx_assessments_type ON pre_post_assessments(assessment_type);
```

#### metacognitive_surveys (메타인지 설문)
```sql
CREATE TABLE metacognitive_surveys (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    survey_timing VARCHAR(20) NOT NULL,  -- 'pre', 'post', 'followup'
    
    -- 메타인지 항목들 (1-5점)
    self_awareness INTEGER CHECK (self_awareness BETWEEN 1 AND 5),
    planning_ability INTEGER CHECK (planning_ability BETWEEN 1 AND 5),
    reflection_ability INTEGER CHECK (reflection_ability BETWEEN 1 AND 5),
    concept_connection INTEGER CHECK (concept_connection BETWEEN 1 AND 5),
    self_monitoring INTEGER CHECK (self_monitoring BETWEEN 1 AND 5),
    
    -- Post only
    question_refinement INTEGER CHECK (question_refinement BETWEEN 1 AND 5),
    self_regulation INTEGER CHECK (self_regulation BETWEEN 1 AND 5),
    problem_decomposition INTEGER CHECK (problem_decomposition BETWEEN 1 AND 5),
    thought_elaboration INTEGER CHECK (thought_elaboration BETWEEN 1 AND 5),
    
    -- 평균 점수
    avg_score DECIMAL(3,2),
    
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metacog_participant ON metacognitive_surveys(participant_id);
```

#### problem_solving_surveys (문제해결 능력 설문)
```sql
CREATE TABLE problem_solving_surveys (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    
    -- 문제해결 항목들 (1-5점)
    new_problem_confidence INTEGER CHECK (new_problem_confidence BETWEEN 1 AND 5),
    concept_connection_ability INTEGER CHECK (concept_connection_ability BETWEEN 1 AND 5),
    strategy_diversity INTEGER CHECK (strategy_diversity BETWEEN 1 AND 5),
    step_by_step_approach INTEGER CHECK (step_by_step_approach BETWEEN 1 AND 5),
    
    -- 평균 점수
    avg_score DECIMAL(3,2),
    
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### learning_outcome_surveys (학습 성과 설문)
```sql
CREATE TABLE learning_outcome_surveys (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    survey_timing VARCHAR(20) NOT NULL,  -- 'pre', 'post', 'followup'
    
    -- 학습 성과 항목
    unit_understanding INTEGER CHECK (unit_understanding BETWEEN 1 AND 5),
    confidence_level INTEGER CHECK (confidence_level BETWEEN 1 AND 5),
    new_concepts_learned VARCHAR(50),  -- post only
    application_ability INTEGER CHECK (application_ability BETWEEN 1 AND 5),  -- post only
    
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### system_effectiveness_surveys (시스템 효과성 설문)
```sql
CREATE TABLE system_effectiveness_surveys (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    group_type VARCHAR(10) NOT NULL,  -- 'A' or 'B'
    
    -- A그룹 전용
    clarification_help INTEGER CHECK (clarification_help BETWEEN 1 AND 5),
    clarification_learning INTEGER CHECK (clarification_learning BETWEEN 1 AND 5),
    quality_feedback INTEGER CHECK (quality_feedback BETWEEN 1 AND 5),
    step_guidance INTEGER CHECK (step_guidance BETWEEN 1 AND 5),
    clarification_description TEXT,
    
    -- B그룹 전용
    fast_response_help INTEGER CHECK (fast_response_help BETWEEN 1 AND 5),
    learning_efficiency INTEGER CHECK (learning_efficiency BETWEEN 1 AND 5),
    exploration_ability INTEGER CHECK (exploration_ability BETWEEN 1 AND 5),
    useful_situation TEXT,
    
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### qualitative_responses (주관식 응답)
```sql
CREATE TABLE qualitative_responses (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    survey_timing VARCHAR(20) NOT NULL,  -- 'mid', 'post', 'followup'
    
    -- 주관식 응답들
    biggest_learning TEXT,
    learning_change TEXT,
    memorable_moment TEXT,
    biggest_strength TEXT,
    biggest_weakness TEXT,
    would_continue VARCHAR(50),
    would_continue_reason TEXT,
    recommendation_score INTEGER CHECK (recommendation_score BETWEEN 1 AND 5),
    recommendation_reason TEXT,
    
    -- 중간 체크인 전용
    difficult_concepts TEXT,
    solved_concepts TEXT,
    
    -- 지연 평가 전용
    method_change VARCHAR(50),
    method_change_description TEXT,
    
    completed_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### usage_statistics (사용 통계 - 자동 수집)
```sql
CREATE TABLE usage_statistics (
    id SERIAL PRIMARY KEY,
    participant_id INTEGER NOT NULL REFERENCES experiment_participants(id),
    week_number INTEGER NOT NULL,  -- 1 or 2
    
    -- 사용 패턴
    total_sessions INTEGER DEFAULT 0,
    total_time_minutes INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    total_answers INTEGER DEFAULT 0,
    avg_session_length DECIMAL(5,2),
    
    -- 질문 품질 (A그룹만)
    avg_question_quality DECIMAL(5,2),
    quality_trend VARCHAR(20),  -- 'improving', 'stable', 'declining'
    clarification_count INTEGER DEFAULT 0,
    clarification_success_rate DECIMAL(5,2),
    
    -- 학습 내용
    concepts_covered JSONB,
    difficulty_areas JSONB,
    
    -- 도구 사용
    desmos_usage INTEGER DEFAULT 0,
    latex_usage INTEGER DEFAULT 0,
    
    calculated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_usage_participant ON usage_statistics(participant_id);
```

#### assessment_questions (평가 문제 은행)
```sql
CREATE TABLE assessment_questions (
    id SERIAL PRIMARY KEY,
    question_bank_id INTEGER NOT NULL,  -- 문제 세트 식별
    question_order INTEGER NOT NULL,
    
    question_type VARCHAR(20) NOT NULL,  -- 'basic', 'application', 'advanced', 'transfer'
    question_text TEXT NOT NULL,
    question_latex TEXT,
    question_image_url VARCHAR(500),
    
    -- 정답 정보
    answer_type VARCHAR(20) NOT NULL,  -- 'multiple_choice', 'short_answer', 'numeric', 'open_ended'
    correct_answer TEXT,
    answer_options JSONB,  -- 객관식 선택지
    
    -- 채점 정보
    points DECIMAL(5,2) DEFAULT 1.00,
    auto_gradable BOOLEAN DEFAULT TRUE,
    
    -- 메타데이터
    difficulty_level VARCHAR(20),  -- 'easy', 'medium', 'hard'
    topic VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_questions_bank ON assessment_questions(question_bank_id);
```

---

## 🔧 2. API 엔드포인트

### 2.1 실험 등록 및 관리

```python
# back/app/api/v1/experiment.py

@router.post("/experiments/register")
async def register_participant(
    request: ExperimentRegistrationRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    실험 참여자 등록 및 그룹 배정
    """
    # 1. 이미 등록되어 있는지 확인
    # 2. 무작위 그룹 배정 (균형 유지)
    # 3. 동의서 확인
    # 4. 참여자 정보 저장
    # 5. 환영 이메일 발송
    pass

@router.get("/experiments/{experiment_id}/status")
async def get_experiment_status(
    experiment_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    실험 진행 상황 조회
    """
    # 완료한 단계, 다음 단계, 진행률 반환
    pass

@router.get("/experiments/{experiment_id}/dashboard")
async def get_experiment_dashboard(
    experiment_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    실험 전체 대시보드 (관리자용)
    """
    # 참여자 수, 완료율, 그룹별 통계 등
    pass
```

### 2.2 사전-사후 평가

```python
@router.post("/experiments/pre-survey")
async def submit_pre_survey(
    request: PreSurveyRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    사전 설문 제출
    """
    # 1. 기본 정보 저장
    # 2. 학습 단원 평가 저장
    # 3. 메타인지 기저선 저장
    pass

@router.get("/experiments/assessment-questions/{assessment_type}")
async def get_assessment_questions(
    assessment_type: str,  # 'pre', 'mid', 'post', 'followup'
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    평가 문제 조회
    """
    # 문제 은행에서 문제 가져오기
    pass

@router.post("/experiments/assessment-response")
async def submit_assessment_response(
    request: AssessmentResponseRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    평가 답안 제출 및 자동 채점
    """
    # 1. 답안 저장
    # 2. 자동 채점 (가능한 경우)
    # 3. 점수 계산
    pass

@router.post("/experiments/post-survey")
async def submit_post_survey(
    request: PostSurveyRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    사후 설문 제출
    """
    # 1. 학습 성과 평가
    # 2. 메타인지 변화
    # 3. 문제해결 능력
    # 4. 시스템 효과성
    # 5. 주관식 응답
    pass
```

### 2.3 데이터 분석 및 내보내기

```python
@router.get("/experiments/{experiment_id}/export")
async def export_experiment_data(
    experiment_id: int,
    format: str = "csv",  # 'csv', 'excel', 'json'
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    실험 데이터 내보내기
    """
    # 모든 데이터를 통합하여 분석 가능한 형태로 내보내기
    pass

@router.get("/experiments/{experiment_id}/statistics")
async def get_experiment_statistics(
    experiment_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    실험 통계 조회
    """
    # 기술 통계, 그룹 비교, 효과 크기 등
    pass

@router.post("/experiments/{experiment_id}/calculate-usage")
async def calculate_usage_statistics(
    experiment_id: int,
    current_user: UserModel = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    사용 통계 계산 (시스템 로그로부터)
    """
    # ab_test_interactions에서 데이터 집계
    # usage_statistics 테이블에 저장
    pass
```

---

## 🎨 3. 프론트엔드 컴포넌트

### 3.1 페이지 구조

```
front/src/routes/experiment/
├── register/
│   └── +page.svelte              # 실험 등록
├── pre-survey/
│   └── +page.svelte              # 사전 설문
├── pre-assessment/
│   └── +page.svelte              # 사전 평가
├── mid-checkin/
│   └── +page.svelte              # 중간 체크인
├── post-survey/
│   └── +page.svelte              # 사후 설문
├── post-assessment/
│   └── +page.svelte              # 사후 평가
├── followup/
│   └── +page.svelte              # 지연 평가
├── dashboard/
│   └── +page.svelte              # 진행 현황
└── admin/
    └── +page.svelte              # 관리자 대시보드
```

### 3.2 주요 컴포넌트

#### ExperimentProgress.svelte
```svelte
<script lang="ts">
  export let currentStep: number;
  export let totalSteps: number;
  
  const steps = [
    { name: '사전 설문', status: 'completed' },
    { name: '사전 평가', status: 'completed' },
    { name: '1주차 사용', status: 'in_progress' },
    { name: '중간 체크인', status: 'pending' },
    { name: '2주차 사용', status: 'pending' },
    { name: '사후 평가', status: 'pending' },
    { name: '지연 평가', status: 'pending' }
  ];
</script>

<div class="progress-tracker">
  {#each steps as step, i}
    <div class="step" class:completed={step.status === 'completed'}
         class:current={step.status === 'in_progress'}>
      <div class="step-number">{i + 1}</div>
      <div class="step-name">{step.name}</div>
    </div>
  {/each}
</div>
```

#### LikertScale.svelte
```svelte
<script lang="ts">
  export let question: string;
  export let value: number = 3;
  export let labels: string[] = ['전혀 아님', '아님', '보통', '그렇다', '매우 그렇다'];
  
  function handleChange(newValue: number) {
    value = newValue;
  }
</script>

<div class="likert-scale">
  <p class="question">{question}</p>
  <div class="scale">
    {#each [1, 2, 3, 4, 5] as score}
      <label class="option">
        <input type="radio" name={question} value={score}
               checked={value === score}
               on:change={() => handleChange(score)} />
        <span class="score">{score}</span>
        <span class="label">{labels[score - 1]}</span>
      </label>
    {/each}
  </div>
</div>
```

#### AssessmentQuestion.svelte
```svelte
<script lang="ts">
  import MathRenderer from '$lib/components/MathRenderer.svelte';
  
  export let question: AssessmentQuestion;
  export let answer: any;
  export let showConfidence: boolean = true;
  
  let confidence: number = 3;
</script>

<div class="assessment-question">
  <div class="question-header">
    <span class="question-number">문제 {question.order}</span>
    <span class="question-type">{question.type}</span>
    <span class="points">{question.points}점</span>
  </div>
  
  <div class="question-text">
    {#if question.latex}
      <MathRenderer latex={question.latex} />
    {:else}
      {@html question.text}
    {/if}
  </div>
  
  {#if question.answerType === 'multiple_choice'}
    <div class="options">
      {#each question.options as option, i}
        <label>
          <input type="radio" name="q{question.id}" value={option.value}
                 bind:group={answer} />
          <MathRenderer latex={option.text} />
        </label>
      {/each}
    </div>
  {:else if question.answerType === 'short_answer'}
    <input type="text" bind:value={answer} placeholder="답을 입력하세요" />
  {:else if question.answerType === 'numeric'}
    <input type="number" bind:value={answer} placeholder="숫자로 입력" />
  {/if}
  
  {#if showConfidence}
    <div class="confidence">
      <p>이 문제를 맞혔다고 확신하나요?</p>
      <LikertScale bind:value={confidence} labels={['전혀', '약간', '보통', '확신', '매우 확신']} />
    </div>
  {/if}
</div>
```

---

## 📊 4. 데이터 분석 스크립트

### 4.1 R 분석 스크립트

```r
# scripts/analysis/analyze_ab_test.R

library(tidyverse)
library(effsize)
library(lme4)

# 데이터 로드
data <- read_csv("data/experiments/ab_test_results.csv")

# ===== 기술 통계 =====
descriptive_stats <- data %>%
  group_by(group) %>%
  summarise(
    n = n(),
    
    # 학습 성과
    pre_mean = mean(pre_score, na.rm = TRUE),
    pre_sd = sd(pre_score, na.rm = TRUE),
    post_mean = mean(post_score, na.rm = TRUE),
    post_sd = sd(post_score, na.rm = TRUE),
    gain_mean = mean(gain_score, na.rm = TRUE),
    gain_sd = sd(gain_score, na.rm = TRUE),
    normalized_gain_mean = mean(normalized_gain, na.rm = TRUE),
    
    # 메타인지
    metacog_pre_mean = mean(metacog_pre, na.rm = TRUE),
    metacog_post_mean = mean(metacog_post, na.rm = TRUE),
    metacog_gain_mean = mean(metacog_gain, na.rm = TRUE),
    
    # 학습 효율
    time_mean = mean(total_time_minutes, na.rm = TRUE),
    efficiency_mean = mean(gain_score / total_time_minutes, na.rm = TRUE),
    
    # 지속성
    retention_mean = mean(retention_score, na.rm = TRUE),
    would_continue_mean = mean(would_continue, na.rm = TRUE),
    recommendation_mean = mean(recommendation_score, na.rm = TRUE)
  )

print(descriptive_stats)

# ===== 가설 1: 학습 성과 =====
# Independent t-test
gain_test <- t.test(
  gain_score ~ group,
  data = data,
  alternative = "greater",  # A > B
  var.equal = FALSE
)

print("=== 가설 1: 학습 성과 ===")
print(gain_test)

# Cohen's d
cohens_d_gain <- cohen.d(
  data$gain_score[data$group == "A"],
  data$gain_score[data$group == "B"]
)
print(cohens_d_gain)

# Normalized gain
normalized_test <- t.test(
  normalized_gain ~ group,
  data = data,
  alternative = "greater"
)
print(normalized_test)

# ===== 가설 2: 메타인지 =====
# Repeated measures ANOVA
metacog_long <- data %>%
  select(participant_id, group, metacog_pre, metacog_post) %>%
  pivot_longer(
    cols = starts_with("metacog"),
    names_to = "time",
    values_to = "score"
  )

metacog_anova <- aov(
  score ~ group * time + Error(participant_id/time),
  data = metacog_long
)

print("=== 가설 2: 메타인지 ===")
summary(metacog_anova)

# ANCOVA (사전 점수 통제)
metacog_ancova <- aov(
  metacog_post ~ group + metacog_pre,
  data = data
)
summary(metacog_ancova)

# ===== 가설 3: 문제해결 능력 =====
problem_solving_test <- t.test(
  problem_solving_score ~ group,
  data = data,
  alternative = "greater"
)

print("=== 가설 3: 문제해결 ===")
print(problem_solving_test)

# 전이 문제 정답률
transfer_chisq <- chisq.test(table(data$group, data$transfer_correct))
print(transfer_chisq)

# ===== 가설 4: 학습 효율성 =====
efficiency_ancova <- aov(
  gain_score ~ group + pre_score + total_time_minutes,
  data = data
)

print("=== 가설 4: 학습 효율성 ===")
summary(efficiency_ancova)

# 효과 크기 (eta squared)
eta_squared <- function(aov_result) {
  ss <- summary(aov_result)[[1]]$'Sum Sq'
  ss[1] / sum(ss)
}

print(paste("Eta squared:", eta_squared(efficiency_ancova)))

# ===== 가설 5: 학습 지속성 =====
retention_test <- t.test(
  retention_rate ~ group,
  data = data,
  alternative = "greater"
)

print("=== 가설 5: 학습 지속성 ===")
print(retention_test)

would_continue_test <- t.test(
  would_continue ~ group,
  data = data,
  alternative = "greater"
)
print(would_continue_test)

# ===== 시각화 =====
# 학습 성과 비교
ggplot(data, aes(x = group, y = gain_score, fill = group)) +
  geom_boxplot() +
  geom_jitter(width = 0.2, alpha = 0.5) +
  labs(
    title = "학습 성과 비교 (Gain Score)",
    x = "그룹",
    y = "향상도"
  ) +
  theme_minimal()

ggsave("results/gain_score_comparison.png", width = 8, height = 6)

# 메타인지 변화
ggplot(metacog_long, aes(x = time, y = score, group = participant_id, color = group)) +
  geom_line(alpha = 0.3) +
  geom_point() +
  facet_wrap(~group) +
  labs(
    title = "메타인지 점수 변화",
    x = "시점",
    y = "메타인지 점수"
  ) +
  theme_minimal()

ggsave("results/metacog_change.png", width = 10, height = 6)

# ===== 보고서 생성 =====
sink("results/statistical_report.txt")

cat("======================================\n")
cat("MAICE A/B 테스트 통계 분석 결과\n")
cat("======================================\n\n")

cat("1. 기술 통계\n")
print(descriptive_stats)

cat("\n2. 가설 검증 결과\n")
cat("\n가설 1: 학습 성과\n")
print(gain_test)
print(cohens_d_gain)

cat("\n가설 2: 메타인지\n")
print(summary(metacog_anova))

cat("\n가설 3: 문제해결\n")
print(problem_solving_test)

cat("\n가설 4: 학습 효율성\n")
print(summary(efficiency_ancova))

cat("\n가설 5: 학습 지속성\n")
print(retention_test)

sink()

cat("분석 완료! 결과는 results/ 폴더에 저장되었습니다.\n")
```

### 4.2 Python 전처리 스크립트

```python
# scripts/analysis/preprocess_data.py

import pandas as pd
import json
from sqlalchemy import create_engine

# 데이터베이스 연결
engine = create_engine('postgresql://user:password@localhost:5432/maice')

# ===== 데이터 수집 =====
def collect_experiment_data(experiment_id: int):
    """실험 데이터를 수집하여 분석 가능한 형태로 변환"""
    
    # 참여자 정보
    participants = pd.read_sql(
        f"""
        SELECT * FROM experiment_participants
        WHERE experiment_id = {experiment_id}
        """,
        engine
    )
    
    # 사전-사후 평가
    assessments = pd.read_sql(
        f"""
        SELECT a.*, p.user_id, p.group_assignment
        FROM pre_post_assessments a
        JOIN experiment_participants p ON a.participant_id = p.id
        WHERE p.experiment_id = {experiment_id}
        """,
        engine
    )
    
    # 메타인지 설문
    metacog = pd.read_sql(
        f"""
        SELECT m.*, p.user_id, p.group_assignment
        FROM metacognitive_surveys m
        JOIN experiment_participants p ON m.participant_id = p.id
        WHERE p.experiment_id = {experiment_id}
        """,
        engine
    )
    
    # 사용 통계
    usage = pd.read_sql(
        f"""
        SELECT u.*, p.user_id, p.group_assignment
        FROM usage_statistics u
        JOIN experiment_participants p ON u.participant_id = p.id
        WHERE p.experiment_id = {experiment_id}
        """,
        engine
    )
    
    # 주관식 응답
    qualitative = pd.read_sql(
        f"""
        SELECT q.*, p.user_id, p.group_assignment
        FROM qualitative_responses q
        JOIN experiment_participants p ON q.participant_id = p.id
        WHERE p.experiment_id = {experiment_id}
        """,
        engine
    )
    
    return {
        'participants': participants,
        'assessments': assessments,
        'metacog': metacog,
        'usage': usage,
        'qualitative': qualitative
    }

def create_analysis_dataset(data: dict):
    """분석을 위한 통합 데이터셋 생성"""
    
    participants = data['participants']
    assessments = data['assessments']
    metacog = data['metacog']
    usage = data['usage']
    
    # 사전-사후 점수 피벗
    pre_scores = assessments[assessments['assessment_type'] == 'pre'][
        ['participant_id', 'total_score']
    ].rename(columns={'total_score': 'pre_score'})
    
    post_scores = assessments[assessments['assessment_type'] == 'post'][
        ['participant_id', 'total_score', 'transfer_score']
    ].rename(columns={'total_score': 'post_score'})
    
    # 메타인지 점수 피벗
    metacog_pre = metacog[metacog['survey_timing'] == 'pre'][
        ['participant_id', 'avg_score']
    ].rename(columns={'avg_score': 'metacog_pre'})
    
    metacog_post = metacog[metacog['survey_timing'] == 'post'][
        ['participant_id', 'avg_score']
    ].rename(columns={'avg_score': 'metacog_post'})
    
    # 사용 통계 집계
    usage_summary = usage.groupby('participant_id').agg({
        'total_time_minutes': 'sum',
        'total_questions': 'sum',
        'total_sessions': 'sum',
        'avg_question_quality': 'mean',
        'clarification_count': 'sum',
        'clarification_success_rate': 'mean'
    }).reset_index()
    
    # 모두 합치기
    analysis_df = participants[['id', 'user_id', 'group_assignment', 'grade', 'recent_math_score']]
    analysis_df = analysis_df.merge(pre_scores, left_on='id', right_on='participant_id', how='left')
    analysis_df = analysis_df.merge(post_scores, left_on='id', right_on='participant_id', how='left')
    analysis_df = analysis_df.merge(metacog_pre, left_on='id', right_on='participant_id', how='left')
    analysis_df = analysis_df.merge(metacog_post, left_on='id', right_on='participant_id', how='left')
    analysis_df = analysis_df.merge(usage_summary, left_on='id', right_on='participant_id', how='left')
    
    # 계산된 변수
    analysis_df['gain_score'] = analysis_df['post_score'] - analysis_df['pre_score']
    analysis_df['normalized_gain'] = (
        analysis_df['gain_score'] / (100 - analysis_df['pre_score'])
    )
    analysis_df['metacog_gain'] = analysis_df['metacog_post'] - analysis_df['metacog_pre']
    analysis_df['efficiency'] = analysis_df['gain_score'] / analysis_df['total_time_minutes']
    
    # 그룹 이름 변경
    analysis_df['group'] = analysis_df['group_assignment']
    
    return analysis_df

def export_for_analysis(experiment_id: int):
    """분석용 데이터 내보내기"""
    
    # 데이터 수집
    data = collect_experiment_data(experiment_id)
    
    # 통합 데이터셋 생성
    analysis_df = create_analysis_dataset(data)
    
    # CSV로 저장 (R 분석용)
    analysis_df.to_csv(f'data/experiments/ab_test_results.csv', index=False)
    
    # 주관식 응답 별도 저장
    data['qualitative'].to_csv(f'data/experiments/qualitative_responses.csv', index=False)
    
    print(f"데이터 내보내기 완료: {len(analysis_df)}명")
    print(f"A그룹: {len(analysis_df[analysis_df['group'] == 'A'])}명")
    print(f"B그룹: {len(analysis_df[analysis_df['group'] == 'B'])}명")
    
    return analysis_df

if __name__ == "__main__":
    export_for_analysis(experiment_id=1)
```

---

## 📅 5. 구현 스케줄

### Week 1-2: 백엔드 개발
- [ ] Day 1-2: 데이터베이스 스키마 설계 및 마이그레이션
- [ ] Day 3-4: API 엔드포인트 개발 (등록, 설문)
- [ ] Day 5-6: API 엔드포인트 개발 (평가, 분석)
- [ ] Day 7-8: 자동 채점 시스템 개발
- [ ] Day 9-10: 테스트 및 버그 수정

### Week 3-4: 프론트엔드 개발
- [ ] Day 11-12: 페이지 레이아웃 및 라우팅
- [ ] Day 13-14: 설문 컴포넌트 개발
- [ ] Day 15-16: 평가 컴포넌트 개발
- [ ] Day 17-18: 대시보드 및 진행 상황 표시
- [ ] Day 19-20: 반응형 디자인 및 접근성

### Week 5: 분석 도구 및 테스트
- [ ] Day 21-22: 데이터 분석 스크립트 작성
- [ ] Day 23-24: 시각화 대시보드 개발
- [ ] Day 25: 통합 테스트
- [ ] Day 26-27: 파일럿 테스트 (5-10명)
- [ ] Day 28: 피드백 반영 및 최종 조정

### Week 6: 본 실험 준비
- [ ] 참여자 모집
- [ ] 최종 시스템 점검
- [ ] 모니터링 도구 준비
- [ ] 오리엔테이션 자료 준비

---

## 🧪 6. 테스트 계획

### 6.1 단위 테스트

```python
# tests/test_experiment_api.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_participant(client: AsyncClient, test_user):
    response = await client.post(
        "/api/experiments/register",
        json={
            "consent_given": True,
            "grade": "고등학교 2학년",
            "learning_unit": "수열"
        },
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "participant_id" in data
    assert "group_assignment" in data
    assert data["group_assignment"] in ["A", "B"]

@pytest.mark.asyncio
async def test_submit_pre_survey(client: AsyncClient, test_participant):
    response = await client.post(
        "/api/experiments/pre-survey",
        json={
            "participant_id": test_participant.id,
            "unit_understanding": 3,
            "confidence_level": 3,
            "metacog_scores": {
                "self_awareness": 3,
                "planning_ability": 2,
                "reflection_ability": 3
            }
        }
    )
    
    assert response.status_code == 200
```

### 6.2 통합 테스트

```python
@pytest.mark.asyncio
async def test_complete_experiment_flow(client: AsyncClient):
    # 1. 등록
    register_response = await client.post("/api/experiments/register", ...)
    participant_id = register_response.json()["participant_id"]
    
    # 2. 사전 설문
    await client.post("/api/experiments/pre-survey", ...)
    
    # 3. 사전 평가
    await client.post("/api/experiments/assessment-response", ...)
    
    # 4. 상태 확인
    status_response = await client.get(f"/api/experiments/status/{participant_id}")
    assert status_response.json()["current_step"] == "week1_usage"
```

---

이 로드맵은 A/B 테스트 시스템의 완전한 구현을 위한 기술적 가이드를 제공합니다.
각 단계를 순차적으로 진행하며, 지속적인 테스트와 피드백을 통해 품질을 확보합니다.

