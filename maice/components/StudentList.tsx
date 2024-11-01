'use client';

import { useState } from 'react';
import { UserIcon } from '@heroicons/react/24/outline';
import { Student } from '@/types/models';

interface StudentListProps {
  initialStudents: Student[];
  onSelectStudent: (studentId: string) => void;
  selectedStudent: string | null;
}

export default function StudentList({ initialStudents, onSelectStudent, selectedStudent }: StudentListProps) {
  const [students] = useState<Student[]>(initialStudents);

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">학생 목록</h2>
      </div>
      {students.length === 0 ? (
        <div className="p-4 text-center text-gray-500">
          등록된 학생이 없습니다
        </div>
      ) : (
        <ul className="divide-y divide-gray-200">
          {students.map((student) => (
            <li
              key={student.id}
              className={`p-4 hover:bg-gray-50 cursor-pointer ${
                selectedStudent === student.id ? 'bg-blue-50' : ''
              }`}
              onClick={() => onSelectStudent(student.id)}
            >
              <div className="flex items-center space-x-3">
                <UserIcon className="h-6 w-6 text-gray-400" />
                <span className="text-gray-900">학생 {student.id}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
