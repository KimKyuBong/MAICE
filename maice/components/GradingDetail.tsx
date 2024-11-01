import { GradingResponse } from '@/types/models';
import { BlockMath, InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

interface GradingDetailProps {
  results: GradingResponse[];
  problemKey: string;
}

export default function GradingDetail({ results, problemKey }: GradingDetailProps) {
  // LaTeX 수식을 렌더링하는 함수
  const renderMath = (text: string) => {
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

  // 채점 번호로 정렬된 결과
  const sortedResults = [...results].sort((a, b) => a.grading_number - b.grading_number);

  return (
    <div className="border rounded-lg p-6 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-bold">문제 {problemKey}</h3>
        <div className="text-sm text-gray-500">
          채점 횟수: {results.length}회
        </div>
      </div>

      {sortedResults.map((grading) => (
        <div 
          key={grading.id}
          className={`${grading.grading_number > 1 ? 'mt-8 pt-8 border-t' : ''}`}
        >
          <div className="flex justify-between items-center mb-4">
            <div className="text-md font-semibold text-gray-700">
              {grading.grading_number}차 채점
            </div>
            <span className="text-sm text-gray-500">
              {new Date(grading.created_at).toLocaleDateString()}
            </span>
          </div>

          {grading.extracted_text && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg overflow-x-auto">
              <div className="whitespace-pre-wrap">
                {renderMath(grading.extracted_text)}
              </div>
            </div>
          )}

          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-semibold mb-2">종합 피드백</h4>
            <div className="text-gray-700 whitespace-pre-line">
              {renderMath(grading.feedback)}
            </div>
          </div>
          
          <div className="space-y-4">
            {grading.detailed_scores.map((score, idx) => (
              <div 
                key={`${grading.id}-score-${idx}`} 
                className="p-4 bg-gray-50 rounded-lg"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <p className="font-medium text-gray-800 mb-2">
                      {score.criteria}
                    </p>
                    {score.feedback && (
                      <p className="text-gray-600 whitespace-pre-line">
                        {renderMath(score.feedback)}
                      </p>
                    )}
                  </div>
                  <div className="ml-4 text-right">
                    <span className="inline-block px-3 py-1 bg-white rounded-full font-medium">
                      {score.score} / {score.max_score}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex justify-between items-center p-4 bg-gray-100 rounded-lg">
            <span className="font-semibold">총점</span>
            <span className="text-lg font-bold">
              {grading.total_score} / {grading.max_score}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}