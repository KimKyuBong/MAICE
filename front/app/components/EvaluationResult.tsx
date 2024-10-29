import React, { useEffect, useRef } from 'react';
import { EvaluationData } from '../types';
import Script from 'next/script';

interface EvaluationResultProps {
  evaluation: {
    evaluation: EvaluationData;
  };
}

const EvaluationResult: React.FC<EvaluationResultProps> = ({ evaluation }) => {
  const mathJaxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.MathJax && window.MathJax.typesetPromise) {
      window.MathJax.typesetPromise().then(() => {
        console.log('MathJax typesetting complete');
      });
    }
  }, [evaluation]);

  if (!evaluation || !evaluation.evaluation) {
    return <p>평가 데이터가 없습니다.</p>;
  }

  const evaluationData = evaluation.evaluation;

  const categories = [
    { key: 'mathematical_understanding', label: '수학적 이해도' },
    { key: 'logical_explanation', label: '논리적 설명' },
    { key: 'term_accuracy', label: '용어 정확성' },
    { key: 'problem_solving_clarity', label: '문제 해결 명확성' },
    { key: 'communication_skills', label: '의사소통 능력' },
  ];

  const renderLatex = (text: string) => {
    text = text.replace(/§/g, '\\'); // §를 백슬래시로 변환
    return text.split(/(\\\(.*?\\\))/g).map((part, index) => {
      if (part.startsWith('\\(') && part.endsWith('\\)')) {
        const latex = part.slice(2, -2); // Remove the \(
        return (
          <span
            key={index}
            dangerouslySetInnerHTML={{ __html: `\\(${latex}\\)` }}
          />
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <>
      <Script
        src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.0/es5/tex-mml-chtml.js"
        strategy="afterInteractive"
        onLoad={() => {
          window.MathJax = {
            tex: {
              inlineMath: [
                ['$', '$'],
                ['\\(', '\\)'],
              ],
              displayMath: [
                ['$$', '$$'],
                ['\\[', '\\]'],
              ],
            },
            options: {
              skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
            },
            startup: {
              pageReady: () => {
                return (window.MathJax as any).startup
                  .defaultPageReady()
                  .then(() => {
                    console.log('MathJax initial typesetting complete');
                  });
              },
            },
          };
          (window.MathJax as any).typesetPromise?.();
        }}
      />
      <div
        ref={mathJaxRef}
        className="mt-8 p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-md"
      >
        <h2 className="text-2xl font-bold mb-4 text-gray-800 dark:text-white">
          평가 결과
        </h2>
        {categories.map(({ key, label }) => {
          const item = evaluationData[key as keyof EvaluationData];
          if (!item) return null;

          return (
            <div key={key} className="mb-6">
              <h3 className="text-lg font-semibold mb-2 text-gray-700 dark:text-gray-300">
                {label}
              </h3>
              <div className="flex items-center mb-2">
                <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mr-2">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full"
                    style={{ width: `${item.score * 20}%` }}
                  ></div>
                </div>
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {item.score}/5
                </span>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <p className="mb-2">
                  <strong>피드백:</strong> {renderLatex(item.feedback)}
                </p>
                <p className="mb-2">
                  <strong>개선 방향:</strong> {renderLatex(item.improvement)}
                </p>
                {item.concept_explanation && (
                  <p className="mb-2">
                    <strong>관련 수학적 개념:</strong>{' '}
                    {renderLatex(item.concept_explanation)}
                  </p>
                )}
                {item.step_analysis && (
                  <p className="mb-2">
                    <strong>단계별 분석:</strong>{' '}
                    {renderLatex(item.step_analysis)}
                  </p>
                )}
                {item.correct_usage && (
                  <p className="mb-2">
                    <strong>올바른 용어 사용:</strong>{' '}
                    {renderLatex(item.correct_usage)}
                  </p>
                )}
                {item.clear_solution && (
                  <p className="mb-2">
                    <strong>명확한 해결 과정:</strong>{' '}
                    {renderLatex(item.clear_solution)}
                  </p>
                )}
                {item.effective_communication && (
                  <p className="mb-2">
                    <strong>효과적인 의사소통 방법:</strong>{' '}
                    {renderLatex(item.effective_communication)}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
};

export default EvaluationResult;

<style jsx global>{`
  .MathJax {
    font-size: 1.1em !important;
  }
`}</style>;
