'use client';

import { useState, useMemo } from 'react';
import { StudentResults, GradingResponse } from '@/types/models';
import ScoreCard from './ScoreCard';
import Image from 'next/image';
import { BlockMath, InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

interface GradingResultsProps {
  initialData: StudentResults;
}

export default function GradingResults({ initialData }: GradingResultsProps) {
  // 결과를 문제별로 그룹화
  const groupedResults = useMemo(() => {
    const groups: { [key: string]: GradingResponse[] } = {};
    
    // 모든 결과를 먼저 그룹화
    initialData.results.forEach((result) => {
      if (!groups[result.problem_key]) {
        groups[result.problem_key] = [];
      }
      groups[result.problem_key].push(result);
    });

    // 각 그룹 내에서 시간순 정렬 (오래된 순)
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
    });

    return groups;
  }, [initialData.results]);

  // 문제 키를 오름차순으로 정렬
  const sortedProblemKeys = useMemo(() => {
    return Object.keys(groupedResults).sort((a, b) => {
      // 문제 번호를 숫자로 변환하여 비교
      const numA = parseInt(a.replace(/[^0-9]/g, ''));
      const numB = parseInt(b.replace(/[^0-9]/g, ''));
      return numA - numB;
    });
  }, [groupedResults]);

  // 상태 관리
  const [currentProblem, setCurrentProblem] = useState<string>(
    sortedProblemKeys[0] || ''
  );
  const [selectedGradingIndex, setSelectedGradingIndex] = useState(0);
  const [expandedCriteria, setExpandedCriteria] = useState<Set<string>>(new Set());

  // 이미지 URL 생성 함수 수정
  const getImageUrl = (result: GradingResponse): string | undefined => {
    if (!result?.file_path) return undefined;
    
    // Windows 경로를 URL 경로로 변환
    const path = result.file_path.replace(/\\/g, '/');
    
    // uploads/ 제거 (필요한 경우)
    const cleanPath = path.replace(/^uploads\//, '');
    
    // 문항 번호를 문항{N} 형식으로 변환
    const formattedPath = cleanPath.replace(/문제(\d+)/i, '문항$1');
    
    return `${process.env.NEXT_PUBLIC_API_URL}${formattedPath}`;
  };

  // LaTeX 수식 렌더링 함수
  const renderMath = (text: string | undefined) => {
    if (!text) return null;

    const blocks = text.split(/(\\\[[\s\S]*?\\\])/);
    
    return blocks.map((block, index) => {
      if (block.startsWith('\\[') && block.endsWith('\\]')) {
        const mathContent = block.slice(2, -2).trim();
        return <BlockMath key={index} math={mathContent} />;
      } else if (block.trim()) {
        const inlineParts = block.split(/(\$.*?\$)/);
        return (
          <span key={index}>
            {inlineParts.map((part, i) => {
              if (part.startsWith('$') && part.endsWith('$')) {
                const mathContent = part.slice(1, -1).trim();
                return <InlineMath key={i} math={mathContent} />;
              }
              return <span key={i}>{part}</span>;
            })}
          </span>
        );
      }
      return null;
    });
  };

  // 기준 토글 함수
  const toggleCriteria = (criteriaId: string) => {
    setExpandedCriteria((prev) => {
      const next = new Set(prev);
      
      if (next.has(criteriaId)) {
        next.delete(criteriaId);
      } else {
        next.add(criteriaId);
      }
      return next;
    });
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6">
        {/* 종합 성적 섹션 */}
        <section className="mb-6">
          <h2 className="text-xl font-bold mb-4">종합 성적</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <ScoreCard
              label="총점"
              score={initialData.current_scores.total_score}
              maxScore={initialData.current_scores.max_total_score}
              className="bg-blue-50"
            />
            <ScoreCard
              label="평균"
              score={initialData.current_scores.average_score}
              suffix="%"
              className="bg-green-50"
            />
          </div>
        </section>

        {/* 문제 선택 탭 */}
        <div className="border-b mb-6">
          <div className="flex space-x-4">
            {sortedProblemKeys.map((problemKey) => (
              <button
                key={problemKey}
                onClick={() => {
                  setCurrentProblem(problemKey);
                  setSelectedGradingIndex(0);
                }}
                className={`px-4 py-2 border-b-2 transition-colors
                  ${currentProblem === problemKey
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
              >
                문제 {problemKey}
              </button>
            ))}
          </div>
        </div>

        {/* 채점 결과 표시 */}
        {currentProblem && groupedResults[currentProblem] && (
          <div className="space-y-6">
            {/* 채점 이력 선택 */}
            <div className="flex space-x-2 overflow-x-auto pb-2">
              {groupedResults[currentProblem].map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => setSelectedGradingIndex(index)}
                  className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap
                    ${selectedGradingIndex === index
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                >
                  <div className="flex flex-col items-center">
                    <span>{index + 1}차 채점</span>
                    <span className="text-xs text-gray-500">
                      {new Date(result.created_at).toLocaleDateString()} 
                      {new Date(result.created_at).toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {/* 이미지 섹션을 위로 이동 */}
            <div className="border rounded-lg bg-white overflow-hidden">
              <div className="bg-gray-50 px-4 py-3 border-b">
                <h3 className="font-medium">제출된 답안</h3>
              </div>
              <div className="p-4">
                <div className="relative aspect-[4/3] w-full h-[500px]">
                  {getImageUrl(groupedResults[currentProblem][selectedGradingIndex]) ? (
                    <Image
                      src={getImageUrl(groupedResults[currentProblem][selectedGradingIndex])!}
                      alt="학생 답안"
                      fill
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                      className="object-contain rounded cursor-pointer hover:opacity-90 transition-opacity"
                      onClick={() => {
                        const url = getImageUrl(groupedResults[currentProblem][selectedGradingIndex]);
                        if (url) window.open(url, '_blank');
                      }}
                      priority
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded">
                      <p className="text-gray-500">이미지를 불러올 수 없습니다</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 채점 결과 섹션 */}
            <div className="border rounded-lg bg-white">
              <div className="bg-gray-50 px-4 py-3 border-b flex justify-between items-center">
                <h3 className="font-medium">채점 결과</h3>
                <span className="text-sm text-gray-500">
                  {groupedResults[currentProblem][selectedGradingIndex].grading_number}차 채점
                  ({new Date(groupedResults[currentProblem][selectedGradingIndex].created_at)
                    .toLocaleDateString()})
                </span>
              </div>
              <div className="p-4 space-y-4">
                {/* 파싱된 답안 */}
                {groupedResults[currentProblem][selectedGradingIndex].extracted_text && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-medium mb-2">파싱된 답안</h4>
                    <div className="whitespace-pre-wrap text-gray-700 bg-white p-3 rounded border">
                      {renderMath(groupedResults[currentProblem][selectedGradingIndex].extracted_text)}
                    </div>
                  </div>
                )}

                {/* 채점 기준별 결과 */}
                <div className="space-y-4">
                  <h4 className="font-medium">채점 기준별 점수</h4>
                  {groupedResults[currentProblem][selectedGradingIndex].detailed_scores.map((score) => (
                    <div key={score.id} className="border rounded-lg hover:shadow-sm transition-shadow">
                      <div className="p-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h5 className="font-medium text-gray-900">{score.criteria}</h5>
                            {score.feedback && (
                              <div className="mt-2 text-gray-600">
                                <h6 className="text-sm font-medium mb-1">피드백:</h6>
                                <div className="pl-3 border-l-2 border-gray-200">
                                  {renderMath(score.feedback)}
                                </div>
                              </div>
                            )}
                          </div>
                          <div className="ml-4">
                            <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-medium">
                              {score.score} / {score.max_score}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 총점 */}
                <div className="mt-6 bg-gray-50 p-4 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="font-medium">총점</span>
                      <p className="text-sm text-gray-500 mt-1">전체 배점 대비 획득 점수</p>
                    </div>
                    <div className="text-right">
                      <span className="text-2xl font-bold">
                        {groupedResults[currentProblem][selectedGradingIndex].total_score}
                      </span>
                      <span className="text-gray-500">
                        {' '}/{' '}
                        {groupedResults[currentProblem][selectedGradingIndex].max_score}
                      </span>
                      <p className="text-sm text-gray-500 mt-1">
                        {Math.round((groupedResults[currentProblem][selectedGradingIndex].total_score / 
                          groupedResults[currentProblem][selectedGradingIndex].max_score) * 100)}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
