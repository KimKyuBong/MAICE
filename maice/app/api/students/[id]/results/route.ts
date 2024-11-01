import { NextRequest, NextResponse } from 'next/server';
import { gradingApi } from '@/services/api';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const studentId = (await params).id;
    const data = await gradingApi.getStudentResults(studentId);
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching student results:', error);
    return NextResponse.json(
      { error: 'Failed to fetch student results' },
      { status: 500 }
    );
  }
}
