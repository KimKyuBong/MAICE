'use client';

import { useState } from 'react';
import axios from 'axios';
import { EvaluationResponse } from '../types';
import EvaluationResult from './EvaluationResult';
import Modal from './Modal';

export default function TextEvaluation() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await axios.post<EvaluationResponse>(
        'http://localhost:8000/evaluate-text',
        {
          question,
          answer,
        }
      );
      console.log('API 응답:', response.data);
      setEvaluation(response.data);
      setIsModalOpen(true);
    } catch (error) {
      console.error('Error:', error);
      alert('평가 중 오류가 발생했습니다.');
    }
  };

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-2 font-bold text-gray-700 dark:text-gray-300">
            질문:
          </label>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="w-full px-3 py-2 border rounded bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            required
          />
        </div>
        <div>
          <label className="block mb-2 font-bold text-gray-700 dark:text-gray-300">
            답변:
          </label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            className="w-full px-3 py-2 border rounded bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
            rows={4}
            required
          ></textarea>
        </div>
        <button
          type="submit"
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition duration-300"
        >
          평가하기
        </button>
      </form>
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        {evaluation && <EvaluationResult evaluation={evaluation.evaluation} />}
      </Modal>
    </div>
  );
}
