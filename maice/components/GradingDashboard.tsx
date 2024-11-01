'use client';

import { useState } from 'react';
import StudentList from '@/components/StudentList';
import GradingResultsClient from '@/components/GradingResultsClient';
import SubmissionForm from '@/components/SubmissionForm';
import { Student } from '@/types/models';

interface GradingDashboardProps {
  initialStudents: Student[];
}

export default function GradingDashboard({ initialStudents }: GradingDashboardProps) {
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
      <div className="md:col-span-3">
        <StudentList 
          initialStudents={initialStudents}
          onSelectStudent={setSelectedStudent}
          selectedStudent={selectedStudent}
        />
      </div>
      <div className="md:col-span-9">
        {selectedStudent ? (
          <GradingResultsClient studentId={selectedStudent} />
        ) : (
          <div className="text-center text-gray-500 p-8 bg-white rounded-lg shadow">
            학생을 선택해주세요
          </div>
        )}
        {selectedStudent && <SubmissionForm studentId={selectedStudent} />}
      </div>
    </div>
  );
}