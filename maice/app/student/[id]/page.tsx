import { gradingApi } from '@/services/api';
import GradingResults from '@/components/GradingResults';
import { Suspense } from 'react';
import LoadingSpinner from '@/components/LoadingSpinner';

interface PageProps {
  params: {
    id: string;
  };
}

async function getStudentResults(studentId: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_APP_URL}/api/students/${studentId}/results`, {
    cache: 'no-store'  // 또는 필요에 따라 revalidate 설정
  });
  
  if (!res.ok) {
    throw new Error('Failed to fetch data');
  }
  
  return res.json();
}

export default async function StudentPage({ params }: PageProps) {
  const initialData = await getStudentResults(params.id);

  return (
    <div className="container mx-auto py-8">
      <Suspense fallback={<LoadingSpinner />}>
        <GradingResults initialData={initialData} />
      </Suspense>
    </div>
  );
}
