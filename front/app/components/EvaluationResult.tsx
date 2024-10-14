import React from 'react';
import { EvaluationData } from '../types';

interface EvaluationItem {
  score: number;
  feedback: string;
}

interface EvaluationResultProps {
  evaluation: EvaluationData;
}

const EvaluationResult: React.FC<EvaluationResultProps> = ({ evaluation }) => {
  console.log('EvaluationResult에 전달된 evaluation:', evaluation);

  if (!evaluation) {
    return <p>평가 데이터가 없습니다.</p>;
  }

  const categories = [
    { key: 'mathematical_understanding', label: '수학적 이해도' },
    { key: 'logical_explanation', label: '논리적 설명' },
    { key: 'term_accuracy', label: '용어 정확성' },
    { key: 'problem_solving_clarity', label: '문제 해결 명확성' },
    { key: 'communication_skills', label: '의사소통 능력' },
  ];

  return (
    <div className="mt-8 p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
        평가 결과
      </h2>
      {categories.map(({ key, label }) => {
        const item = evaluation[key as keyof EvaluationData];
        if (!item) return null;

        return (
          <div key={key} className="mb-4">
            <h3 className="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-300">
              {label}
            </h3>
            <div className="flex items-center mb-2">
              <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mr-2">
                <div
                  className="bg-blue-600 h-2.5 rounded-full"
                  style={{
                    width: `${item.score * 20}%`,
                  }}
                ></div>
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {item.score}/5
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {item.feedback}
            </p>
          </div>
        );
      })}
    </div>
  );
};

export default EvaluationResult;
