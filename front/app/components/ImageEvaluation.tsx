'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { EvaluationResponse } from '../types';
import EvaluationResult from './EvaluationResult';
import Modal from './Modal';

export default function ImageEvaluation() {
  const [image, setImage] = useState<File | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImage(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!image) {
      alert('이미지를 선택해주세요.');
      return;
    }

    const formData = new FormData();
    formData.append('image', image);

    try /*  */ {
      const response = await axios.post<EvaluationResponse>(
        'http://localhost:8000/analyze-image',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
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
            이미지 업로드:
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            className="w-full text-gray-700 dark:text-gray-300"
            required
          />
        </div>
        <button
          type="submit"
          className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 transition duration-300"
        >
          평가하기
        </button>
      </form>
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        {evaluation && <EvaluationResult evaluation={evaluation} />}
      </Modal>
    </div>
  );
}
