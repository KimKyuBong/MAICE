import axios from 'axios';
import { Student, Grading, GradingResponse, GradingSubmitRequest, StudentResults } from '@/types/models';

const API_CONFIG = {
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  version: 'v1',
} as const;

const createApiUrl = (path: string): string => {
  return `api/${API_CONFIG.version}/${path.replace(/^\/+/, '')}`;
};

const api = axios.create({
  baseURL: `${API_CONFIG.baseURL}/api/${API_CONFIG.version}/`,
});

export const gradingApi = {
  // 학생 관련 API
  getStudents: async (): Promise<Student[]> => {
    const { data } = await api.get('students');
    return data;
  },

  getStudent: async (studentId: string): Promise<Student> => {
    const { data } = await api.get(`students/${studentId}`);
    return data;
  },

  // 채점 결과 관련 API
  getStudentResults: async (studentId: string): Promise<StudentResults> => {
    try {
      const { data } = await api.get(`/results/${studentId}`);
      return data;
    } catch (error: any) {
      console.error('API Error:', error.response?.data || error.message);
      throw new Error(error.response?.data?.detail || 'Failed to fetch student results');
    }
  },

  submitGrading: async (formData: FormData): Promise<GradingResponse> => {
    const { data } = await api.post('submit', formData);
    return data;
  },

  // 문제별 채점 결과
  getProblemResults: async (studentId: string, problemKey: string): Promise<Grading[]> => {
    const { data } = await api.get(`results/${studentId}/problem/${problemKey}`);
    return data;
  },

  // 채점 결과 수정
  updateGrading: async (gradingId: number, updates: Partial<Grading>): Promise<GradingResponse> => {
    const { data } = await api.patch(`grading/${gradingId}`, updates);
    return data;
  },

  // 채점 결과 삭제
  deleteGrading: async (gradingId: number): Promise<void> => {
    await api.delete(`grading/${gradingId}`);
  },
};

// API 요청/응답 인터셉터
api.interceptors.request.use(
  (config) => {
    // 요청 전처리 (예: 토큰 추가)
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 타입 가드
export const isGradingResponse = (data: any): data is GradingResponse => {
  return (
    'id' in data &&
    'student_id' in data &&
    'problem_key' in data &&
    'total_score' in data &&
    'max_score' in data
  );
};
