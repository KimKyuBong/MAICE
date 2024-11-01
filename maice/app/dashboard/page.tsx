import { gradingApi } from '@/services/api';
import GradingDashboard from '@/components/GradingDashboard';
import { Suspense } from 'react';
import LoadingSpinner from '@/components/LoadingSpinner';

export default async function DashboardPage() {
  try {
    const students = await gradingApi.getStudents();

    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto py-6 px-4">
            <h1 className="text-3xl font-bold text-gray-900">MAICE 시스템</h1>
          </div>
        </header>
        
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <Suspense fallback={<LoadingSpinner />}>
            <GradingDashboard initialStudents={students} />
          </Suspense>
        </main>
      </div>
    );
  } catch (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <h2 className="text-xl font-bold text-red-600 mb-2">오류 발생</h2>
          <p className="text-gray-600">데이터를 불러오는데 실패했습니다.</p>
        </div>
      </div>
    );
  }
}
