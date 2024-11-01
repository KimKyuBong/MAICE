'use client';

import { useEffect, useState } from 'react';
import { StudentResults } from '@/types/models';
import LoadingSpinner from './LoadingSpinner';
import GradingResults from './GradingResults';

interface GradingResultsClientProps {
  studentId: string;
}

export default function GradingResultsClient({ studentId }: GradingResultsClientProps) {
  const [state, setState] = useState<{
    data: StudentResults | null;
    loading: boolean;
    error: string | null;
  }>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let mounted = true;

    const fetchResults = async () => {
      try {
        const response = await fetch(`/api/students/${studentId}/results`);
        if (!response.ok) throw new Error('Failed to fetch data');
        
        const data = await response.json();
        if (mounted) {
          setState({
            data,
            loading: false,
            error: null
          });
        }
      } catch (error) {
        if (mounted) {
          setState(prev => ({
            ...prev,
            error: '결과를 불러오는데 실패했습니다.',
            loading: false
          }));
        }
      }
    };

    setState(prev => ({ ...prev, loading: true }));
    fetchResults();

    return () => {
      mounted = false;
    };
  }, [studentId]);

  if (state.loading) {
    return <LoadingSpinner />;
  }

  if (state.error || !state.data) {
    return (
      <div className="p-4 bg-red-50 text-red-500 rounded-lg">
        {state.error || '데이터가 없습니다.'}
      </div>
    );
  }

  return <GradingResults initialData={state.data} />;
}
