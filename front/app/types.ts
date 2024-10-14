export interface EvaluationItem {
  score: number;
  feedback: string;
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
