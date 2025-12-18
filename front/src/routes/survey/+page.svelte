<script lang="ts">
	import { onMount } from 'svelte';
	
	let surveyData = {
		studentName: '',
		grade: '',
		subject: '',
		questions: [
			{
				id: 1,
				question: 'AI 응답이 학습에 도움이 되었나요?',
				options: ['매우 도움됨', '도움됨', '보통', '도움 안됨', '전혀 도움 안됨']
			},
			{
				id: 2,
				question: 'AI 응답의 정확성은 어느 정도인가요?',
				options: ['매우 정확함', '정확함', '보통', '부정확함', '매우 부정확함']
			},
			{
				id: 3,
				question: 'AI 응답의 이해하기 쉬운 정도는?',
				options: ['매우 쉬움', '쉬움', '보통', '어려움', '매우 어려움']
			}
		],
		answers: {} as Record<number, string>
	};
	
	let currentStep = 0;
	let isComplete = false;
	
	onMount(() => {
		// URL 파라미터에서 학생 정보 가져오기
		const urlParams = new URLSearchParams(window.location.search);
		surveyData.studentName = urlParams.get('name') || '';
		surveyData.grade = urlParams.get('grade') || '';
		surveyData.subject = urlParams.get('subject') || '';
	});
	
	function nextStep() {
		if (currentStep < surveyData.questions.length - 1) {
			currentStep++;
		}
	}
	
	function prevStep() {
		if (currentStep > 0) {
			currentStep--;
		}
	}
	
	function selectAnswer(questionId: number, answer: string) {
		surveyData.answers[questionId] = answer;
	}
	
	function submitSurvey() {
		// 실제로는 API로 데이터 전송
		console.log('설문조사 제출:', surveyData);
		isComplete = true;
	}
	
	function isQuestionAnswered(questionId: number) {
		return surveyData.answers[questionId] !== undefined;
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-green-50 to-blue-50">
	<div class="max-w-4xl mx-auto py-8 px-4">
		{#if !isComplete}
			<!-- 헤더 -->
			<div class="text-center mb-8">
				<h1 class="text-4xl font-bold text-gray-800 mb-4">학습 설문조사</h1>
				<p class="text-xl text-gray-600">AI 학습 도우미 사용 경험을 평가해주세요</p>
			</div>
			
			<!-- 진행률 바 -->
			<div class="bg-white rounded-xl shadow-lg p-6 mb-8">
				<div class="mb-4">
					<div class="flex justify-between text-sm text-gray-600 mb-2">
						<span>진행률</span>
						<span>{Math.round(((currentStep + 1) / surveyData.questions.length) * 100)}%</span>
					</div>
					<div class="w-full bg-gray-200 rounded-full h-2">
						<div 
							class="bg-gradient-to-r from-blue-500 to-green-500 h-2 rounded-full transition-all duration-300"
							style="width: {((currentStep + 1) / surveyData.questions.length) * 100}%"
						></div>
					</div>
				</div>
				
				<!-- 학생 정보 -->
				<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
					<div class="bg-blue-50 p-4 rounded-lg">
						<p class="text-sm text-blue-600 font-medium">학생명</p>
						<p class="text-lg font-semibold text-blue-800">{surveyData.studentName || '미입력'}</p>
					</div>
					<div class="bg-green-50 p-4 rounded-lg">
						<p class="text-sm text-green-600 font-medium">학년</p>
						<p class="text-lg font-semibold text-green-800">{surveyData.grade || '미입력'}</p>
					</div>
					<div class="bg-purple-50 p-4 rounded-lg">
						<p class="text-sm text-purple-600 font-medium">과목</p>
						<p class="text-lg font-semibold text-purple-800">{surveyData.subject || '미입력'}</p>
					</div>
				</div>
			</div>
			
			<!-- 질문 -->
			<div class="bg-white rounded-xl shadow-lg p-8">
				<div class="text-center mb-8">
					<h2 class="text-2xl font-semibold text-gray-800 mb-2">
						질문 {currentStep + 1} / {surveyData.questions.length}
					</h2>
					<p class="text-lg text-gray-600">{surveyData.questions[currentStep].question}</p>
				</div>
				
				<!-- 답변 옵션 -->
				<div class="space-y-3 mb-8">
					{#each surveyData.questions[currentStep].options as option, index}
						<label class="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors duration-200 {surveyData.answers[surveyData.questions[currentStep].id] === option ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}">
							<input
								type="radio"
								name="question-{surveyData.questions[currentStep].id}"
								value={option}
								on:change={() => selectAnswer(surveyData.questions[currentStep].id, option)}
								class="sr-only"
							/>
							<div class="w-5 h-5 border-2 rounded-full mr-3 flex items-center justify-center {surveyData.answers[surveyData.questions[currentStep].id] === option ? 'border-blue-500' : 'border-gray-300'}">
								{#if surveyData.answers[surveyData.questions[currentStep].id] === option}
									<div class="w-3 h-3 bg-blue-500 rounded-full"></div>
								{/if}
							</div>
							<span class="text-gray-800 font-medium">{option}</span>
						</label>
					{/each}
				</div>
				
				<!-- 네비게이션 버튼 -->
				<div class="flex justify-between">
					<button
						on:click={prevStep}
						disabled={currentStep === 0}
						class="px-6 py-3 bg-gray-500 text-white font-semibold rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
					>
						← 이전
					</button>
					
					{#if currentStep === surveyData.questions.length - 1}
						<button
							on:click={submitSurvey}
							disabled={!isQuestionAnswered(surveyData.questions[currentStep].id)}
							class="px-8 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
						>
							설문조사 제출
						</button>
					{:else}
						<button
							on:click={nextStep}
							disabled={!isQuestionAnswered(surveyData.questions[currentStep].id)}
							class="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
						>
							다음 →
						</button>
					{/if}
				</div>
			</div>
		{:else}
			<!-- 완료 페이지 -->
			<div class="text-center">
				<div class="bg-white rounded-xl shadow-lg p-12 max-w-2xl mx-auto">
					<div class="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
						<svg class="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
						</svg>
					</div>
					
					<h1 class="text-3xl font-bold text-gray-800 mb-4">설문조사 완료!</h1>
					<p class="text-lg text-gray-600 mb-8">
						소중한 피드백을 제공해주셔서 감사합니다.<br>
						여러분의 의견은 AI 교육 시스템 개선에 큰 도움이 됩니다.
					</p>
					
					<div class="space-y-4">
						<a
							href="/"
							class="inline-block px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors duration-200"
						>
							메인 페이지로 돌아가기
						</a>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
