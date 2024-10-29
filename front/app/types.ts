export interface EvaluationItem {
  score: number;
  feedback: string;
  improvement: string;
  concept_explanation?: string;
  step_analysis?: string;
  correct_usage?: string;
  clear_solution?: string;
  effective_communication?: string;
}

export interface EvaluationData {
  mathematical_understanding: EvaluationItem;
  logical_explanation: EvaluationItem;
  term_accuracy: EvaluationItem;
  problem_solving_clarity: EvaluationItem;
  communication_skills: EvaluationItem;
}

export interface EvaluationResponse {
  evaluation: EvaluationData;
}
