// Mock API - 백엔드가 없을 때 테스트용
import type { StudentInfo, AIResponse, ChatSession } from './api';

// Mock 응답 데이터
const mockStudentInfo: StudentInfo = {
	token: 'test-token-123',
	name: '테스트 학생',
	grade: '고등학교 2학년',
	subject: '수학',
	questionCount: 0,
	maxQuestions: 10,
	remainingQuestions: 10
};

const mockChatSessions: ChatSession[] = [
	{
		id: 1,
		title: '수학 학습 세션',
		createdAt: new Date().toISOString(),
		questionCount: 3,
		lastActivity: new Date().toISOString()
	},
	{
		id: 2,
		title: '새로운 학습 세션',
		createdAt: new Date(Date.now() - 86400000).toISOString(), // 1일 전
		questionCount: 0,
		lastActivity: new Date(Date.now() - 86400000).toISOString()
	}
];

const mockSystemStatus = {
	status: 'healthy',
	activeStudents: 15,
	totalQuestions: 127,
	agentStatus: 'online',
	lastUpdate: new Date().toISOString()
};

// Mock 응답 생성 함수
export function getMockResponse(apiType: string, params?: any): any {
	switch (apiType) {
		case 'verifyToken':
			return { ...mockStudentInfo, token: params.token };
		
		case 'submitQuestion':
			const question = params.question || '질문';
			const answer = generateMockAnswer(question);
			return {
				answer,
				session_id: params.sessionId || 1,
				timestamp: new Date().toISOString()
			};
		
		case 'getChatSessions':
			return mockChatSessions;
		
		case 'createNewSession':
			return {
				id: Date.now(),
				title: '새로운 학습 세션',
				createdAt: new Date().toISOString(),
				questionCount: 0,
				lastActivity: new Date().toISOString()
			};
		
		case 'updateStudentInfo':
			return { ...mockStudentInfo, ...params.updates };
		
		case 'getSystemStatus':
			return mockSystemStatus;
		
		default:
			return null;
	}
}

// Mock 답변 생성
function generateMockAnswer(question: string): string {
	const responses = {
		"수학": [
			"수학은 논리적 사고를 기르는 중요한 학문입니다. 미분은 함수의 변화율을 나타내며, 적분은 면적을 계산하는 데 사용됩니다.",
			"수학에서 가장 중요한 것은 개념을 이해하는 것입니다. 공식을 외우기보다는 왜 그런 공식이 나왔는지 생각해보세요.",
			"수학 문제를 풀 때는 단계별로 접근하는 것이 좋습니다. 먼저 문제를 이해하고, 관련된 공식이나 개념을 떠올린 후, 체계적으로 풀어나가세요."
		],
		"영어": [
			"영어는 국제 언어로, 의사소통의 도구입니다. 문법을 이해하면서 실제 대화에서 사용해보는 것이 중요합니다.",
			"영어 학습의 핵심은 반복 연습입니다. 매일 조금씩이라도 영어로 읽고, 쓰고, 말해보세요.",
			"영어 시제는 시간을 나타내는 중요한 요소입니다. 현재, 과거, 미래를 명확히 구분하여 사용하세요."
		],
		"과학": [
			"과학은 자연 현상을 이해하고 설명하는 학문입니다. 관찰, 가설, 실험, 결론의 과정을 통해 진리를 탐구합니다.",
			"과학 실험에서 변인 통제는 매우 중요합니다. 독립변인, 종속변인, 통제변인을 명확히 구분하여 실험을 설계하세요.",
			"과학적 사고는 의심과 검증을 통해 발전합니다. 기존 이론을 맹신하지 말고, 항상 새로운 관점에서 생각해보세요."
		]
	};

	// 질문 내용에 따라 적절한 응답 선택
	if (question.includes('미분') || question.includes('적분')) {
		return "미분과 적분은 수학의 핵심 개념입니다. 미분은 순간변화율을, 적분은 누적값을 구하는 연산입니다. 구체적인 예시를 들어 설명하면...";
	}
	
	if (question.includes('시제') || question.includes('문법')) {
		return "영어 시제는 시간을 나타내는 중요한 문법 요소입니다. 현재시제, 과거시제, 미래시제를 구분하여 사용해야 합니다...";
	}
	
	if (question.includes('실험') || question.includes('변인')) {
		return "과학 실험에서 변인 통제는 정확한 결과를 얻기 위해 필수적입니다. 독립변인, 종속변인, 통제변인을 명확히 구분하여...";
	}
	
	// 기본 응답
	const allResponses = Object.values(responses).flat();
	return allResponses[Math.floor(Math.random() * allResponses.length)];
}

// 스트리밍 응답 시뮬레이션
export function simulateStreamingResponse(
	question: string,
	onChunk?: (chunk: string) => void
): Promise<AIResponse> {
	return new Promise((resolve) => {
		const answer = generateMockAnswer(question);
		const words = answer.split(' ');
		let index = 0;
		
		const interval = setInterval(() => {
			if (index < words.length) {
				if (onChunk) {
					onChunk(words[index] + ' ');
				}
				index++;
			} else {
				clearInterval(interval);
				resolve({
					answer,
					session_id: 1,
					timestamp: new Date().toISOString()
				});
			}
		}, 100);
	});
}

// Mock 세션 생성
export function generateMockSession(): ChatSession {
	return {
		id: Date.now(),
		title: `세션 ${new Date().toLocaleString()}`,
		createdAt: new Date().toISOString(),
		questionCount: 0,
		lastActivity: new Date().toISOString()
	};
}

// Mock 질문 생성
export function generateMockQuestion(): any {
	const subjects = ['수학', '영어', '과학'];
	const questions = [
		'미분이란 무엇인가요?',
		'영어 시제는 어떻게 구분하나요?',
		'과학 실험에서 변인 통제는 왜 중요한가요?'
	];
	
	return {
		id: Date.now(),
		question: questions[Math.floor(Math.random() * questions.length)],
		student: '테스트 학생',
		time: '방금 전',
		status: 'answered'
	};
}
