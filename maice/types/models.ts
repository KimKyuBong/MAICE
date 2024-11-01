// 상세 점수 타입
export interface DetailedScore {
    id: number;
    grading_id: number;
    student_id: string;      // 추가
    problem_key: string;     // 추가
    criteria: string;
    score: number;
    max_score: number;
    feedback: string;
    created_at: string;
  }
  
  // 채점 결과 타입
  export interface Grading {
    id: number;
    student_id: string;
    problem_key: string;
    extracted_text: string;
    total_score: number;
    max_score: number;
    feedback: string;
    grading_number: number;
    file_path: string;       // 추가
    is_consolidated: boolean; // 추가
    created_at: string;
    detailed_scores: DetailedScore[];
  }
  
  // 학생 타입
  export interface Student {
    id: string;
    created_at: string;
    total_score: number;
    max_total_score: number;
    average_score: number;
    gradings: Grading[];
    text_extractions?: TextExtraction[]; // 추가 (선택적)
  }
  
  // 텍스트 추출 결과 타입 (추가)
  export interface TextExtraction {
    id: number;
    student_id: string;
    problem_key: string;
    extracted_text: string;
    confidence_score: number;
    extraction_number: number;
    file_path: string;
    is_consolidated: boolean;
    created_at: string;
  }
  
  // API 응답 타입
  export interface GradingResponse {
    id: number;
    student_id: string;
    problem_key: string;
    submission_id: number;  // 추가
    extracted_text: string;
    solution_steps: SolutionStep[];  // 추가
    latex_expressions: Expression[];  // 추가
    total_score: number;
    max_score: number;
    feedback: string;
    grading_number: number;
    file_path: string;
    is_consolidated: boolean;
    submission: StudentSubmission;  // 추가
    detailed_scores: DetailedScore[];
    created_at: string;
    updated_at?: string;
  }
  
  export interface StudentSubmission {
    id: number;
    student_id: string;
    problem_key: string;
    file_name: string;
    file_path: string;
    file_size: number;
    mime_type: string;
    submission_time: string;
  }
  
  export interface StudentResults {
    student_id: string;
    created_at: string;
    current_scores: {
      total_score: number;
      max_total_score: number;
      average_score: number;
    };
    problem_averages: {
      [key: string]: {
        average_score: number;
        max_score: number;
        grading_count: number;
      };
    };
    results: GradingResponse[];
  }
  
  // API 요청 타입
  export interface GradingSubmitRequest {
    student_id: string;
    problem_key: string;
    file: File;
    criteria: {
      배점: number;           // 수정
      세부기준: Array<{      // 수정
        배점: number;
        설명: string;
        모범답안?: string;
      }>;
    };
  }
  
  // 기본 타입 정의
  export interface Expression {
    original: string;
    latex: string;
  }
  
  export interface SolutionStep {
    step_number: number;
    content: string;
    expressions: Expression[];
  }