'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { gradingApi } from '@/services/api';

interface SubmissionFormProps {
  studentId: string | null;
}

export default function SubmissionForm({ studentId }: SubmissionFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const { register, handleSubmit, reset } = useForm();

  const onSubmit = async (data: any) => {
    if (!studentId) return;

    try {
      setSubmitting(true);
      const formData = new FormData();
      formData.append('file', data.file[0]);
      formData.append('problem_key', data.problem_key);
      formData.append('student_id', studentId);
      formData.append('criteria', JSON.stringify({
        // 여기에 채점 기준을 추가
        accuracy: { max_score: 5, weight: 1 },
        presentation: { max_score: 3, weight: 0.5 }
      }));

      await gradingApi.submitGrading(formData);
      reset();
      alert('제출이 완료되었습니다.');
    } catch (error) {
      console.error('제출 실패:', error);
      alert('제출에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!studentId) {
    return null;
  }

  return (
    <div className="mt-6 bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold mb-4">새로운 답안 제출</h2>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            문제 번호
          </label>
          <input
            type="text"
            {...register('problem_key', { required: true })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
      </form>
    </div>
  );
} 