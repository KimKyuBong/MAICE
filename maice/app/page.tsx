import { Suspense } from 'react';
import { gradingApi } from '@/services/api';
import GradingDashboard from '@/components/GradingDashboard';
import LoadingSpinner from '@/components/LoadingSpinner';

export default async function Home() {
  const students = await gradingApi.getStudents();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">수학 채점 시스템</h1>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Suspense fallback={<LoadingSpinner />}>
          <GradingDashboard initialStudents={students} />
        </Suspense>
      </main>
    </div>
  );
}
