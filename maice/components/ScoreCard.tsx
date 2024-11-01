interface ScoreCardProps {
  label: string;
  score: number;
  maxScore?: number;
  suffix?: string;
  className?: string;
}

export default function ScoreCard({ label, score, maxScore, suffix = '', className = '' }: ScoreCardProps) {
  return (
    <div className={`p-4 rounded-lg ${className}`}>
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold">
        {score.toFixed(1)}
        {maxScore ? ` / ${maxScore}` : ''}
        {suffix}
      </p>
    </div>
  );
}
