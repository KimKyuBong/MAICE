<script lang="ts">
	import Button from '../common/Button.svelte';
	import { updateResearchConsent } from '$lib/api';
	
	let {
		isOpen = false,
		token = '',
		onAccept = () => {},
		onReject = () => {}
	}: {
		isOpen?: boolean;
		token?: string;
		onAccept?: () => void;
		onReject?: () => void;
	} = $props();
	
	let hasRead = $state(false);
	let scrollContainer: HTMLDivElement | undefined = $state();
	let isProcessing = $state(false);
	
	function handleScroll() {
		if (scrollContainer) {
			const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
			const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10;
			if (isAtBottom) {
				hasRead = true;
			}
		}
	}
	
	async function handleAccept() {
		if (isProcessing) return;
		
		try {
			isProcessing = true;
			
			// DB에 동의 저장
			await updateResearchConsent(token, true, '1.0');
			
			// localStorage에도 표시 (중복 모달 방지)
			if (typeof window !== 'undefined') {
				localStorage.setItem('teacher_research_consent', JSON.stringify({
					consent: true,
					date: new Date().toISOString(),
					version: '1.0'
				}));
			}
			
			onAccept();
		} catch (error) {
			console.error('연구 동의 저장 실패:', error);
			alert('동의 저장에 실패했습니다. 다시 시도해주세요.');
		} finally {
			isProcessing = false;
		}
	}
	
	async function handleReject() {
		if (isProcessing) return;
		
		try {
			isProcessing = true;
			
			// DB에 거부 저장
			await updateResearchConsent(token, false, '1.0');
			
			// localStorage에도 표시
			if (typeof window !== 'undefined') {
				localStorage.setItem('teacher_research_consent', JSON.stringify({
					consent: false,
					date: new Date().toISOString(),
					version: '1.0'
				}));
			}
			
			onReject();
		} catch (error) {
			console.error('연구 거부 저장 실패:', error);
			onReject(); // 에러가 나도 일단 진행
		} finally {
			isProcessing = false;
		}
	}
</script>

{#if isOpen}
	<div class="modal-backdrop" role="dialog" aria-modal="true">
		<div class="modal-content">
			<div class="modal-header">
				<h2>🔬 연구 참여 동의 요청</h2>
			</div>
			
			<div class="modal-body" bind:this={scrollContainer} onscroll={handleScroll}>
				<section>
					<h3>연구 제목</h3>
					<p class="research-title">AI 기반 수학 학습 대화 시스템의 교육적 효과성 검증 연구</p>
				</section>
				
				<section>
					<h3>연구 목적</h3>
					<p>본 연구는 AI를 활용한 수학 학습 대화 시스템이 학생들의 학습에 얼마나 효과적인지 검증하고, 교육 현장에서 AI를 더 잘 활용할 수 있는 방안을 모색하기 위해 수행됩니다.</p>
				</section>
				
				<section>
					<h3>참여 내용</h3>
					<ul>
						<li><strong>세션 채점:</strong> 학생-AI 대화 세션을 v4.3 루브릭으로 평가 (목표: 100개)</li>
						<li><strong>루브릭 검토:</strong> 각 루브릭 항목의 타당성에 대한 의견 제공</li>
						<li><strong>소요 시간:</strong> 세션당 약 3-5분 (총 5-8시간 예상)</li>
					</ul>
				</section>
				
				<section>
					<h3>수집 데이터</h3>
					<ul>
						<li>루브릭 기반 평가 점수 (A1~C2 항목별 점수)</li>
						<li>루브릭 항목에 대한 교사 의견</li>
						<li>평가 메타데이터 (평가 일시, 소요 시간 등)</li>
					</ul>
				</section>
				
				<section>
					<h3>개인정보 보호</h3>
					<ul>
						<li>모든 데이터는 <strong>익명 처리</strong>되어 연구에 활용됩니다</li>
						<li>개인을 식별할 수 있는 정보는 <strong>암호화</strong>되어 저장됩니다</li>
						<li>연구 종료 후 개인정보는 <strong>안전하게 폐기</strong>됩니다</li>
						<li>연구 결과는 학술 논문 및 교육 개선 목적으로만 사용됩니다</li>
					</ul>
				</section>
				
				<section>
					<h3>참여자 권리</h3>
					<ul>
						<li>연구 참여는 <strong>자발적</strong>이며, 언제든지 중단할 수 있습니다</li>
						<li>참여를 거부하거나 중단해도 어떠한 불이익도 없습니다</li>
						<li>연구 데이터 열람 및 삭제를 요청할 수 있습니다</li>
					</ul>
				</section>
				
				<section class="consent-box">
					<p><strong>위 내용을 모두 읽고 이해하였으며, 연구 참여에 동의합니다.</strong></p>
				</section>
				
				{#if !hasRead}
					<div class="scroll-hint">
						⬇️ 모든 내용을 읽으신 후 동의/거부를 선택해주세요
					</div>
				{/if}
			</div>
			
			<div class="modal-footer">
				<Button variant="ghost" onclick={handleReject} disabled={isProcessing}>
					거부
				</Button>
				<Button variant="primary" onclick={handleAccept} disabled={!hasRead || isProcessing}>
					{isProcessing ? '처리 중...' : '동의하고 시작하기'}
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
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 2rem;
	}
	
	.modal-content {
		background: var(--maice-bg-card);
		border-radius: 16px;
		max-width: 700px;
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
		background: var(--maice-bg-secondary);
	}
	
	.modal-header h2 {
		margin: 0;
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}
	
	.modal-body {
		padding: 2rem;
		overflow-y: auto;
		flex: 1;
	}
	
	section {
		margin-bottom: 1.5rem;
	}
	
	h3 {
		margin: 0 0 0.75rem 0;
		font-size: 1rem;
		font-weight: 600;
		color: var(--maice-text-primary);
	}
	
	p {
		margin: 0 0 0.5rem 0;
		line-height: 1.6;
		color: var(--maice-text-secondary);
	}
	
	.research-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--maice-primary);
		padding: 1rem;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
	}
	
	ul {
		margin: 0;
		padding-left: 1.5rem;
	}
	
	li {
		margin-bottom: 0.5rem;
		color: var(--maice-text-secondary);
		line-height: 1.6;
	}
	
	.consent-box {
		padding: 1.5rem;
		background: var(--maice-success-bg-light);
		border: 2px solid var(--maice-success-border);
		border-radius: 12px;
		text-align: center;
	}
	
	.consent-box p {
		margin: 0;
		color: var(--maice-success-text-dark);
		font-weight: 600;
	}
	
	.scroll-hint {
		text-align: center;
		padding: 1rem;
		color: var(--maice-text-muted);
		font-size: 0.875rem;
		animation: bounce 2s infinite;
	}
	
	@keyframes bounce {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-5px); }
	}
	
	.modal-footer {
		padding: 1.5rem 2rem;
		border-top: 1px solid var(--maice-border-primary);
		display: flex;
		justify-content: flex-end;
		gap: 1rem;
		background: var(--maice-bg-secondary);
	}
</style>

