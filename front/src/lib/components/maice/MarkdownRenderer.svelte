<script lang="ts">
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import katex from 'katex';
	import DOMPurify from 'dompurify';
	import 'katex/dist/katex.min.css';
	import '$lib/styles/katex-theme.css';

	// marked 설정 - 마크다운 렌더링 개선
	marked.setOptions({
		breaks: true,
		gfm: true,
		pedantic: false
	});

	interface Props {
		content: string;
		className?: string;
	}

	let { content = '', className = '' }: Props = $props();
	let processedHtml = $state('');
	
	// 성능 최적화를 위한 메모이제이션
	let lastProcessedContent = '';
	let renderTimeout: number | null = null;

	// 컨텐츠 변경 감지 및 렌더링 - 성능 최적화
	function renderContent() {
		if (!content) {
			processedHtml = '';
			lastProcessedContent = '';
			return;
		}
		
		// 메모이제이션: 동일한 컨텐츠는 재렌더링하지 않음
		if (content === lastProcessedContent) {
			// console.log('⚡ 메모이제이션: 동일한 컨텐츠, 렌더링 스킵');
			return;
		}
		
		// 컨텐츠 길이가 크게 변하지 않았다면 디바운싱
		const contentLengthDiff = Math.abs(content.length - (lastProcessedContent?.length || 0));
		if (lastProcessedContent && contentLengthDiff < 10 && !content.includes('##')) {
			// 작은 변화는 디바운싱 (제목이 없는 경우)
			return;
		}
		
		console.log('🔄 컨텐츠 변경 감지, 렌더링 시작');
		// console.log('📝 원본 컨텐츠 길이:', content.length);
		
		// 실시간 렌더링을 위한 최적화
		try {
			const html = processMarkdownSync(content);
			// console.log('✅ 실시간 렌더링 완료, HTML 길이:', html.length);
			
			// 즉시 업데이트
			processedHtml = html;
			lastProcessedContent = content;
			
			// LaTeX 수식 실시간 렌더링 최적화
			requestAnimationFrame(() => {
				if (typeof document !== 'undefined') {
					const katexElements = document.querySelectorAll('.katex');
					katexElements.forEach(element => {
						if (element instanceof HTMLElement) {
							element.style.fontSize = '1.1em';
							// 부드러운 애니메이션 효과
							element.style.opacity = '0';
							element.style.transition = 'opacity 0.3s ease-in-out';
							setTimeout(() => {
								element.style.opacity = '1';
							}, 50);
						}
					});
				}
			});
		} catch (error) {
			console.error('❌ 실시간 렌더링 오류:', error);
			processedHtml = `<div class="render-error" style="color: #cc0000; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 0.5rem;">
				<strong>렌더링 오류:</strong> ${error instanceof Error ? error.message : String(error)}
			</div>`;
		}
	}

	// 컨텐츠 변경 시 재렌더링 - 성능 최적화된 디바운싱
	$effect(() => {
		if (content !== undefined) {
			// 기존 타이머 클리어
			if (renderTimeout) {
				clearTimeout(renderTimeout);
			}
			
			// 디바운싱: 빠른 타이핑 시 불필요한 렌더링 방지
			if (content.length > 0) {
				// 컨텐츠 길이에 따른 적응적 지연
				const delay = content.length > 1000 ? 100 : 50;
				renderTimeout = setTimeout(() => {
					renderContent();
				}, delay);
			} else {
				// 빈 컨텐츠는 즉시 처리
				renderContent();
			}
		}
	});

	// LaTeX 블록과 인라인 수식 처리 - 실시간 최적화
	function processLatex(text: string): string {
		// LaTeX 블록 수식 처리 ($$...$$)
		text = text.replace(/\$\$([\s\S]*?)\$\$/g, (match, latex) => {
			try {
				const rendered = katex.renderToString(latex.trim(), {
					displayMode: true,
					throwOnError: false,
					errorColor: '#cc0000',
					strict: false
				});
				return rendered;
			} catch (error) {
				console.warn('❌ LaTeX 블록 렌더링 오류:', error);
				return `<div class="latex-error" style="color: #cc0000; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 0.5rem;">
					<strong>LaTeX 오류:</strong> ${latex}
				</div>`;
			}
		});

		// LaTeX 인라인 수식 처리 ($...$) - 더 정확한 정규식 사용
		text = text.replace(/\$([^$\n\\]*(?:\\.[^$\n\\]*)*)\$/g, (match, latex) => {
			try {
				const rendered = katex.renderToString(latex.trim(), {
					displayMode: false,
					throwOnError: false,
					errorColor: '#cc0000',
					strict: false
				});
				return rendered;
			} catch (error) {
				console.warn('❌ LaTeX 인라인 렌더링 오류:', error);
				return `<span class="latex-error" style="color: #cc0000; background: #fef2f2; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
					${latex}
				</span>`;
			}
		});

		// 추가 LaTeX 패턴 처리 (백슬래시가 포함된 경우)
		text = text.replace(/\\\(([\s\S]*?)\\\)/g, (match, latex) => {
			try {
				const rendered = katex.renderToString(latex.trim(), {
					displayMode: false,
					throwOnError: false,
					errorColor: '#cc0000',
					strict: false
				});
				return rendered;
			} catch (error) {
				console.warn('❌ 백슬래시 LaTeX 렌더링 오류:', error);
				return `<span class="latex-error" style="color: #cc0000; background: #fef2f2; padding: 0.25rem 0.5rem; border-radius: 0.25rem;">
					${latex}
				</span>`;
			}
		});

		// 백슬래시 블록 LaTeX 처리
		text = text.replace(/\\\[([\s\S]*?)\\\]/g, (match, latex) => {
			try {
				const rendered = katex.renderToString(latex.trim(), {
					displayMode: true,
					throwOnError: false,
					errorColor: '#cc0000',
					strict: false
				});
				return rendered;
			} catch (error) {
				console.warn('❌ 백슬래시 블록 LaTeX 렌더링 오류:', error);
				return `<div class="latex-error" style="color: #cc0000; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 0.5rem;">
					<strong>LaTeX 오류:</strong> ${latex}
				</div>`;
			}
		});

		return text;
	}

	// 마크다운 처리 (LaTeX 처리 후) - marked 라이브러리 활용
	function processMarkdownSync(text: string): string {
		try {
			console.log('🔄 마크다운 처리 시작:', text.substring(0, 100) + '...');
			
			// 이미 렌더링된 HTML LaTeX가 있는지 확인
			if (text.includes('<span class="katex">') || text.includes('<div class="katex-display">')) {
				// 이미 렌더링된 HTML LaTeX가 있으면 마크다운만 처리
				console.log('🔍 이미 렌더링된 HTML LaTeX 감지됨 - 마크다운만 처리');
				
				// marked 라이브러리를 사용하여 마크다운 처리
				let html = marked.parse(text) as string;
				
				// XSS 방지 - LaTeX HTML 태그 허용
				const sanitized = DOMPurify.sanitize(html, {
					ADD_TAGS: ['math', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'msqrt', 'mroot', 'semantics', 'annotation', 'span', 'div'],
					ADD_ATTR: ['xmlns', 'display', 'style', 'aria-hidden', 'encoding', 'class', 'viewBox', 'fill', 'd']
				}) as string;
				
				return sanitized;
			}
			
			// LaTeX를 보호하면서 마크다운 처리
			text = processMarkdownWithLatexProtection(text);
			
			// XSS 방지 - LaTeX HTML 태그 허용
			const sanitized = DOMPurify.sanitize(text, {
				ADD_TAGS: ['math', 'mrow', 'mi', 'mo', 'mn', 'msup', 'msub', 'mfrac', 'msqrt', 'mroot', 'semantics', 'annotation', 'span', 'div'],
				ADD_ATTR: ['xmlns', 'display', 'style', 'aria-hidden', 'encoding', 'class', 'viewBox', 'fill', 'd']
			}) as string;
			
			console.log('✅ 마크다운 처리 완료');
			return sanitized;
		} catch (error) {
			console.error('❌ 마크다운 처리 오류:', error);
			return `<div class="markdown-error" style="color: #cc0000; padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 0.5rem;">
				<strong>마크다운 처리 오류:</strong> ${error instanceof Error ? error.message : String(error)}
			</div>`;
		}
	}

	// LaTeX를 보호하면서 마크다운 처리
	function processMarkdownWithLatexProtection(text: string): string {
		const latexPlaceholders = new Map();
		let counter = 0;
		
		// LaTeX 패턴들을 플레이스홀더로 교체
		const latexPatterns = [
			{ pattern: /\\\[([\s\S]*?)\\\]/g, type: 'display' },
			{ pattern: /\\\(([\s\S]*?)\\\)/g, type: 'inline' },
			{ pattern: /\$\$([\s\S]*?)\$\$/g, type: 'display' },
			{ pattern: /\$([^$\n\\]*(?:\\.[^$\n\\]*)*)\$/g, type: 'inline' }
		];
		
		latexPatterns.forEach(({pattern, type}) => {
			text = text.replace(pattern, (match) => {
				const placeholder = `LATEX_PLACEHOLDER_${counter}_${type}`;
				latexPlaceholders.set(placeholder, match);
				counter++;
				return placeholder;
			});
		});
		
		// marked 라이브러리를 사용하여 마크다운 처리
		let html = marked.parse(text) as string;
		
		// LaTeX 플레이스홀더를 실제 LaTeX로 복원
		latexPlaceholders.forEach((originalLatex, placeholder) => {
			html = html.split(placeholder).join(originalLatex);
		});
		
		// LaTeX 렌더링
		html = processLatex(html);
		
		return html;
	}

	// 기존 async 함수는 유지 (호환성)
	async function processMarkdown(text: string): Promise<string> {
		return processMarkdownSync(text);
	}

	// 복사 이벤트 핸들러 - 드래그한 부분만 원본 텍스트로 복사
	function handleCopy(event: ClipboardEvent) {
		if (!event.clipboardData) return;
		
		const selection = window.getSelection();
		if (!selection || selection.rangeCount === 0 || !selection.toString().trim()) {
			return;
		}

		event.preventDefault();
		
		// 선택된 내용을 간단하게 처리
		let result = '';
		const range = selection.getRangeAt(0);
		const clonedContents = range.cloneContents();
		
		// KaTeX 요소만 찾아서 annotation에서 LaTeX 추출, 나머지는 일반 텍스트로 처리
		const katexElements = clonedContents.querySelectorAll('.katex');
		
		// 선택된 영역의 textContent를 기본으로 시작
		let selectedText = clonedContents.textContent || '';
		
		// KaTeX 요소들을 LaTeX로 교체
		for (const katexElement of katexElements) {
			const annotation = katexElement.querySelector('annotation');
			if (annotation?.textContent) {
				const isDisplayMode = katexElement.classList.contains('katex-display');
				const latexText = isDisplayMode ? `$$${annotation.textContent.trim()}$$` : `$${annotation.textContent.trim()}$`;
				
				// 렌더링된 텍스트를 LaTeX로 교체
				const renderedText = katexElement.textContent || '';
				selectedText = selectedText.replace(renderedText, latexText);
			}
		}
		
		result = selectedText;

		event.clipboardData.setData('text/plain', result);
		console.log('📋 드래그된 부분의 원본 텍스트 복사됨:', result.substring(0, 100));
	}

	let renderedContentElement = $state<HTMLDivElement>();

	onMount(() => {
		console.log('🚀 MarkdownRenderer 마운트됨');
		console.log('📝 초기 컨텐츠:', content);
		
		// 컴포넌트 언마운트 시 타이머 정리 및 이벤트 리스너 제거
		return () => {
			if (renderTimeout) {
				clearTimeout(renderTimeout);
				renderTimeout = null;
			}
		};
	});

	// renderedContentElement가 설정되면 복사 이벤트 리스너 추가
	$effect(() => {
		if (renderedContentElement) {
			renderedContentElement.addEventListener('copy', handleCopy);
			console.log('📋 복사 이벤트 리스너 추가됨');
			
			return () => {
				if (renderedContentElement) {
					renderedContentElement.removeEventListener('copy', handleCopy);
				}
			};
		}
	});
</script>

<div 
	class="markdown-content {className}"
>
	{#if !content}
		<div class="empty-content text-maice-text-muted text-center py-8">
			내용이 없습니다.
		</div>
	{:else if !processedHtml}
		<div class="loading-content text-maice-text-muted text-center py-8">
			렌더링 중... ⏳
		</div>
	{:else}
		<div class="rendered-content" bind:this={renderedContentElement}>
			{@html processedHtml}
		</div>
	{/if}
</div>

<style>
	.markdown-content {
		line-height: 1.7;
		color: var(--maice-text-primary);
		font-size: var(--maice-text-base-size, 1.1rem);
		transition: all 0.2s ease-in-out;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
	}

	/* 실시간 렌더링을 위한 부드러운 애니메이션 */
	.rendered-content {
		animation: fadeIn 0.3s ease-in-out;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(5px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* 마크다운 요소 스타일링 - 테마 시스템과 통합 */
	.markdown-content :global(h1) {
		font-size: 1.8rem !important;
		font-weight: 700 !important;
		margin: 1.5rem 0 1rem 0 !important;
		color: var(--maice-text-primary) !important;
		border-bottom: 2px solid var(--maice-border-primary) !important;
		padding-bottom: 0.5rem !important;
		line-height: 1.3 !important;
	}

	.markdown-content :global(h2) {
		font-size: 1.5rem !important;
		font-weight: 600 !important;
		margin: 1.25rem 0 0.75rem 0 !important;
		color: var(--maice-text-primary) !important;
		line-height: 1.4 !important;
	}

	.markdown-content :global(h3) {
		font-size: 1.25rem !important;
		font-weight: 600 !important;
		margin: 1rem 0 0.5rem 0 !important;
		color: var(--maice-text-primary) !important;
		line-height: 1.4 !important;
	}

	.markdown-content :global(p) {
		margin: 0.75rem 0 !important;
		line-height: 1.7 !important;
		color: var(--maice-text-primary) !important;
	}

	.markdown-content :global(strong) {
		font-weight: 700 !important;
		color: var(--maice-text-primary) !important;
	}

	.markdown-content :global(em) {
		font-style: italic !important;
		color: var(--maice-text-secondary) !important;
		font-weight: 500 !important;
	}

	.markdown-content :global(code) {
		background-color: var(--maice-bg-secondary) !important;
		color: var(--maice-primary) !important;
		padding: 0.125rem 0.375rem !important;
		border-radius: 0.25rem !important;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
		font-size: 0.875em !important;
		border: 1px solid var(--maice-border-primary) !important;
		font-weight: 500 !important;
	}

	.markdown-content :global(pre) {
		background-color: var(--maice-bg-secondary) !important;
		border: 1px solid var(--maice-border-primary) !important;
		border-radius: 0.5rem !important;
		padding: 1rem !important;
		margin: 1rem 0 !important;
		overflow-x: auto !important;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
		font-size: 0.875rem !important;
		line-height: 1.5 !important;
	}

	.markdown-content :global(pre code) {
		background: none !important;
		border: none !important;
		padding: 0 !important;
		color: var(--maice-text-primary) !important;
	}

	.markdown-content :global(ul) {
		margin: 0.75rem 0 !important;
		padding-left: 1.5rem !important;
	}

	.markdown-content :global(ol) {
		margin: 0.75rem 0 !important;
		padding-left: 1.5rem !important;
	}

	.markdown-content :global(li) {
		margin: 0.25rem 0 !important;
		line-height: 1.6 !important;
		color: var(--maice-text-primary) !important;
	}

	.markdown-content :global(blockquote) {
		border-left: 4px solid var(--maice-primary) !important;
		background-color: var(--maice-bg-secondary) !important;
		margin: 1rem 0 !important;
		padding: 0.75rem 1rem !important;
		border-radius: 0 0.375rem 0.375rem 0 !important;
		font-style: italic !important;
		color: var(--maice-text-secondary) !important;
	}

	.markdown-content :global(a) {
		color: var(--maice-primary) !important;
		text-decoration: underline !important;
		text-decoration-color: transparent !important;
		transition: text-decoration-color 0.2s ease !important;
	}

	.markdown-content :global(a:hover) {
		text-decoration-color: var(--maice-primary) !important;
	}

	.markdown-content :global(hr) {
		border: none !important;
		border-top: 1px solid var(--maice-border-primary) !important;
		margin: 1.5rem 0 !important;
	}

	/* 취소선 스타일 */
	.markdown-content :global(del),
	.markdown-content :global(s) {
		text-decoration: line-through !important;
		color: var(--maice-text-secondary) !important;
		opacity: 0.7 !important;
	}

	/* 하위 제목 스타일 */
	.markdown-content :global(h4) {
		font-size: 1.1rem !important;
		font-weight: 600 !important;
		margin: 0.875rem 0 0.5rem 0 !important;
		color: var(--maice-text-primary) !important;
		line-height: 1.5 !important;
	}

	.markdown-content :global(h5) {
		font-size: 1rem !important;
		font-weight: 600 !important;
		margin: 0.75rem 0 0.5rem 0 !important;
		color: var(--maice-text-primary) !important;
		line-height: 1.5 !important;
	}

	.markdown-content :global(h6) {
		font-size: 0.9rem !important;
		font-weight: 600 !important;
		margin: 0.75rem 0 0.5rem 0 !important;
		color: var(--maice-text-secondary) !important;
		line-height: 1.5 !important;
	}

	/* 이미지 스타일 */
	.markdown-content :global(img) {
		max-width: 100% !important;
		height: auto !important;
		border-radius: 0.5rem !important;
		margin: 1rem 0 !important;
		border: 1px solid var(--maice-border-primary) !important;
		display: block !important;
	}

	/* 테이블 스타일 */
	.markdown-content :global(table) {
		width: 100% !important;
		border-collapse: collapse !important;
		margin: 1rem 0 !important;
		border: 1px solid var(--maice-border-primary) !important;
		border-radius: 0.5rem !important;
		overflow: hidden !important;
	}

	.markdown-content :global(thead) {
		background-color: var(--maice-bg-secondary) !important;
	}

	.markdown-content :global(th) {
		padding: 0.75rem 1rem !important;
		text-align: left !important;
		font-weight: 600 !important;
		color: var(--maice-text-primary) !important;
		border-bottom: 2px solid var(--maice-border-primary) !important;
	}

	.markdown-content :global(td) {
		padding: 0.75rem 1rem !important;
		border-bottom: 1px solid var(--maice-border-primary) !important;
		color: var(--maice-text-primary) !important;
	}

	.markdown-content :global(tbody tr:hover) {
		background-color: var(--maice-bg-secondary) !important;
	}

	/* LaTeX 수식 스타일링 - 테마 시스템과 통합 */
	.markdown-content :global(.katex) {
		font-size: 1.1em !important;
		color: var(--maice-text-primary) !important;
		background: transparent !important;
		border: none !important;
		padding: 0 !important;
		/* 렌더링된 수식은 편집 불가능하도록 설정 */
		user-select: none !important;
		pointer-events: none !important;
		-moz-user-select: none !important;
		-webkit-user-select: none !important;
		-ms-user-select: none !important;
	}

	.markdown-content :global(.katex-display) {
		margin: 1rem 0 !important;
		text-align: center !important;
		background: var(--maice-bg-card) !important;
		border: 1px solid var(--maice-border-primary) !important;
		border-radius: 0.5rem !important;
		padding: 1rem !important;
		color: var(--maice-text-primary) !important;
	}

	/* 인라인 LaTeX 수식 */
	.markdown-content :global(.katex:not(.katex-display)) {
		background: var(--maice-bg-card) !important;
		border: 1px solid var(--maice-border-primary) !important;
		border-radius: 0.25rem !important;
		padding: 0.125rem 0.375rem !important;
		margin: 0 0.125rem !important;
		color: var(--maice-text-primary) !important;
		vertical-align: middle !important;
		display: inline-block !important;
	}

	/* 다크 테마에서 수식 배경색 개선 */
	:global(.dark) .markdown-content :global(.katex-display) {
		background: rgba(31, 41, 55, 0.6) !important;
		border: 1px solid rgba(75, 85, 99, 0.3) !important;
		backdrop-filter: blur(8px) !important;
	}

	:global(.dark) .markdown-content :global(.katex:not(.katex-display)) {
		background: rgba(31, 41, 55, 0.4) !important;
		border: 1px solid rgba(75, 85, 99, 0.2) !important;
		backdrop-filter: blur(4px) !important;
	}

	/* LaTeX 수식 애니메이션 */
	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateX(-10px);
		}
		to {
			opacity: 1;
			transform: translateX(0);
		}
	}

	/* 반응형 디자인 - 모바일 최적화 */
	@media (max-width: 768px) {
		.markdown-content {
			font-size: 1.2rem !important;
		}
		
		.markdown-content :global(h1) {
			font-size: 1.6rem !important;
		}
		
		.markdown-content :global(h2) {
			font-size: 1.4rem !important;
		}
		
		.markdown-content :global(h3) {
			font-size: 1.2rem !important;
		}
	}

	/* 매우 작은 화면 (스마트폰) */
	@media (max-width: 480px) {
		.markdown-content {
			font-size: 1.3rem !important;
		}
		
		.markdown-content :global(pre) {
			padding: 0.75rem !important;
			font-size: 0.8rem !important;
		}
	}
</style>