<script lang="ts">
	import Button from '../common/Button.svelte';
	
	let {
		isOpen = false,
		onClose = () => {}
	}: {
		isOpen?: boolean;
		onClose?: () => void;
	} = $props();
	
	function handleClose() {
		// 안내를 읽었다는 표시
		if (typeof window !== 'undefined') {
			localStorage.setItem('teacher_guide_read', 'true');
		}
		onClose();
	}
	
	function handleBackdropClick(event: MouseEvent) {
		if ((event.target as HTMLElement).classList.contains('modal-backdrop')) {
			handleClose();
		}
	}
</script>

{#if isOpen}
	<div class="modal-backdrop" onclick={handleBackdropClick} role="dialog" aria-modal="true">
		<div class="modal-content">
			<div class="modal-header">
				<h2>👨‍🏫 교사 평가자 안내</h2>
				<button class="close-btn" onclick={handleClose}>×</button>
			</div>
			
			<div class="modal-body">
				<section class="intro-section">
					<h3>🎯 연구 목적</h3>
					<p>이 평가는 <strong>AI 기반 수학 학습 대화 시스템의 교육적 효과성</strong>을 검증하기 위한 것입니다.</p>
					<p>선생님께서 제공해주신 평가 데이터는 AI 시스템 개선과 교육 연구에 활용됩니다.</p>
				</section>
				
				<section class="task-section">
					<h3>📋 평가 과제</h3>
					<div class="task-box">
						<div class="task-item">
							<span class="task-icon">1️⃣</span>
							<div>
								<strong>세션 채점 (목표: 100개)</strong>
								<p>v4.3 루브릭을 사용하여 학생-AI 대화 세션을 평가합니다.</p>
							</div>
						</div>
						<div class="task-item">
							<span class="task-icon">2️⃣</span>
							<div>
								<strong>루브릭 검토</strong>
								<p>각 루브릭 항목의 타당성과 개선점에 대한 의견을 작성합니다.</p>
							</div>
						</div>
					</div>
				</section>
				
				<section class="rubric-section">
					<h3>📊 v4.3 루브릭 구조</h3>
					<div class="rubric-overview">
						<div class="rubric-category">
							<div class="category-header">A. 질문 영역 (15점)</div>
							<ul>
								<li><strong>A1. 수학적 전문성</strong> - 개념 정확성, 용어 사용, 위계성</li>
								<li><strong>A2. 질문 구조화</strong> - 논리적 연계, 선행 지식, 목표 명시</li>
								<li><strong>A3. 학습 맥락 적용</strong> - 단원 식별, 교육과정 반영</li>
							</ul>
						</div>
						<div class="rubric-category">
							<div class="category-header">B. 응답 영역 (15점)</div>
							<ul>
								<li><strong>B1. 학습자 맞춤도</strong> - 쉬운 설명, 수준 반영</li>
								<li><strong>B2. 설명의 체계성</strong> - 논리적 구조, 단계별 확인</li>
								<li><strong>B3. 학습 내용 확장성</strong> - 확장 활동, 개념 연계</li>
							</ul>
						</div>
						<div class="rubric-category">
							<div class="category-header">C. 맥락 영역 (10점)</div>
							<ul>
								<li><strong>C1. 대화 일관성</strong> - 문맥 유지, 이전 대화 참조</li>
								<li><strong>C2. 학습 과정 지원성</strong> - 동기 지원, 긍정적 피드백</li>
							</ul>
						</div>
					</div>
					<div class="rubric-note">
						<strong>채점 방식:</strong> 각 항목은 4개 체크리스트로 구성되며, 체크된 개수 + 1점으로 계산됩니다 (1~5점)
					</div>
				</section>
				
				<section class="workflow-section">
					<h3>🔄 평가 워크플로우</h3>
					<div class="workflow-steps">
						<div class="step">
							<span class="step-num">1</span>
							<div class="step-content">
								<strong>세션 채점</strong>
								<p>• 랜덤으로 제시되는 세션의 대화 내용 검토</p>
								<p>• 각 루브릭 항목의 체크리스트 평가</p>
								<p>• 자동으로 다음 세션 로드 (100개 목표)</p>
							</div>
						</div>
						<div class="step">
							<span class="step-num">2</span>
							<div class="step-content">
								<strong>루브릭 평가</strong>
								<p>• 항목별로 세션을 필터링하여 검토</p>
								<p>• 각 루브릭 항목의 타당성에 대한 의견 작성</p>
								<p>• 개선이 필요한 부분 제안</p>
							</div>
						</div>
					</div>
				</section>
				
				<section class="note-section">
					<h3>⚠️ 유의사항</h3>
					<ul class="note-list">
						<li>평가 데이터는 연구 목적으로만 사용되며 익명 처리됩니다</li>
						<li>세션 채점은 체크리스트 방식으로 간편하게 진행됩니다</li>
						<li>건너뛰기 기능으로 평가하기 어려운 세션은 넘길 수 있습니다</li>
						<li>진행 상황은 실시간으로 확인 가능합니다</li>
					</ul>
				</section>
			</div>
			
			<div class="modal-footer">
				<Button variant="primary" onclick={handleClose}>
					시작하기
				</Button>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 2rem;
	}
	
	.modal-content {
		background: var(--maice-bg-card);
		border-radius: 16px;
		max-width: 800px;
		width: 100%;
		max-height: 90vh;
		overflow: hidden;
		box-shadow: var(--maice-shadow-xl);
		display: flex;
		flex-direction: column;
	}
	
	.modal-header {
		padding: 1.5rem 2rem;
		border-bottom: 2px solid var(--maice-border-primary);
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: var(--maice-bg-secondary);
	}
	
	.modal-header h2 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}
	
	.close-btn {
		background: none;
		border: none;
		font-size: 2rem;
		cursor: pointer;
		color: var(--maice-text-muted);
		line-height: 1;
		padding: 0;
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		transition: all 0.2s;
	}
	
	.close-btn:hover {
		background: var(--maice-bg-hover);
		color: var(--maice-text-primary);
	}
	
	.modal-body {
		padding: 2rem;
		overflow-y: auto;
		flex: 1;
	}
	
	section {
		margin-bottom: 2rem;
	}
	
	section:last-child {
		margin-bottom: 0;
	}
	
	h3 {
		margin: 0 0 1rem 0;
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}
	
	p {
		margin: 0 0 0.75rem 0;
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}
	
	.intro-section {
		padding: 1.5rem;
		background: var(--maice-bg-secondary);
		border-radius: 12px;
		border-left: 4px solid var(--maice-primary);
	}
	
	.task-box {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	
	.task-item {
		display: flex;
		gap: 1rem;
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
	}
	
	.task-icon {
		font-size: 1.5rem;
		flex-shrink: 0;
	}
	
	.task-item strong {
		display: block;
		margin-bottom: 0.25rem;
		color: var(--maice-text-primary);
	}
	
	.task-item p {
		margin: 0;
		font-size: 0.9375rem;
		color: var(--maice-text-muted);
	}
	
	.rubric-overview {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	
	.rubric-category {
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
		border-left: 3px solid var(--maice-primary);
	}
	
	.category-header {
		font-weight: 600;
		font-size: 1rem;
		margin-bottom: 0.75rem;
		color: var(--maice-text-primary);
	}
	
	.rubric-category ul {
		margin: 0;
		padding-left: 1.5rem;
	}
	
	.rubric-category li {
		margin-bottom: 0.5rem;
		color: var(--maice-text-secondary);
		line-height: 1.5;
	}
	
	.rubric-note {
		margin-top: 1rem;
		padding: 1rem;
		background: var(--maice-warning-bg);
		color: var(--maice-warning-text);
		border-radius: 8px;
		font-size: 0.9375rem;
	}
	
	.workflow-steps {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}
	
	.step {
		display: flex;
		gap: 1rem;
	}
	
	.step-num {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 40px;
		height: 40px;
		background: var(--maice-primary);
		color: white;
		border-radius: 50%;
		font-weight: 600;
		font-size: 1.125rem;
		flex-shrink: 0;
	}
	
	.step-content {
		flex: 1;
	}
	
	.step-content strong {
		display: block;
		margin-bottom: 0.5rem;
		font-size: 1rem;
		color: var(--maice-text-primary);
	}
	
	.step-content p {
		margin: 0.25rem 0;
		font-size: 0.9375rem;
		color: var(--maice-text-secondary);
	}
	
	.note-list {
		margin: 0;
		padding-left: 1.5rem;
	}
	
	.note-list li {
		margin-bottom: 0.5rem;
		color: var(--maice-text-secondary);
		line-height: 1.6;
	}
	
	.modal-footer {
		padding: 1.5rem 2rem;
		border-top: 1px solid var(--maice-border-primary);
		display: flex;
		justify-content: flex-end;
		background: var(--maice-bg-secondary);
	}
</style>

