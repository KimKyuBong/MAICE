<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import "mathlive";
	import type { MathfieldElement } from "mathlive";

	let {
		placeholder = '메시지를 입력하세요...',
		disabled = false,
		isLoading = false,
		value = $bindable('')
	}: {
		placeholder?: string;
		disabled?: boolean;
		isLoading?: boolean;
		value?: string;
	} = $props();

	// State 변수들
	let editableElement: HTMLDivElement;
	let mathCounter = $state(0); // 각 수식에 고유 ID 부여
	let isUpdating = $state(false); // 업데이트 중 플래그
	let isMathFieldFocused = $state(false); // 수식 필드에 포커스가 있는지 여부
	let currentMathField: any = null; // 현재 포커스된 MathField
	let isTransitioning = $state(false); // 포커스 전환 중 플래그
	let focusDebounceTimer: any = null; // 포커스 디바운스 타이머
	let lastFocusTime = 0; // 마지막 포커스 시간
	let isComposing = $state(false); // 한글 조합 상태 추적
	
	// 이미지 업로드 관련 상태
	let isConvertingImage = $state(false); // 이미지 변환 중 플래그
	let imageInputFile: HTMLInputElement; // 파일 선택 입력 요소
	let showImageMenu = $state(false); // 이미지 메뉴 표시 여부
	let isInputTall = $state(false); // 입력창이 높아졌는지 여부
	
	// 호버 메뉴 상태
	let showToolMenu = $state(false); // 도구 메뉴 표시 여부
	let toolMenuTimeout: any = null; // 메뉴 숨김 타이머
	
	// 포커스 상태 변화 추적
	$effect(() => {
		console.log('포커스 상태 변화:', isMathFieldFocused);
	});

	// 입력창 높이 감지 함수
	function checkInputHeight() {
		if (editableElement) {
			const height = editableElement.offsetHeight;
			// 100px 이상이면 높다고 판단 (기본 min-height 80px + 여유분)
			const wasTall = isInputTall;
			isInputTall = height > 100;
			console.log(`입력창 높이: ${height}px, 이전 상태: ${wasTall}, 현재 상태: ${isInputTall}`);
		}
	}
	
	// 모바일에서만 도구 메뉴 표시/숨김 함수
	function showToolMenuHandler() {
		// 모바일에서만 작동
		if (window.innerWidth <= 768) {
			showToolMenu = true;
			// 포커스 해제 타이머 정리 (포커스 중이면 메뉴 유지)
			if (toolMenuTimeout) {
				clearTimeout(toolMenuTimeout);
				toolMenuTimeout = null;
			}
		}
	}
	
	function hideToolMenuHandler() {
		// 모바일에서만 작동
		if (window.innerWidth <= 768) {
			toolMenuTimeout = setTimeout(() => {
				showToolMenu = false;
			}, 2000); // 2초 지연 후 숨김
		}
	}
	
	function toggleToolMenu() {
		// 모바일에서만 작동
		if (window.innerWidth <= 768) {
			showToolMenu = !showToolMenu;
			if (toolMenuTimeout) {
				clearTimeout(toolMenuTimeout);
			}
		}
	}
	
	// 모바일에서 터치 이벤트 처리
	function handleTouchStart() {
		// 모바일에서만 작동
		if (window.innerWidth <= 768) {
			showToolMenu = true;
			if (toolMenuTimeout) {
				clearTimeout(toolMenuTimeout);
			}
		}
	}
	
	function handleTouchEnd() {
		// 모바일에서만 작동
		if (window.innerWidth <= 768) {
			// 터치 종료 시 약간의 지연 후 숨김
			toolMenuTimeout = setTimeout(() => {
				showToolMenu = false;
			}, 3000); // 모바일에서는 3초 지연
		}
	}

	// 입력창 높이 변화 감지
	$effect(() => {
		checkInputHeight();
	});

	// 입력창 내용 변화 감지
	$effect(() => {
		// value가 변경될 때마다 높이 체크
		if (editableElement) {
			// 약간의 지연을 두고 높이 체크 (DOM 업데이트 후)
			setTimeout(() => {
				checkInputHeight();
			}, 50);
			
			// 입력창에 직접 이벤트 리스너 추가
			const handleInput = () => {
				setTimeout(() => {
					checkInputHeight();
				}, 10);
			};
			
			editableElement.addEventListener('input', handleInput);
			editableElement.addEventListener('paste', handleInput);
			
			// cleanup
			return () => {
				editableElement.removeEventListener('input', handleInput);
				editableElement.removeEventListener('paste', handleInput);
			};
		}
	});

	const dispatch = createEventDispatcher<{
		send: { message: string };
		input: { message: string };
	}>();

	// 다음 텍스트 위치로 포커스 이동
	function moveToNextTextPosition(mathContainer: Element) {
		if (!browser || typeof window === 'undefined' || typeof document === 'undefined') return;
		const mathIndex = Array.from(editableElement.childNodes).indexOf(mathContainer);
		
		// 수식 다음에 텍스트 노드가 있는지 확인
		if (mathIndex < editableElement.childNodes.length - 1) {
			const nextNode = editableElement.childNodes[mathIndex + 1];
			if (nextNode.nodeType === Node.TEXT_NODE) {
				// 다음 텍스트 노드의 시작으로 커서 이동
				const range = document.createRange();
				range.setStart(nextNode, 0);
				range.collapse(true);
				const selection = window.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(range);
				editableElement.focus();
				return;
			}
		}
		
		// 다음 텍스트 노드가 없으면 수식 뒤에 새로운 위치 생성
		const range = document.createRange();
		range.setStart(editableElement, mathIndex + 1);
		range.collapse(true);
		const selection = window.getSelection();
		selection?.removeAllRanges();
		selection?.addRange(range);
		editableElement.focus();
	}

	// 이전 텍스트 위치로 포커스 이동
	function moveToPreviousTextPosition(mathContainer: Element) {
		if (!browser || typeof window === 'undefined' || typeof document === 'undefined') return;
		const mathIndex = Array.from(editableElement.childNodes).indexOf(mathContainer);
		
		// 수식 이전에 텍스트 노드가 있는지 확인
		if (mathIndex > 0) {
			const prevNode = editableElement.childNodes[mathIndex - 1];
			if (prevNode.nodeType === Node.TEXT_NODE) {
				// 이전 텍스트 노드의 끝으로 커서 이동
				const range = document.createRange();
				range.setStart(prevNode, prevNode.textContent?.length || 0);
				range.collapse(true);
				const selection = window.getSelection();
				selection?.removeAllRanges();
				selection?.addRange(range);
				editableElement.focus();
				return;
			}
		}
		
		// 이전 텍스트 노드가 없으면 수식 앞에 새로운 위치 생성
		const range = document.createRange();
		range.setStart(editableElement, mathIndex);
		range.collapse(true);
		const selection = window.getSelection();
		selection?.removeAllRanges();
		selection?.addRange(range);
		editableElement.focus();
	}

	// 커스텀 가상 키보드 레이아웃 설정
	function setupCustomVirtualKeyboard() {
		if (!browser || typeof window === 'undefined') return;
		
		try {
			// MathLive 가상 키보드에 접근
			const { mathVirtualKeyboard } = window as any;
			
			if (mathVirtualKeyboard) {
				// 기존 레이아웃에 수학기호 레이아웃 추가 (대체하지 않고 추가)
				mathVirtualKeyboard.layouts = [
					"numeric",   // 기본 numeric 레이아웃 먼저
					"symbols",   // 기본 symbols 레이아웃
					"alphabetic", // 기본 alphabetic 레이아웃
					{
						label: "수학기호",
						tooltip: "고급 수학 기호와 첨자",
						rows: [
							[
								"\\sum_{#?}^{#?}", "\\prod_{#?}^{#?}", "\\int_{#?}^{#?}", "\\lim_{#? \\to #?}", "\\sin", "\\cos", "\\tan", "\\log", "\\ln", "\\sqrt{#0}"
							],
							[
								"#@^{#?}", "#@_{#?}", "\\frac{#@}{#?}", "\\binom{#@}{#?}", "\\left(#@\\right)", "\\left[#@\\right]", "\\left\\{#@\\right\\}", "\\left|#@\\right|", "\\infty", "\\pi"
							],
							[
								"\\alpha", "\\beta", "\\gamma", "\\delta", "\\theta", "\\lambda", "\\mu", "\\sigma", "\\omega", "\\Omega"
							],
							[
								"\\neq", "\\leq", "\\geq", "\\approx", "\\equiv", "\\subset", "\\supset", "\\in", "\\notin", "\\forall"
							]
						]
					}
				];
			}
		} catch (error) {
			console.log('커스텀 가상 키보드 설정 오류:', error);
		}
	}

	// 가상 키보드가 나타날 때 화면을 위로 스크롤하는 함수
	let isScrolling = false; // 스크롤 중 플래그
	
	function scrollForVirtualKeyboard() {
		if (!browser || !editableElement || isScrolling) return;
		
		// 포커스가 해제된 상태에서는 스크롤하지 않음
		if (!isMathFieldFocused) {
			console.log('포커스가 해제된 상태에서 스크롤 중단');
			return;
		}
		
		try {
			isScrolling = true;
			
			// 현재 입력창의 위치 계산
			const inputRect = editableElement.getBoundingClientRect();
			const viewportHeight = window.innerHeight;
			
			// 데스크톱과 모바일에서 다른 키보드 높이 추정
			const isMobile = window.innerWidth <= 768;
			const estimatedKeyboardHeight = isMobile ? viewportHeight * 0.45 : 300; // 데스크톱에서는 300px로 추정
			const availableHeight = viewportHeight - estimatedKeyboardHeight;
			
			// 입력창이 가려지거나 가상키보드 영역에 겹치는지 확인
			if (inputRect.bottom > availableHeight || inputRect.top < 100) {
				// 입력창이 화면 상단 1/3 지점에 오도록 스크롤
				const targetPosition = viewportHeight * 0.33; // 화면 상단 1/3 지점
				const currentScrollY = window.scrollY;
				const inputTop = inputRect.top + currentScrollY;
				const scrollAmount = inputTop - targetPosition;
				
				// 부드러운 스크롤
				window.scrollBy({
					top: scrollAmount,
					behavior: 'smooth'
				});
				
				console.log('가상키보드용 스크롤 실행:', { 
					isMobile, 
					estimatedKeyboardHeight, 
					scrollAmount,
					inputRect: inputRect 
				});
			}
			
			// 스크롤 완료 후 플래그 리셋
			setTimeout(() => {
				isScrolling = false;
			}, 500);
			
		} catch (error) {
			console.log('스크롤 처리 중 오류:', error);
			isScrolling = false;
		}
	}

	// 포커스 강제 해제 중 플래그
	let isForceClearingFocus = false;
	
	// MathLive API 안전 호출 유틸리티
	function safeMathLiveCall(mathField: any, operation: string, fallback: any = null) {
		try {
			// MathField가 유효한지 확인
			if (!mathField || !mathField.isConnected || !mathField.parentNode) {
				console.log(`MathField가 DOM에서 제거되었거나 유효하지 않음: ${operation}`);
				return fallback;
			}
			
			// MathField가 완전히 초기화되었는지 확인
			if (!mathField.getValue || typeof mathField.executeCommand !== 'function') {
				console.log(`MathField가 완전히 초기화되지 않음: ${operation}`);
				return fallback;
			}
			
			switch (operation) {
				case 'position':
					return mathField.position || 0;
				case 'selection':
					return mathField.selection || { start: 0, end: 0 };
				case 'value':
					return mathField.value || '';
				case 'showVirtualKeyboard':
					mathField.executeCommand('showVirtualKeyboard');
					return true;
				case 'hideVirtualKeyboard':
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					return true;
				case 'toggleVirtualKeyboard':
					mathField.executeCommand('toggleVirtualKeyboard');
					return true;
				default:
					return fallback;
			}
		} catch (error) {
			console.log(`MathLive ${operation} 호출 오류:`, error);
			return fallback;
		}
	}
	
	// 디바운스된 포커스 처리 함수
	function handleDebouncedFocus(mathField: any) {
		const now = Date.now();
		
		// 100ms 이내의 중복 포커스 이벤트 무시
		if (now - lastFocusTime < 100) {
			console.log('중복 포커스 이벤트 무시:', mathField.id, now - lastFocusTime, 'ms');
			mathField.blur(); // 즉시 포커스 해제
			return false;
		}
		
		// 강제 해제 중이거나 전환 중이면 무시
		if (isForceClearingFocus || isTransitioning) {
			console.log('강제 해제/전환 중, 포커스 설정 생략:', mathField.id);
			mathField.blur(); // 즉시 포커스 해제
			return false;
		}
		
		// 이미 같은 필드에 포커스가 있으면 무시
		if (isMathFieldFocused && currentMathField === mathField) {
			console.log('이미 포커스된 수식 필드, 중복 처리 생략:', mathField.id);
			return false;
		}
		
		// 다른 필드에 포커스가 있으면 먼저 해제
		if (isMathFieldFocused && currentMathField && currentMathField !== mathField) {
			console.log('다른 수식 필드에서 포커스 이동:', currentMathField.id, '→', mathField.id);
			isTransitioning = true;
			
			// 이전 필드의 가상 키보드 숨기기
			safeMathLiveCall(currentMathField, 'hideVirtualKeyboard');
			
			setTimeout(() => {
				isTransitioning = false;
			}, 50);
		}
		
		lastFocusTime = now;
		return true;
	}
	
	// 모든 수식 필드에서 포커스 강제 해제
	function forceClearMathFocus() {
		if (!browser || typeof window === 'undefined') return;
		
		console.log('강제 포커스 해제 실행 - 현재 상태:', {
			isMathFieldFocused,
			currentMathField: currentMathField?.id || null,
			activeElement: document.activeElement?.tagName || null
		});
		
		// 강제 해제 중 플래그 설정
		isForceClearingFocus = true;
		
		// 디바운스 타이머 클리어
		if (focusDebounceTimer) {
			clearTimeout(focusDebounceTimer);
			focusDebounceTimer = null;
		}
		
		// 상태 즉시 초기화 (반응형 상태 강제 업데이트)
		isMathFieldFocused = false;
		currentMathField = null;
		
		// Svelte의 상태 업데이트를 강제로 반영
		setTimeout(() => {
			console.log('포커스 상태 초기화 후 (지연 확인):', isMathFieldFocused);
		}, 0);
		
		// 모든 수식 필드 찾기
		const mathFields = editableElement?.querySelectorAll('math-field');
		mathFields?.forEach(field => {
			try {
				const mathField = field as MathfieldElement;
				
				// 가상 키보드 숨기기
				try {
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					console.log('가상 키보드 숨기기:', mathField.id);
				} catch (e) {
					console.log('가상 키보드 숨기기 실패:', e);
				}
				
				// 포커스 해제
				mathField.blur();
				console.log('수식 필드 포커스 해제:', mathField.id);
			} catch (e) {
				console.log('수식 필드 포커스 해제 오류:', e);
			}
		});
		
		// 현재 포커스된 요소가 수식 필드인 경우 강제로 포커스 해제
		if (document.activeElement && document.activeElement.tagName === 'MATH-FIELD') {
			(document.activeElement as HTMLElement).blur();
			console.log('현재 활성 수식 필드 포커스 해제');
		}
		
		// 전역적으로 수식 관련 포커스 강제 해제 및 가상 키보드 숨기기
		const allMathFields = document.querySelectorAll('math-field');
		allMathFields.forEach(field => {
			try {
				const mathField = field as MathfieldElement;
				
				// 가상 키보드 숨기기
				try {
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
				} catch (e) {
					// 무시
				}
				
				// 가상 키보드 강제 숨기기
				try {
					if ((mathField as any).virtualKeyboardVisible) {
						(mathField as any).virtualKeyboardVisible = false;
					}
				} catch (e) {
					// 무시
				}
				
				// 포커스 해제
				mathField.blur();
			} catch (e) {
				// 무시
			}
		});
		
		// DOM에서 가상 키보드 요소 직접 제거
		setTimeout(() => {
			try {
				// MathLive 가상 키보드 관련 DOM 요소들 찾기
				const virtualKeyboardElements = document.querySelectorAll('.ML__virtual-keyboard, .mathlive-virtual-keyboard, [data-mathlive-virtual-keyboard]');
				virtualKeyboardElements.forEach(element => {
					console.log('가상 키보드 DOM 요소 제거:', element);
					element.remove();
				});
				
				// 추가로 MathLive 관련 오버레이 요소들도 제거
				const overlayElements = document.querySelectorAll('.ML__overlay, .mathlive-overlay');
				overlayElements.forEach(element => {
					if (element.textContent?.includes('keyboard') || element.className.includes('keyboard')) {
						console.log('가상 키보드 오버레이 제거:', element);
						element.remove();
					}
				});
				
				// body에서 가상 키보드 관련 클래스 제거
				document.body.classList.remove('ML__virtual-keyboard-visible', 'mathlive-virtual-keyboard-visible');
				
				// CSS를 통한 강제 숨기기
				const style = document.createElement('style');
				style.textContent = `
					.ML__virtual-keyboard,
					.mathlive-virtual-keyboard,
					[data-mathlive-virtual-keyboard] {
						display: none !important;
						visibility: hidden !important;
						opacity: 0 !important;
						transform: translateY(100%) !important;
					}
				`;
				document.head.appendChild(style);
				
				// 1초 후 스타일 제거 (일시적 숨기기)
				setTimeout(() => {
					if (style.parentNode) {
						style.parentNode.removeChild(style);
					}
				}, 1000);
				
			} catch (e) {
				console.log('DOM 요소 제거 중 오류:', e);
			}
		}, 100);
		
		// 강제 해제 완료 후 플래그 리셋 (더 긴 지연으로 재포커스 방지)
		setTimeout(() => {
			isForceClearingFocus = false;
			console.log('강제 포커스 해제 완료');
		}, 500); // 200ms → 500ms로 증가
	}

	// 수식 삽입 또는 가상 키보드 토글 함수
	async function insertMathAtCursor() {
		if (!browser || !editableElement || typeof window === 'undefined') return;
		
		// 수식 버튼 클릭 시 포커스 해제 방지
		console.log('수식 버튼 클릭 - 포커스 해제 방지');
		
		// 포커스 해제 방지 플래그 설정 (짧은 시간 동안)
		const wasForceClearing = isForceClearingFocus;
		isForceClearingFocus = true;
		setTimeout(() => {
			isForceClearingFocus = wasForceClearing;
		}, 100);
		
		// 수식 필드에 포커스가 있으면 가상 키보드 토글
		if (isMathFieldFocused && currentMathField) {
			console.log('가상 키보드 토글 시도');
			
			// 커스텀 레이아웃 설정
			setupCustomVirtualKeyboard();
			
			if (safeMathLiveCall(currentMathField, 'toggleVirtualKeyboard')) {
				// 가상 키보드 토글 후 스크롤 처리
				setTimeout(() => {
					scrollForVirtualKeyboard();
				}, 300);
			}
			return;
		}
		
		try {
			// 브라우저 환경 재확인
			if (typeof window === 'undefined' || typeof document === 'undefined') return;
			
			// 현재 커서 위치 저장
			const selection = window.getSelection();
			let range = (selection && selection.rangeCount > 0) ? selection.getRangeAt(0) : null;
			
			// 현재 커서가 입력 영역 내부에 있는지 확인
			let isCursorInInputArea = false;
			if (range) {
				// 현재 선택의 컨테이너가 입력 영역 내부에 있는지 확인
				isCursorInInputArea = editableElement.contains(range.startContainer) || 
									editableElement.contains(range.commonAncestorContainer);
				
				// 더 확실한 확인을 위해 startContainer의 부모들도 체크
				let currentNode: Node | null = range.startContainer;
				while (currentNode && currentNode !== document.body) {
					if (currentNode === editableElement) {
						isCursorInInputArea = true;
						break;
					}
					currentNode = currentNode.parentNode;
				}
			}
			
			// 커서가 입력 영역 밖에 있으면 입력 영역으로 이동
			if (!isCursorInInputArea) {
				console.log('커서가 입력 영역 밖에 있어서 입력 영역으로 포커스 이동 (렌더링 영역에서 수식 버튼 클릭)');
				
				// 입력 영역으로 포커스 이동
				editableElement.focus();
				
				// 입력 영역 끝에 커서 설정
				const newRange = document.createRange();
				newRange.selectNodeContents(editableElement);
				newRange.collapse(false); // 끝으로 이동
				selection?.removeAllRanges();
				selection?.addRange(newRange);
				range = newRange;
				
				// 약간의 지연을 두어 포커스가 확실히 설정되도록 함
				await new Promise(resolve => setTimeout(resolve, 50));
			}
			
			// selection이 없거나 range가 없으면 editableElement의 끝에 삽입
			if (!selection || selection.rangeCount === 0 || !range) {
				console.log('selection이 없어서 끝에 수식 삽입');
				// editableElement의 끝에 포커스 설정
				editableElement.focus();
				const newRange = document.createRange();
				newRange.selectNodeContents(editableElement);
				newRange.collapse(false); // 끝으로 이동
				selection?.removeAllRanges();
				selection?.addRange(newRange);
				range = newRange;
			}
			
			if (!range) return;
			
			// 현재 커서가 수식 안에 있는지 확인
			let currentNode: Node | null = range.startContainer;
			while (currentNode && currentNode !== editableElement) {
				if (currentNode.nodeType === Node.ELEMENT_NODE) {
					const element = currentNode as Element;
					if (element.tagName === 'MATH-FIELD' || element.classList.contains('inline-math-container')) {
						// 이미 수식 안에 있으면 수식 삽입 중단
						console.log('이미 수식 영역 안에 있습니다.');
						return;
					}
				}
				currentNode = currentNode.parentNode;
			}
			
			// 고유 ID 생성
			const mathId = `math-${++mathCounter}`;
			
			// 작은 MathLive 컨테이너 생성
			const mathContainer = document.createElement('span');
			mathContainer.className = 'inline-math-container';
			mathContainer.contentEditable = 'false'; // 수식 영역은 편집 불가
			mathContainer.style.cssText = `
				display: inline-block;
				margin: 0 2px;
				vertical-align: middle;
				background: var(--maice-bg-secondary);
				border: 1px solid var(--maice-border-secondary);
				border-radius: 6px;
				padding: 4px 8px;
				min-width: 50px;
				min-height: 28px;
				cursor: pointer;
				position: relative;
			`;
			
		// MathLive 필드 생성
		const mathField = document.createElement('math-field') as MathfieldElement;
		mathField.id = mathId;
		
		// 가상 키보드 수동 모드로 설정
		mathField.setAttribute('virtual-keyboard-mode', 'manual');
		
		// MathField 초기화 완료 대기
		mathField.addEventListener('ready', () => {
			console.log('MathField 초기화 완료:', mathField.id);
		});
			
			mathField.style.cssText = `
				border: none;
				background: transparent;
				font-size: 14px;
				min-height: 20px;
				padding: 0;
				margin: 0;
				display: inline-block;
				width: auto;
				min-width: 30px;
			`;
			
			// MathLive 설정 (순수 수식 모드)
			try {
				Object.assign(mathField, {
					defaultMode: 'math',
					placeholder: '?',
					virtualKeyboardMode: 'manual', // 일관된 설정
					smartMode: false,
					smartFence: true,
					smartSuperscript: true,
					keypressSound: null,
					readOnly: false,
					// 추가 안정성 설정
					ignoreSpacebarInMathMode: true,
					removeExtraneousParentheses: false,
					// 렌더링 안정성 설정
					renderAccessibleContent: false, // 접근성 콘텐츠 렌더링 비활성화
					useSharedVirtualKeyboard: true, // 공유 가상 키보드 사용
				});
			} catch (error) {
				console.log('MathLive 설정 오류:', error);
			}
			
			// 기본 input 이벤트
			mathField.addEventListener('input', () => {
				updateTextValue();
			});
			
			// 수식 필드에서 포커스 이동을 위한 키보드 이벤트
			mathField.addEventListener('keydown', (e) => {
				// 화살표 키 처리 - 올바른 MathLive API 사용
				if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
					try {
						// MathLive의 position과 selection ranges를 사용하여 정확한 위치 확인
						const selection = mathField.selection;
						const position = mathField.position ?? 0;
						const value = mathField.value || '';
						
						// selection.ranges는 [[start, end]] 형태의 배열
						const ranges = selection?.ranges || [[0, 0]];
						const [start, end] = ranges[0] || [0, 0];
						
						console.log('화살표 키 처리:', {
							key: e.key,
							position,
							start,
							end,
							valueLength: value.length
						});
					
					// 오른쪽 화살표 키: 커서가 끝에 있을 때 다음 텍스트 영역으로 이동
					if (e.key === 'ArrowRight') {
						// end가 value 길이와 같거나, position이 끝에 도달했는지 확인
						if (end >= value.length || position >= value.length) {
							console.log('수식 끝에 도달 - 다음 텍스트 영역으로 이동');
							e.preventDefault();
							
							// 전환 중 플래그 설정하여 재포커스 방지
							isTransitioning = true;
							isMathFieldFocused = false;
							currentMathField = null;
							
							// 가상 키보드 숨기기
							try {
								safeMathLiveCall(mathField, 'hideVirtualKeyboard');
							} catch (err) {
								console.log('가상 키보드 숨기기 실패:', err);
							}
							
							// 포커스 이동
							mathField.blur();
							setTimeout(() => {
								moveToNextTextPosition(mathContainer);
								isTransitioning = false;
							}, 50);
							return;
						}
					}
					// 왼쪽 화살표 키: 커서가 시작에 있을 때 이전 텍스트 영역으로 이동
					if (e.key === 'ArrowLeft') {
						if (start <= 0 || position <= 0) {
							console.log('수식 시작에 도달 - 이전 텍스트 영역으로 이동');
							e.preventDefault();
							
							// 전환 중 플래그 설정하여 재포커스 방지
							isTransitioning = true;
							isMathFieldFocused = false;
							currentMathField = null;
							
							// 가상 키보드 숨기기
							try {
								safeMathLiveCall(mathField, 'hideVirtualKeyboard');
							} catch (err) {
								console.log('가상 키보드 숨기기 실패:', err);
							}
							
							// 포커스 이동
							mathField.blur();
							setTimeout(() => {
								moveToPreviousTextPosition(mathContainer);
								isTransitioning = false;
							}, 50);
							return;
						}
					}
				} catch (error) {
						console.log('MathLive API 호출 실패, 기본 동작 허용:', error);
						return;
					}
				}
				
				// Tab 키: 다음 요소로 포커스 이동
				if (e.key === 'Tab') {
					e.preventDefault();
					e.stopPropagation();
					if (e.shiftKey) {
						moveToPreviousTextPosition(mathContainer);
					} else {
						moveToNextTextPosition(mathContainer);
					}
					return;
				}
				// Escape 키: 수식 편집 종료하고 텍스트 영역으로 포커스
				if (e.key === 'Escape') {
					e.preventDefault();
					e.stopPropagation();
					
					// 전환 중 플래그 설정
					isTransitioning = true;
					
					// 상태 즉시 업데이트
					isMathFieldFocused = false;
					currentMathField = null;
					
					// 가상 키보드 숨기기
					try {
						safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					} catch (e) {
						console.log('가상 키보드 숨기기 실패:', e);
					}
					
					// 포커스 제거
					mathField.blur();
					
					// 텍스트 영역으로 포커스 이동
					setTimeout(() => {
						editableElement.focus();
						// 수식 뒤에 커서 위치
						const mathIndex = Array.from(editableElement.childNodes).indexOf(mathContainer);
						if (mathIndex !== -1) {
							const range = document.createRange();
							range.setStart(editableElement, mathIndex + 1);
							range.collapse(true);
							const selection = window.getSelection();
							selection?.removeAllRanges();
							selection?.addRange(range);
						}
						
						// 전환 완료
						isTransitioning = false;
					}, 50);
					return;
				}
				
				// 추가: Enter 키로도 수식에서 빠져나올 수 있도록
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					e.stopPropagation();
					
					// 전환 중 플래그 설정
					isTransitioning = true;
					
					// 상태 즉시 업데이트
					isMathFieldFocused = false;
					currentMathField = null;
					
					// 가상 키보드 숨기기
					try {
						safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					} catch (e) {
						console.log('가상 키보드 숨기기 실패:', e);
					}
					
					// 포커스 제거 후 다음 위치로 이동
					mathField.blur();
					
					setTimeout(() => {
						moveToNextTextPosition(mathContainer);
						// 전환 완료
						isTransitioning = false;
					}, 50);
					return;
				}
			});
			
		// 수식 필드 포커스 추적 (디바운스 처리)
		mathField.addEventListener('focus', () => {
			// 전환 중이면 포커스 무시
			if (isTransitioning) {
				console.log('포커스 전환 중, focus 이벤트 무시:', mathField.id);
				mathField.blur();
				return;
			}
			
			// 디바운스된 포커스 처리
			if (!handleDebouncedFocus(mathField)) {
				return;
			}
			
			console.log('수식 필드 포커스 설정:', mathField.id);
			isMathFieldFocused = true;
			currentMathField = mathField;
			
			// 디바운스 타이머 클리어
			if (focusDebounceTimer) {
				clearTimeout(focusDebounceTimer);
			}
			
			// 가상 키보드 표시를 디바운스 처리
			focusDebounceTimer = setTimeout(() => {
				// 재검증: 여전히 포커스가 유효한지 확인
				if (!isForceClearingFocus && !isTransitioning && isMathFieldFocused && currentMathField === mathField) {
					if (safeMathLiveCall(mathField, 'showVirtualKeyboard')) {
						console.log('가상키보드 표시됨:', mathField.id);
						// 가상키보드 표시 후 스크롤
						setTimeout(() => {
							scrollForVirtualKeyboard();
						}, 200);
					}
				} else {
					console.log('포커스 상태 변경으로 가상키보드 표시 취소:', mathField.id);
				}
				focusDebounceTimer = null;
			}, 150);
		});
			
		// 수식 필드에서 포커스가 나갈 때 처리
		mathField.addEventListener('blur', (e) => {
			// 전환 중이면 처리하지 않음
			if (isTransitioning) {
				console.log('포커스 전환 중, blur 처리 생략:', mathField.id);
				return;
			}
			
			// 즉시 포커스 상태 해제 (지연 시간 단축)
			setTimeout(() => {
				// 전환 중이면 처리하지 않음 (다시 체크)
				if (isTransitioning) {
					console.log('포커스 전환 중 (재확인), blur 처리 생략:', mathField.id);
					return;
				}
				
				// 현재 활성 요소가 이 수식 필드가 아니면 포커스 해제
				if (document.activeElement !== mathField) {
					console.log('수식 필드 포커스 해제 (blur 이벤트):', mathField.id);
					
					// 이미 포커스가 해제된 상태라면 추가 처리하지 않음
					if (!isMathFieldFocused) {
						console.log('이미 포커스가 해제된 상태, 추가 처리 생략');
						return;
					}
					
					isMathFieldFocused = false;
					currentMathField = null;
					
					// 가상 키보드 자동 숨기기 (안전한 호출)
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					
					// 빈 수식이면 제거 (안전한 값 확인)
					const fieldValue = safeMathLiveCall(mathField, 'value', '');
					if (!fieldValue || !fieldValue.trim()) {
						mathContainer.remove();
						updateTextValue();
					}
				}
			}, 50); // 지연 시간을 150ms에서 50ms로 단축
		});
			
		// 수식 컨테이너 클릭 처리 - 더블클릭 시에만 포커스
		mathContainer.addEventListener('click', (e) => {
			// 단일 클릭은 포커스하지 않고, 더블클릭이나 키보드로만 포커스
			e.preventDefault();
			e.stopPropagation();
			e.stopImmediatePropagation();
			
			// 수식 필드에 포커스하지 않음 - 더블클릭이나 키보드 입력 시에만 포커스
		});

		// 수식 컨테이너에 더블클릭으로 편집 모드 진입
		mathContainer.addEventListener('dblclick', (e) => {
			e.preventDefault();
			e.stopPropagation();
			e.stopImmediatePropagation();
			
			// 더블클릭 시 수식 편집 모드로 진입
			mathField.focus();
		});

			// 수식 필드에서 Ctrl+Delete로 삭제 (위의 keydown 이벤트에 통합됨)
			
			// 컨테이너에 MathLive 추가
			mathContainer.appendChild(mathField);
			
			// 커서 위치에 삽입
			range.deleteContents();
			range.insertNode(mathContainer);
			
			// 수식 뒤에 공백 문자 삽입 (나중에 백스페이스로 제거 가능하도록)
			const spaceText = document.createTextNode(' '); // 공백 문자
			const afterRange = document.createRange();
			afterRange.setStartAfter(mathContainer);
			afterRange.insertNode(spaceText);
			
			// 수식 생성 후 새로 만든 수식 필드에 자동 포커스 및 가상 키보드 표시
			// requestAnimationFrame을 사용하여 브라우저가 렌더링을 완료할 때까지 대기
			requestAnimationFrame(() => {
				requestAnimationFrame(() => {
					// MathField가 DOM에 완전히 마운트될 때까지 대기
					if (!mathField || !mathField.getValue) {
						console.log('MathField가 아직 준비되지 않음');
						return;
					}
					
					try {
						// 포커스 설정
						mathField.focus();
						
						// 포커스 상태 업데이트
						isMathFieldFocused = true;
						currentMathField = mathField;
						
						// 가상 키보드 표시 - 추가 지연으로 MathField 완전 초기화 대기
						setTimeout(() => {
							try {
								// MathField 상태 재확인
								if (!mathField || !mathField.getValue || typeof mathField.executeCommand !== 'function') {
									console.log('MathField가 완전히 준비되지 않음, 가상 키보드 표시 생략');
									return;
								}
								
								// 커스텀 레이아웃 설정
								setupCustomVirtualKeyboard();
								
								// 안전하게 가상 키보드 표시
								safeMathLiveCall(mathField, 'showVirtualKeyboard');
								
								// 가상키보드 표시 후 스크롤 처리
								setTimeout(() => {
									scrollForVirtualKeyboard();
								}, 300);
							} catch (e) {
								console.log('가상 키보드 표시 실패 (무시됨):', e);
							}
						}, 150); // 지연 시간 증가
					} catch (e) {
						console.log('MathField 포커스 실패:', e);
					}
				});
			});
			
			updateTextValue();
			
		} catch (error) {
			console.error('수식 삽입 오류:', error);
		}
	}

	// 텍스트 값 업데이트 (LaTeX 형태로 변환)
	function updateTextValue() {
		if (!editableElement || isUpdating) return;
		
		isUpdating = true;
		
		try {
			let result = '';
			const walker = document.createTreeWalker(
				editableElement,
				NodeFilter.SHOW_ALL,
				null
			);
			
			let node;
			while (node = walker.nextNode()) {
				if (node.nodeType === Node.TEXT_NODE) {
					result += node.textContent;
				} else if (node.nodeType === Node.ELEMENT_NODE) {
					const element = node as Element;
					
					if (element.tagName === 'MATH-FIELD') {
						const mathField = element as MathfieldElement;
						const latex = safeMathLiveCall(mathField, 'value', '');
						if (latex && latex.trim()) {
							result += `$${latex}$`;
						}
					} else if (element.tagName === 'BR') {
						result += '\n';
					}
				}
			}
			
			if (result !== value) {
				value = result;
				dispatch('input', { message: result });
			}
		} finally {
			setTimeout(() => {
				isUpdating = false;
			}, 10);
		}
	}

	// 붙여넣기 이벤트 처리 - 이미지 또는 텍스트 처리
	async function handlePaste(event: ClipboardEvent) {
		const clipboardData = event.clipboardData;
		if (!clipboardData) return;
		
		// 1. 먼저 이미지가 있는지 확인
		const items = clipboardData.items;
		if (items) {
			for (const item of items) {
				if (item.type.startsWith('image/')) {
					event.preventDefault(); // 기본 붙여넣기 동작 방지
					
					const file = item.getAsFile();
					if (!file) continue;
					
					console.log('클립보드에서 이미지 감지:', {
						type: file.type,
						size: file.size
					});
					
					// 파일 크기 검증 (10MB)
					const maxSize = 10 * 1024 * 1024;
					if (file.size > maxSize) {
						alert('파일 크기는 10MB 이하여야 합니다.');
						return;
					}
					
					// 이미지를 Data URL로 변환하여 크롭 모달 표시
					const reader = new FileReader();
					reader.onload = (e) => {
						const imageUrl = e.target?.result as string;
						dispatch('openImageCrop', { imageUrl });
					};
					reader.readAsDataURL(file);
					
					return; // 이미지 처리 후 종료
				}
			}
		}
		
		// 2. 이미지가 없으면 텍스트 처리
		event.preventDefault();
		
		// 클립보드에서 텍스트 데이터 가져오기
		const pastedText = clipboardData.getData('text/plain');
		const pastedHTML = clipboardData.getData('text/html');
		
		console.log('=== 붙여넣기 디버그 ===');
		console.log('텍스트 길이:', pastedText.length);
		console.log('HTML 길이:', pastedHTML.length);
		console.log('전체 텍스트:', JSON.stringify(pastedText.substring(0, 500)));
		if (pastedHTML) {
			console.log('HTML 샘플:', pastedHTML.substring(0, 1000));
		}
		
		// 복사된 텍스트가 이미 올바른 형태인지 확인
		// LaTeX가 포함된 순수 텍스트인 경우 text/plain을 우선 사용
		const hasValidLatexInText = /\$[^$]+\$/.test(pastedText);
		
		// LaTeX가 포함된 텍스트가 있으면 그것을 사용, 없으면 HTML 사용
		const sourceText = hasValidLatexInText ? pastedText : (pastedHTML || pastedText);
		if (!sourceText) return;
		
		// 서식 정리된 텍스트 처리
		const cleanedText = cleanPastedText(sourceText);
		console.log('최종 결과:', JSON.stringify(cleanedText.substring(0, 500)));
		insertTextAtCursor(cleanedText);
	}
	
	// 붙여넣은 텍스트의 서식을 정리하는 함수
	function cleanPastedText(text: string): string {
		console.log('원본 붙여넣기 텍스트:', JSON.stringify(text.substring(0, 300)));
		
		// 이미 올바른 형태의 텍스트인지 확인 (LaTeX가 포함된 순수 텍스트)
		const hasValidLatex = /\$[^$]+\$/.test(text);
		const hasHtmlTags = text.includes('<') && text.includes('>');
		
		// LaTeX가 있고 HTML 태그가 없는 경우 (이미 올바른 형태), 최소한의 처리만
		if (hasValidLatex && !hasHtmlTags) {
			console.log('이미 올바른 형태의 텍스트, 최소 처리만 수행');
			return text
				.replace(/[\u200B-\u200D\uFEFF]/g, '') // 제로 너비 문자만 제거
				.trim();
		}
		
		// HTML이 포함된 경우에만 전체 처리 수행
		console.log('HTML 포함 텍스트, 전체 처리 수행');
		
		// 1. HTML 구조에서 실제 텍스트와 LaTeX를 파싱
		text = parseHTMLContent(text);
		
		// 2. LaTeX 수식을 먼저 보호
		const latexMap = new Map<string, string>();
		
		// 블록 수식 보호
		text = text.replace(/\$\$([^$]+?)\$\$/g, (match, content) => {
			const key = `$$LATEX_BLOCK_${latexMap.size}$$`;
			latexMap.set(key, `$$${content.trim()}$$`);
			return key;
		});
		
		// 인라인 수식 보호
		text = text.replace(/\$([^$]+?)\$/g, (match, content) => {
			const key = `$LATEX_INLINE_${latexMap.size}$`;
			latexMap.set(key, `$${content.trim()}$`);
			return key;
		});
		
		// 3. KaTeX HTML을 LaTeX로 변환 (HTML이 있을 때만)
		if (text.includes('<')) {
			text = convertKaTeXToLatex(text);
			text = fixBrokenMathText(text);
		}
		
		// 4. HTML 태그와 서식 제거
		let cleaned = text
			.replace(/<[^>]*>/g, ' ') // HTML 태그 제거
			.replace(/&nbsp;/g, ' ') // HTML 엔티티 변환
			.replace(/&lt;/g, '<')
			.replace(/&gt;/g, '>')
			.replace(/&amp;/g, '&')
			.replace(/&quot;/g, '"')
			.replace(/&#39;/g, "'")
			.replace(/&apos;/g, "'")
			.replace(/\s+/g, ' ') // 연속된 공백을 하나로
			.replace(/\n\s*\n/g, '\n\n') // 문단 구분 보존
			.trim();
		
		// 5. 보호된 LaTeX 수식 복원
		latexMap.forEach((originalLatex, key) => {
			cleaned = cleaned.replace(key, originalLatex);
		});
		
		// 6. 최종 정리
		cleaned = cleaned
			.replace(/[\u200B-\u200D\uFEFF]/g, '') // 제로 너비 문자 제거
			.replace(/[\u00A0]/g, ' ') // 비분리 공백을 일반 공백으로
			.replace(/\u00AD/g, '') // 소프트 하이픈 제거
			.trim();
		
		console.log('서식 정리 완료:', cleaned.substring(0, 200) + '...');
		return cleaned;
	}
	
	// HTML 구조에서 실제 텍스트와 LaTeX를 파싱하는 함수
	function parseHTMLContent(htmlText: string): string {
		console.log('HTML 파싱 시작:', htmlText.substring(0, 200));
		
		// HTML이 아닌 경우 그대로 반환
		if (!htmlText.includes('<') || !htmlText.includes('>')) {
			return htmlText;
		}
		
		try {
			// DOM 파서를 사용할 수 없는 환경이므로 정규식으로 파싱
			
			// 1. 먼저 KaTeX 관련 HTML 태그들을 LaTeX로 변환
			let parsedText = htmlText;
			
			// KaTeX 인라인 수식 찾기
			parsedText = parsedText.replace(/<span[^>]*class="[^"]*katex[^"]*"[^>]*>([\s\S]*?)<\/span>/gi, (match, content) => {
				const latex = extractLatexFromKaTeXContent(content);
				return latex ? `$${latex}$` : match;
			});
			
			// KaTeX 블록 수식 찾기
			parsedText = parsedText.replace(/<div[^>]*class="[^"]*katex-display[^"]*"[^>]*>([\s\S]*?)<\/div>/gi, (match, content) => {
				const latex = extractLatexFromKaTeXContent(content);
				return latex ? `$$${latex}$$` : match;
			});
			
			// MathML 태그 찾기
			parsedText = parsedText.replace(/<math[^>]*>([\s\S]*?)<\/math>/gi, (match, mathml) => {
				const latex = extractLatexFromMathML(mathml);
				return latex ? `$${latex}$` : match;
			});
			
			// MathLive 태그 찾기
			parsedText = parsedText.replace(/<math-field[^>]*>([\s\S]*?)<\/math-field>/gi, (match, content) => {
				const latex = extractLatexFromMathField(content);
				return latex ? `$${latex}$` : match;
			});
			
			// 2. 모든 HTML 태그 제거 (하지만 LaTeX는 보존)
			// 먼저 LaTeX를 임시 마커로 대체
			const latexMarkers: { [key: string]: string } = {};
			let markerCount = 0;
			
			parsedText = parsedText.replace(/\$[^$]+\$/g, (match) => {
				const marker = `__LATEX_TEMP_${markerCount++}__`;
				latexMarkers[marker] = match;
				return marker;
			});
			
			// HTML 태그 제거
			parsedText = parsedText.replace(/<[^>]*>/g, ' ');
			
			// HTML 엔티티 변환
			parsedText = parsedText
				.replace(/&nbsp;/g, ' ')
				.replace(/&lt;/g, '<')
				.replace(/&gt;/g, '>')
				.replace(/&amp;/g, '&')
				.replace(/&quot;/g, '"')
				.replace(/&#39;/g, "'")
				.replace(/&apos;/g, "'");
			
			// LaTeX 복원
			Object.entries(latexMarkers).forEach(([marker, latex]) => {
				parsedText = parsedText.replace(marker, latex);
			});
			
			// 3. 공백 정리
			parsedText = parsedText
				.replace(/\s+/g, ' ') // 연속된 공백을 하나로
				.replace(/\n\s*\n/g, '\n\n') // 문단 구분 보존
				.trim();
			
			console.log('HTML 파싱 완료:', parsedText.substring(0, 200));
			return parsedText;
			
		} catch (error) {
			console.warn('HTML 파싱 오류:', error);
			// 오류 발생시 기본 태그 제거만 수행
			return htmlText.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
		}
	}
	
	// 개별 글자로 분리된 수학 텍스트를 복원하는 함수
	function fixBrokenMathText(text: string): string {
		console.log('수학 텍스트 복원 시작:', JSON.stringify(text.substring(0, 200)));
		
		// 더 강력한 패턴으로 개별 글자가 분리된 수식 복원
		
		// 0. 여러 번의 개행으로 분리된 수학 표현식들을 먼저 복원
		// 예: k\n\n+\n\n1 → k+1
		text = text.replace(/([a-zA-Z0-9\(\)])\s*\n+\s*([+=\-*\/])+\s*\n+\s*([a-zA-Z0-9\(\)])/g, '$1$2$3');
		text = text.replace(/([a-zA-Z0-9\(\)])\s*\n+\s*([+=\-*\/])/g, '$1$2');
		text = text.replace(/([+=\-*\/])\s*\n+\s*([a-zA-Z0-9\(\)])/g, '$1$2');
		
		// 1. 기본적인 개별 문자 분리 패턴들
		// n\n=\n1 같은 패턴을 n=1로
		text = text.replace(/([a-zA-Z])\s*\n+\s*=\s*\n+\s*(\d+)/g, '$1=$2');
		text = text.replace(/([a-zA-Z])\s*\n+\s*\+\s*\n+\s*(\d+)/g, '$1+$2');
		text = text.replace(/(\d+)\s*\n+\s*\+\s*\n+\s*([a-zA-Z])/g, '$1+$2');
		
		// 2. 복잡한 수식 패턴들 복원 (사용자 예시 기반)
		// 1+2+3+...+k+(k+1) 패턴
		text = text.replace(/1\s*\n*\s*\+\s*\n*\s*2\s*\n*\s*\+\s*\n*\s*3\s*\n*\s*\+\s*\n*\s*⋯\s*\n*\s*\+\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*\(\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*1\s*\n*\s*\)/g, '1+2+3+\\cdots+k+(k+1)');
		
		// k(k+1)/2 패턴
		text = text.replace(/k\s*\n*\s*\(\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*1\s*\n*\s*\)\s*\n*\s*\/\s*\n*\s*2/g, 'k(k+1)/2');
		text = text.replace(/n\s*\n*\s*\(\s*\n*\s*n\s*\n*\s*\+\s*\n*\s*1\s*\n*\s*\)\s*\n*\s*\/\s*\n*\s*2/g, 'n(n+1)/2');
		
		// (k+1)(k+2)/2 패턴
		text = text.replace(/\(\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*1\s*\n*\s*\)\s*\n*\s*\(\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*2\s*\n*\s*\)\s*\n*\s*\/\s*\n*\s*2/g, '(k+1)(k+2)/2');
		
		// n=k+1 패턴
		text = text.replace(/n\s*\n*\s*=\s*\n*\s*k\s*\n*\s*\+\s*\n*\s*1/g, 'n=k+1');
		
		// 3. 연속된 숫자/문자 복원 (개행과 공백 모두 처리)
		text = text.replace(/([a-zA-Z0-9\(\)])\s*\n+\s*([a-zA-Z0-9\(\)])/g, '$1$2');
		text = text.replace(/([a-zA-Z0-9\(\)])\s+([a-zA-Z0-9\(\)])/g, '$1$2');
		
		// 4. 괄호 내부의 분리된 내용 복원
		text = text.replace(/\(\s*\n+\s*([^)]+?)\s*\n+\s*\)/g, (match, content) => {
			return `(${content.replace(/\s*\n+\s*/g, '')})`;
		});
		
		// 5. 분수 관련 복원
		text = text.replace(/([a-zA-Z0-9\(\)\+]+)\s*\n+\s*\/\s*\n+\s*([a-zA-Z0-9\(\)\+]+)/g, '$1/$2');
		
		// 6. 등호 주변 복원 (더 유연하게)
		text = text.replace(/([a-zA-Z0-9\(\)\+\-\/\s]+)\s*\n+\s*=\s*\n+\s*([a-zA-Z0-9\(\)\+\-\/\s]+)/g, (match, left, right) => {
			const cleanLeft = left.trim().replace(/\s*\n+\s*/g, '');
			const cleanRight = right.trim().replace(/\s*\n+\s*/g, '');
			// 수학 표현식인 경우만 처리
			if (/[a-zA-Z]/.test(cleanLeft) && (/[a-zA-Z]/.test(cleanRight) || /[\/\(\)]/.test(cleanRight))) {
				return `${cleanLeft} = ${cleanRight}`;
			}
			return match;
		});
		
		// 7. 연속된 공백과 줄바꿈 정리 (하지만 문단 구분은 유지)
		text = text.replace(/\s*\n\s*\n\s*\n+/g, '\n\n'); // 여러 줄바꿈을 두 개로
		
		console.log('수학 텍스트 복원 완료:', JSON.stringify(text.substring(0, 200)));
		return text;
	}
	
	// 수학 표현식을 LaTeX로 변환하는 함수
	function convertMathExpressionsToLatex(text: string): string {
		console.log('수학 표현식 변환 시작:', text.substring(0, 200) + '...');
		
		// 이미 $로 감싸진 부분을 제외하고 처리하기 위해 임시 마커 사용
		const markers: { [key: string]: string } = {};
		let markerCount = 0;
		
		// $로 감싸진 부분을 임시 마커로 대체
		text = text.replace(/\$[^$]+\$/g, (match) => {
			const marker = `__LATEX_MARKER_${markerCount++}__`;
			markers[marker] = match;
			return marker;
		});
		
		// 1. 특별한 수학 패턴들을 먼저 처리 (우선순위 높음)
		text = text
			// 사용자 예시에서 자주 나오는 복잡한 패턴들 먼저 처리
			// 1+2+3+...+k+(k+1) 패턴
			.replace(/1\+2\+3\+\?\?\+k\+\(k\+1\)/g, '$1+2+3+\\cdots+k+(k+1)$')
			.replace(/1\s*\+\s*2\s*\+\s*3\s*\+\s*\.\.\.\s*\+\s*k\s*\+\s*\(\s*k\s*\+\s*1\s*\)/g, '$1+2+3+\\cdots+k+(k+1)$')
			
			// 복잡한 등식들
			.replace(/1\+2\+3\+\?\?\+k\+\(k\+1\)\s*=\s*\(k\+1\)\(\(k\+1\)\+1\)\/2/g, '$1+2+3+\\cdots+k+(k+1) = \\frac{(k+1)((k+1)+1)}{2}$')
			
			// 개별 문자로 분리된 수식 패턴들을 먼저 복원
			// n=1 패턴 (개별 문자로 분리된 경우)
			.replace(/(\w+)\s*=\s*(\d+)/g, (match, variable, num) => {
				if (/^[a-zA-Z]$/.test(variable) && /^\d+$/.test(num)) {
					return `$${variable}=${num}$`;
				}
				return match;
			})
			
			// k+1, n=k+1 패턴 (개별 문자로 분리된 경우)
			.replace(/([a-zA-Z])\s*\+\s*(\d+)/g, (match, variable, num) => {
				if (/^[a-zA-Z]$/.test(variable) && /^\d+$/.test(num)) {
					return `$${variable}+${num}$`;
				}
				return match;
			})
			.replace(/n\s*=\s*k\s*\+\s*1/g, '$n=k+1$')
			
			// 복잡한 수식 패턴들 (분리된 문자들을 복원)
			// 1+2+3+...+n 패턴
			.replace(/1\s*\+\s*2\s*\+\s*3\s*\+\s*\.\.\.\s*\+\s*n/g, '$1+2+3+\\cdots+n$')
			.replace(/1\s*\+\s*2\s*\+\s*3\s*\+\s*⋯\s*\+\s*n/g, '$1+2+3+\\cdots+n$')
			
			// 분수 패턴들 - k(k+1)/2, n(n+1)/2
			.replace(/k\s*\(\s*k\s*\+\s*1\s*\)\s*\/\s*2/g, '$\\frac{k(k+1)}{2}$')
			.replace(/n\s*\(\s*n\s*\+\s*1\s*\)\s*\/\s*2/g, '$\\frac{n(n+1)}{2}$')
			
			// (k+1)(k+2)/2 패턴  
			.replace(/\(\s*k\s*\+\s*1\s*\)\s*\(\s*k\s*\+\s*2\s*\)\s*\/\s*2/g, '$\\frac{(k+1)(k+2)}{2}$')
			.replace(/\(\s*k\s*\+\s*1\s*\)\s*\(\s*\(\s*k\s*\+\s*1\s*\)\s*\+\s*1\s*\)\s*\/\s*2/g, '$\\frac{(k+1)((k+1)+1)}{2}$')
			
			// k(k+1)+2(k+1) 패턴
			.replace(/k\s*\(\s*k\s*\+\s*1\s*\)\s*\+\s*2\s*\(\s*k\s*\+\s*1\s*\)/g, '$k(k+1)+2(k+1)$')
			.replace(/k\s*\(\s*k\s*\+\s*1\s*\)\/2\s*\+\s*\(\s*k\s*\+\s*1\s*\)/g, '$\\frac{k(k+1)}{2}+(k+1)$')
			
			// 일반적인 등식 패턴: 1+2+3+...+n = n(n+1)/2
			.replace(/([a-zA-Z0-9\+\-\(\)\s]+)\s*=\s*([a-zA-Z0-9\+\-\(\)\/\s]+)/g, (match, left, right) => {
				const cleanLeft = left.trim();
				const cleanRight = right.trim();
				
				// 양쪽 모두 수학 표현식인 경우 (문자가 포함된 경우)
				if (/[a-zA-Z]/.test(cleanLeft) && (/[a-zA-Z]/.test(cleanRight) || /[\/\(\)]/.test(cleanRight))) {
					return `$${cleanLeft} = ${cleanRight}$`;
				}
				return match;
			})
			
			// P(k), P(k+1) 등의 함수 표기법
			.replace(/\bP\s*\(\s*([^)]+)\s*\)/g, '$$P($1)$')
			
			// 일반적인 분수 패턴 (더 정교하게)
			.replace(/([a-zA-Z0-9\(\)\+\-\s]+)\s*\/\s*([a-zA-Z0-9\(\)\+\-\s]+)/g, (match, num, den) => {
				const cleanNum = num.trim();
				const cleanDen = den.trim();
				
				// 분자와 분모가 모두 수학적 표현인 경우만 변환
				if (/[a-zA-Z0-9\(\)\+\-]/.test(cleanNum) && /[a-zA-Z0-9\(\)\+\-]/.test(cleanDen)) {
					return `$\\frac{${cleanNum}}{${cleanDen}}$`;
				}
				return match;
			})
			
			// 변수와 괄호 표현식: n(n+1), k(k+1) 등
			.replace(/([a-zA-Z])\s*\(\s*([^)]+)\s*\)/g, (match, letter, expression) => {
				// 수학적 표현식인 경우만 변환
				const cleanExpr = expression.trim();
				if (/[a-zA-Z0-9\(\)\+\-\/\^\_]/.test(cleanExpr)) {
					return `$${letter}(${cleanExpr})$`;
				}
				return match;
			});
		
		// 2. 수학 문맥에서의 단일 변수들 처리 (더 신중하게)
		text = text.replace(/\b([a-zA-Z])\b/g, (match, letter) => {
			// 이미 $로 감싸진 변수는 건드리지 않음
			if (match.includes('$')) return match;
			
			// 앞뒤 문맥을 확인해서 수학적 문맥인지 판단
			const index = text.indexOf(match);
			const before = index > 0 ? text[index - 1] : '';
			const after = index + match.length < text.length ? text[index + match.length] : '';
			
			// 수학적 기호나 공백 앞뒤에 있는 경우
			const mathContext = ['+', '-', '=', '(', ')', '*', '/', '^', '_', '\n', ' '].includes(before) || 
							   ['+', '-', '=', '(', ')', '*', '/', '^', '_', '\n', ' '].includes(after);
			
			// 또한 이 변수가 문장의 시작이나 끝에 있지 않은 경우
			const notInText = !/^[a-zA-Z\s]/.test(text.substring(Math.max(0, index - 2), index + match.length + 2));
			
			if (mathContext || notInText) {
				return `$${letter}$`;
			}
			return match;
		});
		
		// 3. 임시 마커들을 원래 LaTeX로 복원
		Object.entries(markers).forEach(([marker, originalLatex]) => {
			text = text.replace(marker, originalLatex);
		});
		
		console.log('수학 표현식 변환 완료:', text.substring(0, 200) + '...');
		return text;
	}
	
	// KaTeX 렌더링된 HTML을 LaTeX로 역변환하는 함수
	function convertKaTeXToLatex(text: string): string {
		console.log('KaTeX 변환 시작 (HTML 포함):', text.substring(0, 500));
		
		// 1. 복잡한 KaTeX HTML 구조들을 더 포괄적으로 매칭
		// 블록 수식 (display mode) - 더 유연한 패턴
		text = text.replace(/<div[^>]*class="[^"]*katex-display[^"]*"[^>]*>([\s\S]*?)<\/div>/gi, (match, content) => {
			const latex = extractLatexFromKaTeXContent(content);
			return latex ? `$$${latex}$$` : match;
		});
		
		// 인라인 수식 - 더 유연한 패턴  
		text = text.replace(/<span[^>]*class="[^"]*katex[^"]*"[^>]*>([\s\S]*?)<\/span>/gi, (match, content) => {
			const latex = extractLatexFromKaTeXContent(content);
			return latex ? `$${latex}$` : match;
		});
		
		// 2. MathML에서 LaTeX 추출
		text = text.replace(/<math[^>]*>([\s\S]*?)<\/math>/gi, (match, mathml) => {
			const latex = extractLatexFromMathML(mathml);
			return latex ? latex : match;
		});
		
		// 3. KaTeX HTML 컨텐츠에서 직접 추출
		text = text.replace(/<span[^>]*class="[^"]*katex-html[^"]*"[^>]*>([\s\S]*?)<\/span>/gi, (match, html) => {
			const latex = extractLatexFromHTML(html);
			return latex ? `$${latex}$` : match;
		});
		
		// 4. MathLive 수식 필드
		text = text.replace(/<math-field[^>]*>([\s\S]*?)<\/math-field>/gi, (match, content) => {
			const latex = extractLatexFromMathField(content);
			return latex ? `$${latex}$` : match;
		});
		
		// 5. 일반적인 수학 기호들도 변환
		text = convertMathSymbolsToLatex(text);
		
		console.log('KaTeX 변환 완료:', text.substring(0, 200) + '...');
		return text;
	}
	
	// KaTeX 컨텐츠에서 LaTeX 추출하는 개선된 함수
	function extractLatexFromKaTeXContent(content: string): string | null {
		// MathML 부분에서 먼저 시도
		const mathmlMatch = content.match(/<math[^>]*>([\s\S]*?)<\/math>/i);
		if (mathmlMatch) {
			const latex = extractLatexFromMathML(mathmlMatch[1]);
			if (latex) return latex;
		}
		
		// HTML 부분에서 시도
		const htmlMatch = content.match(/<span[^>]*class="[^"]*katex-html[^"]*"[^>]*>([\s\S]*?)<\/span>/i);
		if (htmlMatch) {
			const latex = extractLatexFromHTML(htmlMatch[1]);
			if (latex) return latex;
		}
		
		// 전체 컨텐츠에서 HTML 태그 제거 후 추출
		const cleanedContent = content.replace(/<[^>]*>/g, '').replace(/&[^;]+;/g, ' ').trim();
		if (cleanedContent && /[a-zA-Z0-9\(\)\+\-\/\^\_]/.test(cleanedContent)) {
			return cleanedContent;
		}
		
		return null;
	}
	
	// 수학 기호를 LaTeX로 변환하는 함수
	function convertMathSymbolsToLatex(text: string): string {
		// 유니코드 수학 기호들을 LaTeX로 변환
		const symbolMap: { [key: string]: string } = {
			'π': '\\pi',
			'α': '\\alpha',
			'β': '\\beta',
			'γ': '\\gamma',
			'δ': '\\delta',
			'ε': '\\epsilon',
			'θ': '\\theta',
			'λ': '\\lambda',
			'μ': '\\mu',
			'σ': '\\sigma',
			'τ': '\\tau',
			'φ': '\\phi',
			'ω': '\\omega',
			'∞': '\\infty',
			'∑': '\\sum',
			'∏': '\\prod',
			'∫': '\\int',
			'√': '\\sqrt',
			'≤': '\\leq',
			'≥': '\\geq',
			'≠': '\\neq',
			'≈': '\\approx',
			'≡': '\\equiv',
			'±': '\\pm',
			'×': '\\times',
			'÷': '\\div',
			'→': '\\rightarrow',
			'←': '\\leftarrow',
			'↔': '\\leftrightarrow',
			'∈': '\\in',
			'∉': '\\notin',
			'⊂': '\\subset',
			'⊃': '\\supset',
			'∪': '\\cup',
			'∩': '\\cap',
			'∅': '\\emptyset',
			'∀': '\\forall',
			'∃': '\\exists',
			'∇': '\\nabla',
			'∂': '\\partial',
			'∆': '\\Delta',
			'∠': '\\angle',
			'⊥': '\\perp',
			'∥': '\\parallel',
			'∴': '\\therefore',
			'∵': '\\because',
			'ℕ': '\\mathbb{N}',
			'ℤ': '\\mathbb{Z}',
			'ℚ': '\\mathbb{Q}',
			'ℝ': '\\mathbb{R}',
			'ℂ': '\\mathbb{C}'
		};
		
		// 기호 변환
		for (const [symbol, latex] of Object.entries(symbolMap)) {
			text = text.replace(new RegExp(symbol, 'g'), latex);
		}
		
		// 첨자 변환
		text = text
			.replace(/([a-zA-Z0-9]+)²/g, '$1^2')
			.replace(/([a-zA-Z0-9]+)³/g, '$1^3')
			.replace(/([a-zA-Z0-9]+)₁/g, '$1_1')
			.replace(/([a-zA-Z0-9]+)₂/g, '$1_2')
			.replace(/([a-zA-Z0-9]+)₃/g, '$1_3');
		
		// 분수 변환
		text = text
			.replace(/([0-9]+)\/([0-9]+)/g, '\\frac{$1}{$2}')
			.replace(/([a-zA-Z]+)\/([a-zA-Z]+)/g, '\\frac{$1}{$2}');
		
		return text;
	}
	
	// MathLive 필드에서 LaTeX 추출
	function extractLatexFromMathField(content: string): string | null {
		try {
			// MathLive 필드의 value 속성에서 추출
			const valueMatch = content.match(/value="([^"]*)"/);
			if (valueMatch) {
				return valueMatch[1];
			}
			
			// 내부 텍스트에서 추출
			const latex = extractLatexFromHTML(content);
			return latex;
		} catch (error) {
			console.warn('MathLive 필드 변환 오류:', error);
			return null;
		}
	}
	
	// MathML에서 LaTeX 추출
	function extractLatexFromMathML(mathml: string): string | null {
		try {
			// 간단한 MathML 패턴 매칭으로 LaTeX 추출
			// 이는 기본적인 패턴만 처리하며, 완전한 변환은 아닙니다
			
			// 제곱: <msup><mi>x</mi><mn>2</mn></msup> -> x^2
			mathml = mathml.replace(/<msup><mi>([^<]*)<\/mi><mn>([^<]*)<\/mn><\/msup>/g, '$1^$2');
			mathml = mathml.replace(/<msup><mi>([^<]*)<\/mi><mi>([^<]*)<\/mi><\/msup>/g, '$1^$2');
			
			// 분수: <mfrac><mi>a</mi><mi>b</mi></mfrac> -> \frac{a}{b}
			mathml = mathml.replace(/<mfrac><mi>([^<]*)<\/mi><mi>([^<]*)<\/mi><\/mfrac>/g, '\\frac{$1}{$2}');
			mathml = mathml.replace(/<mfrac><mn>([^<]*)<\/mn><mn>([^<]*)<\/mn><\/mfrac>/g, '\\frac{$1}{$2}');
			
			// 제곱근: <msqrt><mi>x</mi></msqrt> -> \sqrt{x}
			mathml = mathml.replace(/<msqrt><mi>([^<]*)<\/mi><\/msqrt>/g, '\\sqrt{$1}');
			mathml = mathml.replace(/<msqrt><mn>([^<]*)<\/mn><\/msqrt>/g, '\\sqrt{$1}');
			
			// 기본 요소들
			mathml = mathml.replace(/<mi>([^<]*)<\/mi>/g, '$1');
			mathml = mathml.replace(/<mn>([^<]*)<\/mn>/g, '$1');
			mathml = mathml.replace(/<mo>([^<]*)<\/mo>/g, '$1');
			
			// HTML 태그 제거
			mathml = mathml.replace(/<[^>]*>/g, '');
			
			// 공백 정리
			mathml = mathml.replace(/\s+/g, ' ').trim();
			
			return mathml || null;
		} catch (error) {
			console.warn('MathML 변환 오류:', error);
			return null;
		}
	}
	
	// HTML에서 LaTeX 추출 (간단한 패턴 매칭)
	function extractLatexFromHTML(html: string): string | null {
		try {
			// HTML 태그 제거
			let latex = html.replace(/<[^>]*>/g, '');
			
			// HTML 엔티티 변환
			latex = latex
				.replace(/&lt;/g, '<')
				.replace(/&gt;/g, '>')
				.replace(/&amp;/g, '&')
				.replace(/&quot;/g, '"')
				.replace(/&#39;/g, "'")
				.replace(/&nbsp;/g, ' ');
			
			// 공백 정리
			latex = latex.replace(/\s+/g, ' ').trim();
			
			// 빈 문자열이면 null 반환
			if (!latex) return null;
			
			// 수학 기호 변환은 convertMathSymbolsToLatex에서 처리하므로 여기서는 기본적인 것만
			return latex;
		} catch (error) {
			console.warn('HTML 변환 오류:', error);
			return null;
		}
	}
	
	// 커서 위치에 텍스트 삽입 (LaTeX 수식을 수식 객체로 변환)
	async function insertTextAtCursor(text: string) {
		if (!editableElement || !browser) return;
		
		console.log('insertTextAtCursor 입력:', JSON.stringify(text.substring(0, 200)));
		
		const selection = window.getSelection();
		let range: Range;
		
		// 현재 커서가 입력 영역 내부에 있는지 확인
		let isCursorInInputArea = false;
		if (selection && selection.rangeCount > 0) {
			const currentRange = selection.getRangeAt(0);
			// 현재 선택의 컨테이너가 입력 영역 내부에 있는지 확인
			isCursorInInputArea = editableElement.contains(currentRange.startContainer) || 
								editableElement.contains(currentRange.commonAncestorContainer);
		}
		
		if (!selection || selection.rangeCount === 0 || !isCursorInInputArea) {
			// 선택 영역이 없거나 입력 영역 밖에 있으면 입력 영역 끝에 추가
			console.log('커서가 입력 영역 밖에 있거나 선택 영역이 없음 - 입력 영역 끝에 삽입');
			range = document.createRange();
			range.selectNodeContents(editableElement);
			range.collapse(false);
			
			// 입력 영역에 포커스 설정
			editableElement.focus();
		} else {
			range = selection.getRangeAt(0);
			console.log('현재 커서 위치에서 삽입:', {
				startContainer: range.startContainer,
				startOffset: range.startOffset,
				isInEditable: editableElement.contains(range.startContainer)
			});
		}
		
		// 현재 선택된 내용 삭제
		range.deleteContents();
		
		// LaTeX 패턴으로 분리 ($$...$$와 $...$ 모두 처리)
		const parts = text.split(/(\$\$[^$]+\$\$|\$[^$]+\$)/g);
		
		// 모든 노드를 생성하고 배열에 저장
		const nodesToInsert: Node[] = [];
		
		for (const part of parts) {
			if (part.startsWith('$$') && part.endsWith('$$')) {
				// 블록 수식 부분
				const latex = part.slice(2, -2).trim();
				if (latex) {
					try {
						const mathContainer = await createMathContainerForInsertion(latex);
						if (mathContainer) {
							nodesToInsert.push(mathContainer);
							// 수식 뒤에 공백 추가
							nodesToInsert.push(document.createTextNode(' '));
						}
					} catch (error) {
						console.warn('블록 수식 생성 실패:', error);
						nodesToInsert.push(document.createTextNode(part));
					}
				}
			} else if (part.startsWith('$') && part.endsWith('$')) {
				// 인라인 수식 부분
				const latex = part.slice(1, -1).trim();
				if (latex) {
					try {
						const mathContainer = await createMathContainerForInsertion(latex);
						if (mathContainer) {
							nodesToInsert.push(mathContainer);
							// 수식 뒤에 공백 추가
							nodesToInsert.push(document.createTextNode(' '));
						}
					} catch (error) {
						console.warn('인라인 수식 생성 실패:', error);
						nodesToInsert.push(document.createTextNode(part));
					}
				}
			} else if (part.trim()) {
				// 일반 텍스트 부분
				nodesToInsert.push(document.createTextNode(part));
			}
		}
		
		// 삽입할 노드 개수를 저장
		const nodeCount = nodesToInsert.length;
		
		// DocumentFragment에 모든 노드를 추가
		const fragment = document.createDocumentFragment();
		for (const node of nodesToInsert) {
			fragment.appendChild(node);
		}
		
		// 삽입 전 range 위치 저장
		const insertContainer = range.startContainer;
		const insertOffset = range.startOffset;
		
		// 한 번에 삽입
		range.insertNode(fragment);
		
		// 삽입 후 range 위치 조정
		if (nodeCount > 0) {
			// 삽입된 노드들의 마지막 위치를 찾아서 range 설정
			if (insertContainer.nodeType === Node.TEXT_NODE) {
				// 텍스트 노드인 경우
				const parent = insertContainer.parentNode;
				if (parent) {
					const nodeIndex = Array.from(parent.childNodes).indexOf(insertContainer as ChildNode);
					if (nodeIndex >= 0 && nodeIndex + nodeCount < parent.childNodes.length) {
						const lastInsertedNode = parent.childNodes[nodeIndex + nodeCount - 1];
						range.setStartAfter(lastInsertedNode);
						range.setEndAfter(lastInsertedNode);
					}
				}
			} else {
				// Element 노드인 경우
				if (insertContainer.childNodes.length >= insertOffset + nodeCount) {
					const lastInsertedNode = insertContainer.childNodes[insertOffset + nodeCount - 1];
					range.setStartAfter(lastInsertedNode);
					range.setEndAfter(lastInsertedNode);
				}
			}
			
			// 선택 영역 업데이트
			if (selection) {
				selection.removeAllRanges();
				selection.addRange(range);
			}
		}
		
		// 텍스트 값 업데이트
		updateTextValue();
	}
	
	// 이미지 업로드 관련 함수들
	async function handleImageUpload() {
		showImageMenu = !showImageMenu;
	}
	
	function handleImageFromFile() {
		showImageMenu = false;
		if (!imageInputFile) return;
		imageInputFile.click();
	}
	
	function handleImageFromCamera() {
		showImageMenu = false;
		dispatch('openCamera');
	}
	
	// 외부에서 호출할 수 있도록 export
	export function handleImageCropConfirm(event: CustomEvent<{ blob: Blob }>) {
		processImageCrop(event.detail.blob);
	}
	
	async function processImageCrop(blob: Blob) {
		console.log('크롭된 이미지 받음:', blob);
		
		// Blob을 File 객체로 변환
		const file = new File([blob], 'cropped-image.jpg', { type: 'image/jpeg' });
		
		// 이미지 변환 및 삽입
		await convertAndInsertImage(file);
	}
	
	async function convertAndInsertImage(file: File) {
		isConvertingImage = true;
		
		try {
			const { getMaiceAPIClient } = await import('$lib/api/maice-client');
			const apiClient = getMaiceAPIClient();
			
			console.log('이미지 변환 요청:', {
				filename: file.name,
				size: file.size,
				type: file.type
			});
			
			const result = await apiClient.convertImageToLatex(file);
			
			let latex = null;
			if (result.data && typeof result.data === 'object') {
				latex = result.data.latex;
			} else if (typeof result.data === 'string') {
				latex = result.data;
			}
			
			if (latex && latex.trim()) {
				const processedLatex = latex.replace(/\\n/g, '\n');
				await insertTextAtCursor(processedLatex);
			} else {
				alert('이미지에서 수학 공식을 찾을 수 없습니다.');
			}
		} catch (error) {
			console.error('이미지 변환 오류:', error);
			alert('이미지 변환 중 오류가 발생했습니다.');
		} finally {
			isConvertingImage = false;
		}
	}
	
	async function onImageSelected(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		
		if (!file) return;
		
		// 파일 형식 검증
		const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
		if (!allowedTypes.includes(file.type)) {
			alert('JPG, PNG, WebP 파일만 지원됩니다.');
			return;
		}
		
		// 파일 크기 검증 (10MB)
		const maxSize = 10 * 1024 * 1024;
		if (file.size > maxSize) {
			alert('파일 크기는 10MB 이하여야 합니다.');
			return;
		}
		
		// 파일을 Data URL로 변환하여 크롭 모달 표시
		const reader = new FileReader();
		reader.onload = (e) => {
			const imageUrl = e.target?.result as string;
			dispatch('openImageCrop', { imageUrl });
		};
		reader.readAsDataURL(file);
		
		// 파일 입력 초기화
		if (target) {
			target.value = '';
		}
	}
	
	
	// 텍스트만 삽입하는 함수 (수식 컨테이너 생성하지 않음)
	async function insertTextAtCursorAsText(text: string) {
		if (!editableElement || !browser) return;
		
		console.log('insertTextAtCursorAsText 입력:', JSON.stringify(text.substring(0, 200)));
		
		const selection = window.getSelection();
		let range: Range;
		
		if (!selection || selection.rangeCount === 0) {
			// 선택 영역이 없으면 끝에 추가
			range = document.createRange();
			range.selectNodeContents(editableElement);
			range.collapse(false);
		} else {
			range = selection.getRangeAt(0);
		}
		
		// 현재 선택된 내용 삭제
		range.deleteContents();
		
		// 텍스트 노드로 삽입
		const textNode = document.createTextNode(text);
		range.insertNode(textNode);
		
		// 커서를 삽입된 텍스트 뒤로 이동
		range.setStartAfter(textNode);
		range.setEndAfter(textNode);
		if (selection && selection.rangeCount >= 0) {
			selection.removeAllRanges();
			selection.addRange(range);
		}
		
		// 텍스트 값 업데이트
		updateTextValue();
	}

	// 수식 컨테이너만 생성하여 반환하는 함수 (insertTextAtCursor용)
	async function createMathContainerForInsertion(latex: string = '') {
		if (!browser || typeof window === 'undefined' || typeof document === 'undefined') return null;
		
		const mathId = `math-${++mathCounter}`;
		
		// 컨테이너 생성
		const mathContainer = document.createElement('span');
		mathContainer.className = 'inline-math-container';
		mathContainer.contentEditable = 'false';
		mathContainer.style.cssText = `
			display: inline-block;
			margin: 0 2px;
			vertical-align: middle;
			background: var(--maice-bg-secondary);
			border: 1px solid var(--maice-border-secondary);
			border-radius: 6px;
			padding: 4px 8px;
			min-width: 50px;
			min-height: 28px;
			cursor: pointer;
			position: relative;
		`;
		
		// MathLive 필드 생성
		const mathField = document.createElement('math-field') as MathfieldElement;
		mathField.id = mathId;
		mathField.value = latex;
		
		// 가상 키보드 수동 모드로 설정
		mathField.setAttribute('virtual-keyboard-mode', 'manual');
		
		mathField.style.cssText = `
			border: none;
			background: transparent;
			font-size: 14px;
			min-height: 20px;
			padding: 0;
			margin: 0;
			display: inline-block;
			width: auto;
			min-width: 30px;
		`;
		
		// MathLive 설정
		try {
			Object.assign(mathField, {
				defaultMode: 'math',
				placeholder: '?',
				virtualKeyboardMode: 'manual',
				smartMode: false,
				smartFence: true,
				smartSuperscript: true,
				keypressSound: null,
				readOnly: false,
				ignoreSpacebarInMathMode: true,
				removeExtraneousParentheses: false,
				renderAccessibleContent: false,
				useSharedVirtualKeyboard: true,
			});
		} catch (error) {
			console.log('MathLive 설정 오류:', error);
		}
		
		// 기본 이벤트 리스너 추가
		mathField.addEventListener('input', updateTextValue);
		
		// 포커스 이벤트 추가 (완전한 버전)
		mathField.addEventListener('focus', () => {
			// 포커스 전환 중이면 무시
			if (isTransitioning) {
				console.log('포커스 전환 중, focus 이벤트 무시:', mathField.id);
				mathField.blur();
				return;
			}
			
			// 중복 포커스 방지
			if (!handleDebouncedFocus(mathField)) {
				return;
			}
			
			console.log('수식 필드 포커스 설정:', mathField.id);
			isMathFieldFocused = true;
			currentMathField = mathField;
			
			// 가상 키보드 표시 (지연)
			focusDebounceTimer = setTimeout(() => {
				// 재검증: 여전히 포커스가 유효한지 확인
				if (!isForceClearingFocus && !isTransitioning && isMathFieldFocused && currentMathField === mathField) {
					if (safeMathLiveCall(mathField, 'showVirtualKeyboard')) {
						console.log('가상키보드 표시됨:', mathField.id);
						// 가상키보드 표시 후 스크롤
						setTimeout(() => {
							scrollForVirtualKeyboard();
						}, 200);
					}
				} else {
					console.log('포커스 상태 변경으로 가상키보드 표시 취소:', mathField.id);
				}
			}, 100);
		});
		
		mathField.addEventListener('blur', (e) => {
			// 포커스 전환 중이면 무시
			if (isTransitioning) {
				console.log('포커스 전환 중, blur 처리 생략:', mathField.id);
				return;
			}
			
			// 포커스 전환 중인지 재확인
			setTimeout(() => {
				if (isTransitioning) {
					console.log('포커스 전환 중 (재확인), blur 처리 생략:', mathField.id);
					return;
				}
				
				// 실제로 포커스가 해제되었는지 확인
				if (document.activeElement !== mathField) {
					console.log('수식 필드 포커스 해제 (blur 이벤트):', mathField.id);
					
					// 포커스 상태가 이미 해제되었는지 확인
					if (!isMathFieldFocused) {
						console.log('이미 포커스 해제됨, 중복 처리 방지');
						return;
					}
					
					isMathFieldFocused = false;
					currentMathField = null;
					
					// 가상 키보드 자동 숨기기
					try {
						safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					} catch (e) {
						console.log('가상 키보드 숨기기 실패:', e);
					}
					
					// 빈 수식 필드 제거
					if (!mathField.value.trim()) {
						mathContainer.remove();
						updateTextValue();
					}
				}
			}, 100);
		});
		
		// 컨테이너 클릭 이벤트
		mathContainer.addEventListener('click', (e) => {
			e.preventDefault();
			e.stopPropagation();
		});
		
		mathContainer.appendChild(mathField);
		
		return mathContainer;
	}

	// contenteditable 입력 처리
	function handleEditableInput() {
		updateTextValue();
	}

	// contenteditable 클릭 처리 - 수식 주변 클릭 시 올바른 커서 위치 설정
	function handleEditableClick(event: MouseEvent) {
		if (!browser || typeof window === 'undefined' || typeof document === 'undefined') return;
		
		// 클릭된 요소가 수식 관련 요소인지 더 정확하게 확인
		const target = event.target as Element;
		
		// 가상 키보드 클릭인지 확인
		const isVirtualKeyboardClick = !!(
			target.closest?.('.ML__virtual-keyboard') ||
			target.closest?.('.mathlive-virtual-keyboard') ||
			target.closest?.('[data-mathlive-virtual-keyboard]') ||
			target.closest?.('.ML__keyboard') ||
			target.closest?.('.ML__popover') ||
			target.classList?.contains('ML__keyboard') ||
			target.classList?.contains('ML__keycap') ||
			target.classList?.contains('ML__key') ||
			target.classList?.contains('ML__popover')
		);
		
		// 가상 키보드 클릭이면 포커스 해제하지 않고 이벤트 계속 처리
		if (isVirtualKeyboardClick) {
			console.log('가상 키보드 클릭 감지 - 포커스 유지, 이벤트 처리 계속');
			// return하지 않고 계속 진행해서 이벤트가 정상 처리되도록 함
		}
		
		const isMathRelated = !!(
			target.classList?.contains('inline-math-container') || 
			target.closest?.('.inline-math-container') ||
			target.tagName === 'MATH-FIELD' ||
			target.closest?.('math-field') ||
			target.classList?.contains('math-button') ||
			target.closest?.('.math-button') ||
			target.classList?.contains('image-upload-button') ||
			target.closest?.('.image-upload-button') ||
			target.classList?.contains('send-button') ||
			target.closest?.('.send-button')
		);
		
		console.log('editable 클릭 감지:', {
			isMathRelated,
			isMathFieldFocused,
			target: target.tagName,
			className: target.className
		});
		
		// 수식 관련 요소가 아니고 가상 키보드 클릭도 아닌 텍스트 영역을 클릭한 경우 포커스 해제
		if (!isMathRelated && !isVirtualKeyboardClick && (isMathFieldFocused || currentMathField)) {
			console.log('editable 클릭으로 포커스 해제');
			// 입력창 포커스는 유지하고 수식 필드만 포커스 해제
			forceClearMathFocus();
		}
		
		// 클릭 위치 기반으로 올바른 커서 위치 설정
		setTimeout(() => {
			const selection = window.getSelection();
			if (selection && selection.rangeCount > 0) {
				const range = selection.getRangeAt(0);
				
				// 수식 컨테이너 바로 뒤를 클릭한 경우 처리
				if (range.startContainer.nodeType === Node.ELEMENT_NODE) {
					const element = range.startContainer as Element;
					if (element === editableElement) {
						// contenteditable 내에서 직접 클릭한 경우
						const childNodes = Array.from(editableElement.childNodes);
						const clickedIndex = range.startOffset;
						
						if (clickedIndex < childNodes.length) {
							const clickedNode = childNodes[clickedIndex];
							if (clickedNode.nodeType === Node.ELEMENT_NODE) {
								const clickedElement = clickedNode as Element;
								if (clickedElement.classList.contains('inline-math-container')) {
									// 수식 컨테이너를 클릭한 경우, 수식 뒤로 커서 이동
									const newRange = document.createRange();
									newRange.setStart(editableElement, clickedIndex + 1);
									newRange.collapse(true);
									selection.removeAllRanges();
									selection.addRange(newRange);
								}
							}
						}
					}
				}
			}
		}, 10);
	}

	// 한글 조합 시작 감지
	function handleCompositionStart(event: CompositionEvent) {
		isComposing = true;
	}

	// 한글 조합 완료 감지
	function handleCompositionEnd(event: CompositionEvent) {
		isComposing = false;
		// 조합 완료 후 값 업데이트
		setTimeout(() => {
			updateTextValue();
		}, 0);
	}

	// 키보드 이벤트 처리
	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			
			console.log('🔤 엔터키 감지 - 조합 상태:', isComposing, '현재 값:', value);
			
			// 조합 중이면 조합을 완료시키기 위해 잠시 대기
			if (isComposing) {
				console.log('⏳ 조합 중... 완료 대기');
				// 조합 완료를 위해 약간의 대기 후 재시도
				setTimeout(() => {
					console.log('🔄 조합 완료 후 재시도, 값:', value);
					if (value.trim() && !disabled && !isLoading) {
						dispatch('send', { message: value.trim() });
						// 입력창 초기화
						if (editableElement) {
							editableElement.innerHTML = '';
						}
						value = '';
						isMathFieldFocused = false;
						currentMathField = null;
					}
				}, 100);
			} else {
				// 조합 중이 아니면 바로 전송
				console.log('✅ 바로 전송, 값:', value);
				handleSend();
			}
		} else if (event.key === 'Backspace') {
			// 백스페이스로 수식 삭제 처리 (데스크톱용)
			handleBackspaceDelete(event);
		}
	}
	
	// 모바일 입력 이벤트 처리 (beforeinput - 모바일에서 더 안정적)
	function handleBeforeInput(event: InputEvent) {
		// deleteContentBackward는 백스페이스를 의미
		if (event.inputType === 'deleteContentBackward') {
			console.log('📱 모바일 백스페이스 감지 (beforeinput)');
			const handled = handleBackspaceDelete(event as any);
			if (handled) {
				console.log('✅ 수식 삭제 처리 완료');
			}
		}
	}

	// 백스페이스로 수식 삭제 처리 (데스크톱 & 모바일 공통)
	function handleBackspaceDelete(event: KeyboardEvent | InputEvent): boolean {
		if (!browser || typeof window === 'undefined') return false;
		
		try {
			const selection = window.getSelection();
			if (!selection || selection.rangeCount === 0) {
				console.log('⚠️ selection이 없음');
				return false;
			}
			
			const range = selection.getRangeAt(0);
			if (!range || !range.collapsed) {
				console.log('⚠️ range가 없거나 collapsed 상태가 아님');
				return false; // 선택 영역이 있으면 기본 동작
			}
			
			// 커서 바로 앞에 수식이 있는지 확인
			const cursorNode = range.startContainer;
			const cursorOffset = range.startOffset;
			
			console.log('🔍 백스페이스 처리:', {
				nodeType: cursorNode.nodeType,
				nodeName: cursorNode.nodeName,
				offset: cursorOffset,
				isTextNode: cursorNode.nodeType === Node.TEXT_NODE,
				isEditableElement: cursorNode === editableElement
			});
			
			// 텍스트 노드에서 커서가 맨 앞에 있는 경우
			if (cursorNode.nodeType === Node.TEXT_NODE && cursorOffset === 0) {
				const prevSibling = cursorNode.previousSibling;
				console.log('📝 텍스트 노드 시작 위치, 이전 sibling:', prevSibling?.nodeName);
				
				if (prevSibling && prevSibling.nodeType === Node.ELEMENT_NODE) {
					const element = prevSibling as Element;
					if (element.classList.contains('inline-math-container')) {
						console.log('✅ 수식 컨테이너 발견, 삭제 진행');
						// 앞의 수식 컨테이너 삭제
						event.preventDefault();
						
						// 포커스 상태 초기화 (삭제되는 수식이 현재 포커스된 수식인 경우)
						if (currentMathField && element.contains(currentMathField)) {
							isMathFieldFocused = false;
							currentMathField = null;
						}
						
						element.remove();
						updateTextValue();
						return true;
					}
				}
			}
			
			// contenteditable div에서 커서 앞에 수식이 있는 경우
			if (cursorNode === editableElement && cursorOffset > 0) {
				const childNodes = Array.from(editableElement.childNodes);
				const prevNode = childNodes[cursorOffset - 1];
				
				console.log('📝 contenteditable 직접 위치, 이전 node:', prevNode?.nodeName);
				
				if (prevNode && prevNode.nodeType === Node.ELEMENT_NODE) {
					const element = prevNode as Element;
					if (element.classList.contains('inline-math-container')) {
						console.log('✅ 수식 컨테이너 발견, 삭제 진행');
						// 앞의 수식 컨테이너 삭제
						event.preventDefault();
						
						// 포커스 상태 초기화 (삭제되는 수식이 현재 포커스된 수식인 경우)
						if (currentMathField && element.contains(currentMathField)) {
							isMathFieldFocused = false;
							currentMathField = null;
						}
						
						element.remove();
						updateTextValue();
						
						// 커서 위치 조정
						const newRange = document.createRange();
						newRange.setStart(editableElement, cursorOffset - 1);
						newRange.collapse(true);
						selection.removeAllRanges();
						selection.addRange(newRange);
						return true;
					}
				}
			}
			
			// 텍스트 노드 중간에서 백스페이스 - 부모를 통해 이전 형제 확인
			if (cursorNode.nodeType === Node.TEXT_NODE && cursorOffset === 0) {
				let parent = cursorNode.parentNode;
				while (parent && parent !== editableElement) {
					const prevSibling = parent.previousSibling;
					if (prevSibling && prevSibling.nodeType === Node.ELEMENT_NODE) {
						const element = prevSibling as Element;
						if (element.classList.contains('inline-math-container')) {
							console.log('✅ 부모 경로를 통해 수식 컨테이너 발견, 삭제 진행');
							event.preventDefault();
							
							if (currentMathField && element.contains(currentMathField)) {
								isMathFieldFocused = false;
								currentMathField = null;
							}
							
							element.remove();
							updateTextValue();
							return true;
						}
					}
					parent = parent.parentNode;
				}
			}
			
			console.log('ℹ️ 수식 삭제 조건 불충족, 기본 동작');
			return false;
		} catch (error) {
			console.error('❌ 백스페이스 처리 중 오류:', error);
			return false;
		}
	}

	// 전송 처리
	function handleSend() {
		console.log('🔤 전송 버튼 클릭 - 조합 상태:', isComposing, '현재 값:', value);
		
		// 조합 중이면 조합을 완료시키기 위해 잠시 대기
		if (isComposing) {
			console.log('⏳ 버튼 클릭 시 조합 중... 완료 대기');
			// 조합 완료를 위해 약간의 대기 후 재시도
			setTimeout(() => {
				console.log('🔄 버튼 클릭 조합 완료 후 재시도, 값:', value);
				if (value.trim() && !disabled && !isLoading) {
					dispatch('send', { message: value.trim() });
					// 입력창 초기화
					if (editableElement) {
						editableElement.innerHTML = '';
					}
					value = '';
					isMathFieldFocused = false;
					currentMathField = null;
				}
			}, 100);
		} else {
			// 조합 중이 아니면 바로 전송
			if (value.trim() && !disabled && !isLoading) {
				dispatch('send', { message: value.trim() });
				
				// 포커스 상태 초기화
				isMathFieldFocused = false;
				currentMathField = null;
				
				// 입력창 초기화
				if (editableElement) {
					editableElement.innerHTML = '';
				}
				value = '';
			}
		}
	}

	// 컴포넌트 마운트시 초기값 설정
	onMount(() => {
		if (browser && value) {
			// 초기 값이 있는 경우 LaTeX 파싱해서 표시
			setTimeout(() => {
				parseAndDisplayContent(value);
			}, 100);
		}
		
		// 전역 클릭 이벤트 리스너 추가 - 수식 외부 클릭 시 포커스 해제 및 이미지 메뉴 닫기
		let isClearingFocus = false; // 포커스 해제 중 플래그
		let lastFocusCheck = false; // 마지막 포커스 상태 저장
		
		const handleGlobalClick = (event: MouseEvent) => {
			const target = event.target as Element;
			
			// 이미지 메뉴 외부 클릭 시 메뉴 닫기
			if (showImageMenu) {
				const isImageMenuClick = !!(
					target.closest?.('.image-menu') ||
					target.closest?.('.image-upload-button')
				);
				if (!isImageMenuClick) {
					showImageMenu = false;
				}
			}
			
			// 이미 포커스 해제 중이면 중복 실행 방지
			if (isClearingFocus) return;
			
			const isInsideInput = editableElement && editableElement.contains(target);
			
			// 가상 키보드 클릭인지 확인
			const isVirtualKeyboardClick = !!(
				target.closest?.('.ML__virtual-keyboard') ||
				target.closest?.('.mathlive-virtual-keyboard') ||
				target.closest?.('[data-mathlive-virtual-keyboard]') ||
				target.closest?.('.ML__keyboard') ||
				target.closest?.('.ML__popover') ||
				target.classList?.contains('ML__keyboard') ||
				target.classList?.contains('ML__keycap') ||
				target.classList?.contains('ML__key') ||
				target.classList?.contains('ML__popover')
			);
			
			// 수식 관련 요소인지 더 정확하게 확인 (수식 버튼 포함)
			const isMathRelated = !!(
				target.classList?.contains('inline-math-container') || 
				target.closest?.('.inline-math-container') ||
				target.tagName === 'MATH-FIELD' ||
				target.closest?.('math-field') ||
				target.classList?.contains('math-button') ||
				target.closest?.('.math-button') ||
				target.classList?.contains('image-upload-button') ||
				target.closest?.('.image-upload-button') ||
				target.classList?.contains('send-button') ||
				target.closest?.('.send-button') ||
				isVirtualKeyboardClick
			);
			
			// 현재 실제 포커스 상태를 DOM에서 직접 확인
			const hasActiveMathField = document.activeElement && document.activeElement.tagName === 'MATH-FIELD';
			const shouldClearFocus = hasActiveMathField || isMathFieldFocused || currentMathField !== null;
			
			console.log('전역 클릭 감지:', {
				isInsideInput,
				isMathRelated,
				isMathFieldFocused,
				hasActiveMathField,
				shouldClearFocus,
				currentMathField: currentMathField?.id || null,
				target: target.tagName,
				className: target.className
			});
			
			// 수식과 관련 없는 곳을 클릭했고, 포커스 해제가 필요한 경우
			if (!isMathRelated && shouldClearFocus && !isClearingFocus) {
				console.log('전역 클릭으로 포커스 해제 시작');
				isClearingFocus = true;
				
				// 모든 포커스 관련 타이머 클리어
				if (focusDebounceTimer) {
					clearTimeout(focusDebounceTimer);
					focusDebounceTimer = null;
				}
				
				forceClearMathFocus();
				
				// 포커스 해제 완료 후 플래그 리셋 (더 긴 지연)
				setTimeout(() => {
					isClearingFocus = false;
				}, 500);
			} else if (isMathRelated) {
				console.log('수식 관련 영역 클릭, 포커스 해제 생략');
			} else if (!shouldClearFocus) {
				console.log('포커스 해제 불필요');
			}
		};
		
		document.addEventListener('click', handleGlobalClick);
		
		// 컴포넌트 정리 시 이벤트 리스너 제거
		return () => {
			document.removeEventListener('click', handleGlobalClick);
		};
	});

	// LaTeX 포함 텍스트를 파싱해서 표시
	async function parseAndDisplayContent(text: string) {
		if (!editableElement || !browser || typeof window === 'undefined') return;
		
		try {
			editableElement.innerHTML = '';
			
			// LaTeX 패턴으로 분리
			const parts = text.split(/(\$[^$]+\$)/g);
			
			for (const part of parts) {
				if (part.startsWith('$') && part.endsWith('$')) {
					// LaTeX 수식 부분
					const latex = part.slice(1, -1);
					await createInlineMathField(latex);
				} else if (part.trim()) {
					// 일반 텍스트 부분
					const textNode = document.createTextNode(part);
					editableElement.appendChild(textNode);
				}
			}
		} catch (error) {
			console.error('콘텐츠 파싱 오류:', error);
		}
	}

	// 인라인 MathLive 필드 생성
	async function createInlineMathField(latex: string = '') {
		if (!browser || typeof window === 'undefined' || typeof document === 'undefined') return;
		const mathId = `math-${++mathCounter}`;
		
		// 컨테이너 생성
		const mathContainer = document.createElement('span');
		mathContainer.className = 'inline-math-container';
		mathContainer.contentEditable = 'false'; // 수식 영역은 편집 불가
		mathContainer.style.cssText = `
			display: inline-block;
			margin: 0 2px;
			vertical-align: middle;
			background: var(--maice-bg-secondary);
			border: 1px solid var(--maice-border-secondary);
			border-radius: 6px;
			padding: 4px 8px;
			min-width: 50px;
			min-height: 28px;
			cursor: pointer;
			position: relative;
		`;
		
		// MathLive 필드 생성
		const mathField = document.createElement('math-field') as MathfieldElement;
		mathField.id = mathId;
		mathField.value = latex;
		
		// 가상 키보드 수동 모드로 설정
		mathField.setAttribute('virtual-keyboard-mode', 'manual');
		
		mathField.style.cssText = `
			border: none;
			background: transparent;
			font-size: 14px;
			min-height: 20px;
			padding: 0;
			margin: 0;
			display: inline-block;
			width: auto;
			min-width: 30px;
		`;
		
		// MathLive 설정 (순수 수식 모드)
		try {
			Object.assign(mathField, {
				defaultMode: 'math',
				placeholder: '?',
				virtualKeyboardMode: 'manual', // 일관된 설정
				smartMode: false,
				smartFence: true,
				smartSuperscript: true,
				keypressSound: null,
				readOnly: false,
				// 추가 안정성 설정
				ignoreSpacebarInMathMode: true,
				removeExtraneousParentheses: false,
				// 렌더링 안정성 설정
				renderAccessibleContent: false, // 접근성 콘텐츠 렌더링 비활성화
				useSharedVirtualKeyboard: true, // 공유 가상 키보드 사용
			});
		} catch (error) {
			console.log('MathLive 설정 오류:', error);
		}
		
		// 기본 input 이벤트
		mathField.addEventListener('input', updateTextValue);
		
		// 수식 필드에서 포커스 이동을 위한 키보드 이벤트
		mathField.addEventListener('keydown', (e) => {
			// 화살표 키 처리 - 올바른 MathLive API 사용
			if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
				try {
					// MathLive의 position과 selection ranges를 사용하여 정확한 위치 확인
					const selection = mathField.selection;
					const position = mathField.position ?? 0;
					const value = mathField.value || '';
					
					// selection.ranges는 [[start, end]] 형태의 배열
					const ranges = selection?.ranges || [[0, 0]];
					const [start, end] = ranges[0] || [0, 0];
					
					console.log('화살표 키 처리:', {
						key: e.key,
						position,
						start,
						end,
						valueLength: value.length
					});
					
					// 오른쪽 화살표 키: 커서가 끝에 있을 때 다음 텍스트 영역으로 이동
					if (e.key === 'ArrowRight') {
						// end가 value 길이와 같거나, position이 끝에 도달했는지 확인
						if (end >= value.length || position >= value.length) {
							console.log('수식 끝에 도달 - 다음 텍스트 영역으로 이동');
							e.preventDefault();
							
							// 전환 중 플래그 설정하여 재포커스 방지
							isTransitioning = true;
							isMathFieldFocused = false;
							currentMathField = null;
							
							// 가상 키보드 숨기기
							try {
								safeMathLiveCall(mathField, 'hideVirtualKeyboard');
							} catch (err) {
								console.log('가상 키보드 숨기기 실패:', err);
							}
							
							// 포커스 이동
							mathField.blur();
							setTimeout(() => {
								moveToNextTextPosition(mathContainer);
								isTransitioning = false;
							}, 50);
							return;
						}
					}
					// 왼쪽 화살표 키: 커서가 시작에 있을 때 이전 텍스트 영역으로 이동
					if (e.key === 'ArrowLeft') {
						if (start <= 0 || position <= 0) {
							console.log('수식 시작에 도달 - 이전 텍스트 영역으로 이동');
							e.preventDefault();
							
							// 전환 중 플래그 설정하여 재포커스 방지
							isTransitioning = true;
							isMathFieldFocused = false;
							currentMathField = null;
							
							// 가상 키보드 숨기기
							try {
								safeMathLiveCall(mathField, 'hideVirtualKeyboard');
							} catch (err) {
								console.log('가상 키보드 숨기기 실패:', err);
							}
							
							// 포커스 이동
							mathField.blur();
							setTimeout(() => {
								moveToPreviousTextPosition(mathContainer);
								isTransitioning = false;
							}, 50);
							return;
						}
					}
				} catch (error) {
					console.log('MathLive API 호출 실패, 기본 동작 허용:', error);
					return;
				}
			}
			
			// Tab 키: 다음 요소로 포커스 이동
			if (e.key === 'Tab') {
				e.preventDefault();
				e.stopPropagation();
				if (e.shiftKey) {
					moveToPreviousTextPosition(mathContainer);
				} else {
					moveToNextTextPosition(mathContainer);
				}
				return;
			}
			// Escape 키: 수식 편집 종료하고 텍스트 영역으로 포커스
			if (e.key === 'Escape') {
				e.preventDefault();
				e.stopPropagation();
				
				// 전환 중 플래그 설정
				isTransitioning = true;
				
				// 상태 즉시 업데이트
				isMathFieldFocused = false;
				currentMathField = null;
				
				// 가상 키보드 숨기기
				try {
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
				} catch (e) {
					console.log('가상 키보드 숨기기 실패:', e);
				}
				
				// 포커스 제거
				mathField.blur();
				
				// 텍스트 영역으로 포커스 이동
				setTimeout(() => {
					editableElement.focus();
					// 수식 뒤에 커서 위치
					const mathIndex = Array.from(editableElement.childNodes).indexOf(mathContainer);
					if (mathIndex !== -1) {
						const range = document.createRange();
						range.setStart(editableElement, mathIndex + 1);
						range.collapse(true);
						const selection = window.getSelection();
						selection?.removeAllRanges();
						selection?.addRange(range);
					}
					
					// 전환 완료
					isTransitioning = false;
				}, 50);
				return;
			}
			
			// 추가: Enter 키로도 수식에서 빠져나올 수 있도록
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				e.stopPropagation();
				
				// 전환 중 플래그 설정
				isTransitioning = true;
				
				// 상태 즉시 업데이트
				isMathFieldFocused = false;
				currentMathField = null;
				
				// 가상 키보드 숨기기
				try {
					safeMathLiveCall(mathField, 'hideVirtualKeyboard');
				} catch (e) {
					console.log('가상 키보드 숨기기 실패:', e);
				}
				
				// 포커스 제거 후 다음 위치로 이동
				mathField.blur();
				
				setTimeout(() => {
					moveToNextTextPosition(mathContainer);
					// 전환 완료
					isTransitioning = false;
				}, 50);
				return;
			}
		});
		
		// 수식 필드 포커스 추적 (디바운스 처리)
		mathField.addEventListener('focus', () => {
			// 전환 중이면 포커스 무시
			if (isTransitioning) {
				console.log('포커스 전환 중, focus 이벤트 무시:', mathField.id);
				mathField.blur();
				return;
			}
			
			// 디바운스된 포커스 처리
			if (!handleDebouncedFocus(mathField)) {
				return;
			}
			
			console.log('수식 필드 포커스 설정:', mathField.id);
			isMathFieldFocused = true;
			currentMathField = mathField;
			
			// 디바운스 타이머 클리어
			if (focusDebounceTimer) {
				clearTimeout(focusDebounceTimer);
			}
			
			// 가상 키보드 표시를 디바운스 처리
			focusDebounceTimer = setTimeout(() => {
				// 재검증: 여전히 포커스가 유효한지 확인
				if (!isForceClearingFocus && !isTransitioning && isMathFieldFocused && currentMathField === mathField) {
					if (safeMathLiveCall(mathField, 'showVirtualKeyboard')) {
						console.log('가상키보드 표시됨:', mathField.id);
						// 가상키보드 표시 후 스크롤
						setTimeout(() => {
							scrollForVirtualKeyboard();
						}, 200);
					}
				} else {
					console.log('포커스 상태 변경으로 가상키보드 표시 취소:', mathField.id);
				}
				focusDebounceTimer = null;
			}, 150);
		});
		
		// 수식 필드에서 포커스가 나갈 때 처리
		mathField.addEventListener('blur', (e) => {
			// 전환 중이면 처리하지 않음
			if (isTransitioning) {
				console.log('포커스 전환 중, blur 처리 생략:', mathField.id);
				return;
			}
			
			// 현재 포커스된 필드가 아니면 처리하지 않음
			if (currentMathField !== mathField) {
				console.log('다른 필드의 blur 이벤트, 처리 생략:', mathField.id);
				return;
			}
			
			// 지연 후 포커스 상태 확인
			setTimeout(() => {
				// 현재 활성 요소가 이 수식 필드가 아니고, 강제 해제 중이 아닐 때만 해제
				if (document.activeElement !== mathField && !isForceClearingFocus && currentMathField === mathField) {
					console.log('수식 필드 포커스 해제 (blur 이벤트):', mathField.id);
					
					// 이미 포커스가 해제된 상태라면 추가 처리하지 않음
					if (!isMathFieldFocused) {
						console.log('이미 포커스가 해제된 상태, 추가 처리 생략');
						return;
					}
					
					isMathFieldFocused = false;
					currentMathField = null;
					
					// 가상 키보드 자동 숨기기
					try {
						safeMathLiveCall(mathField, 'hideVirtualKeyboard');
					} catch (e) {
						console.log('가상 키보드 숨기기 실패:', e);
					}
					
					// 빈 수식이면 제거 (안전한 값 확인)
					const fieldValue = safeMathLiveCall(mathField, 'value', '');
					if (!fieldValue || !fieldValue.trim()) {
						mathContainer.remove();
						updateTextValue();
					}
				} else {
					console.log('blur 처리 조건 불충족:', {
						activeElement: document.activeElement?.tagName,
						isForceClearingFocus,
						currentMathField: currentMathField?.id,
						mathFieldId: mathField.id
					});
				}
			}, 100);
		});
		
		// 수식 컨테이너 클릭 처리 - 더블클릭 시에만 포커스
		mathContainer.addEventListener('click', (e) => {
			// 단일 클릭은 포커스하지 않고, 더블클릭이나 키보드로만 포커스
			e.preventDefault();
			e.stopPropagation();
			e.stopImmediatePropagation();
			
			// 수식 필드에 포커스하지 않음 - 더블클릭이나 키보드 입력 시에만 포커스
		});
		
		mathContainer.appendChild(mathField);
		editableElement.appendChild(mathContainer);
		
		// 수식 뒤에 공백 문자 삽입 (나중에 백스페이스로 제거 가능하도록)
		const spaceText = document.createTextNode(' ');
		editableElement.appendChild(spaceText);
		
		return mathField;
	}

	// 컴포넌트 정리
	onDestroy(() => {
		// 디바운스 타이머 정리
		if (focusDebounceTimer) {
			clearTimeout(focusDebounceTimer);
			focusDebounceTimer = null;
		}
		
		// 모든 MathLive 필드 정리
		const mathFields = editableElement?.querySelectorAll('math-field');
		mathFields?.forEach(field => {
			field.remove();
		});
	});
</script>

<div class="inline-math-input-container">
	<!-- 도구 메뉴 (호버 시 표시) -->
	<div 
		class="tool-menu" 
		class:show={showToolMenu}
		role="toolbar"
		aria-label="수식, 이미지 및 전송 도구"
		tabindex="-1"
		onmouseenter={showToolMenuHandler}
		onmouseleave={hideToolMenuHandler}
		ontouchstart={handleTouchStart}
		ontouchend={handleTouchEnd}
	>
		<!-- 수식 삽입/가상키보드 토글 버튼 -->
		<button 
			class="tool-button math-button" 
			class:keyboard-mode={isMathFieldFocused}
			onclick={insertMathAtCursor}
			title={isMathFieldFocused ? "가상 키보드 토글 (수식 편집 모드)" : "수식 삽입 (∑, ∫, √ 등)"}
			disabled={disabled || isConvertingImage}
		>
			{#if isMathFieldFocused}
				<!-- 가상 키보드 아이콘 -->
				<svg class="math-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
					<line x1="8" y1="21" x2="16" y2="21"/>
					<line x1="12" y1="17" x2="12" y2="21"/>
					<path d="M6 7h.01M10 7h.01M14 7h.01M18 7h.01M6 11h.01M10 11h.01M14 11h.01M18 11h.01"/>
				</svg>
				<span class="tool-label">키보드</span>
			{:else}
				<!-- 수식 아이콘 -->
				<svg class="math-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M9 7H6a2 2 0 00-2 2v6a2 2 0 002 2h3m6 0h3a2 2 0 002-2V9a2 2 0 00-2-2h-3m-6 0V4a2 2 0 012-2h2a2 2 0 012 2v3m-6 0h6"/>
					<text x="8" y="12" font-size="6" fill="currentColor" font-family="serif">∑</text>
				</svg>
				<span class="tool-label">수식</span>
			{/if}
		</button>
		
		<!-- 이미지 업로드 버튼 -->
		<button 
			class="tool-button image-upload-button" 
			onclick={handleImageUpload}
			disabled={disabled || isConvertingImage}
			title="이미지에서 수식 변환"
		>
			{#if isConvertingImage}
				<svg class="loading-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M21 12a9 9 0 11-6.219-8.56"/>
				</svg>
				<span class="tool-label">변환중</span>
			{:else}
				<svg class="image-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
					<circle cx="8.5" cy="8.5" r="1.5"/>
					<polyline points="21,15 16,10 5,21"/>
				</svg>
				<span class="tool-label">이미지</span>
			{/if}
		</button>
		
		<!-- 전송 버튼 -->
		<button 
			class="tool-button send-button" 
			onclick={handleSend}
			disabled={disabled || isLoading || !value.trim() || isConvertingImage}
			title="메시지 전송"
		>
			{#if isLoading}
				<svg class="loading-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M21 12a9 9 0 11-6.219-8.56"/>
				</svg>
				<span class="tool-label">전송중</span>
			{:else}
				<svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
				</svg>
				<span class="tool-label">전송</span>
			{/if}
		</button>
	</div>
	
	<!-- 메인 입력 영역 -->
	<div 
		class="input-area"
		role="textbox"
		aria-label="메시지 입력 영역"
		tabindex="-1"
		onmouseenter={showToolMenuHandler}
		onmouseleave={hideToolMenuHandler}
		ontouchstart={handleTouchStart}
		ontouchend={handleTouchEnd}
	>
		<!-- contenteditable div로 텍스트와 수식 통합 -->
		<div
			bind:this={editableElement}
			contenteditable={!disabled && !isConvertingImage}
			class="editable-input"
			class:disabled={disabled || isConvertingImage}
			data-placeholder={placeholder}
			oninput={handleEditableInput}
			onbeforeinput={handleBeforeInput}
			onkeydown={handleKeyDown}
			onclick={handleEditableClick}
			onpaste={handlePaste}
			oncompositionstart={handleCompositionStart}
			oncompositionend={handleCompositionEnd}
			onfocus={() => {
				console.log('입력창 포커스됨');
			}}
			role="textbox"
			aria-multiline="true"
			tabindex="0"
		>
		</div>
		
		<!-- 변환 중 메시지 (입력창 외부에 오버레이) -->
		{#if isConvertingImage}
			<div class="converting-message">
				이미지를 수식으로 변환 중입니다...
			</div>
		{/if}
	</div>
	
	<!-- 데스크톱용 버튼 영역 (768px 이상에서만 표시) -->
	<div class="desktop-button-area">
		<!-- 왼쪽 버튼 그룹 (수식, 이미지) -->
		<div class="left-button-group">
			<!-- 수식 삽입/가상키보드 토글 버튼 -->
			<button 
				class="desktop-button math-button" 
				class:keyboard-mode={isMathFieldFocused}
				onclick={insertMathAtCursor}
				title={isMathFieldFocused ? "가상 키보드 토글 (수식 편집 모드)" : "수식 삽입 (∑, ∫, √ 등)"}
				disabled={disabled || isConvertingImage}
			>
				{#if isMathFieldFocused}
					<!-- 가상 키보드 아이콘 -->
					<svg class="math-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
						<line x1="8" y1="21" x2="16" y2="21"/>
						<line x1="12" y1="17" x2="12" y2="21"/>
						<path d="M6 7h.01M10 7h.01M14 7h.01M18 7h.01M6 11h.01M10 11h.01M14 11h.01M18 11h.01"/>
					</svg>
					<span class="button-label">키보드</span>
				{:else}
					<!-- 수식 아이콘 -->
					<svg class="math-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M9 7H6a2 2 0 00-2 2v6a2 2 0 002 2h3m6 0h3a2 2 0 002-2V9a2 2 0 00-2-2h-3m-6 0V4a2 2 0 012-2h2a2 2 0 012 2v3m-6 0h6"/>
						<text x="8" y="12" font-size="6" fill="currentColor" font-family="serif">∑</text>
					</svg>
					<span class="button-label">수식</span>
				{/if}
			</button>
			
			<!-- 이미지 업로드 버튼 -->
			<button 
				class="desktop-button image-upload-button" 
				onclick={handleImageUpload}
				disabled={disabled || isConvertingImage}
				title="이미지에서 수식 변환"
			>
				{#if isConvertingImage}
					<svg class="loading-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 12a9 9 0 11-6.219-8.56"/>
					</svg>
					<span class="button-label">변환중</span>
				{:else}
					<svg class="image-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
						<circle cx="8.5" cy="8.5" r="1.5"/>
						<polyline points="21,15 16,10 5,21"/>
					</svg>
					<span class="button-label">이미지</span>
				{/if}
			</button>
		</div>
		
		<!-- 전송 버튼 (오른쪽) -->
		<button 
			class="desktop-button send-button" 
			onclick={handleSend}
			disabled={disabled || isLoading || !value.trim() || isConvertingImage}
			title="메시지 전송"
		>
			{#if isLoading}
				<svg class="loading-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M21 12a9 9 0 11-6.219-8.56"/>
				</svg>
				<span class="button-label">전송중</span>
			{:else}
				<svg class="send-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
				</svg>
				<span class="button-label">전송</span>
			{/if}
		</button>
	</div>
	
	<!-- 이미지 선택 메뉴 -->
	{#if showImageMenu}
		<div class="image-menu">
			<button 
				class="image-menu-item"
				onclick={handleImageFromFile}
			>
				<svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
					<polyline points="13 2 13 9 20 9"/>
				</svg>
				파일에서 선택
			</button>
			<button 
				class="image-menu-item"
				onclick={handleImageFromCamera}
			>
				<svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
					<circle cx="12" cy="13" r="4"/>
				</svg>
				카메라로 촬영
			</button>
		</div>
	{/if}
	
	<!-- 숨겨진 파일 입력 (파일 선택용) -->
	<input
		bind:this={imageInputFile}
		type="file"
		accept="image/jpeg,image/png,image/webp"
		onchange={onImageSelected}
		style="display: none;"
	/>
	
</div>

<style>
	.inline-math-input-container {
		display: flex;
		align-items: flex-end;
		gap: 12px;
		width: 100%;
		position: relative;
	}

	/* 모바일에서 컨테이너 간격 비율 맞춤으로 조정 */
	@media (max-width: 768px) {
		.inline-math-input-container {
			gap: 8px;
		}
	}

	/* 도구 메뉴 스타일 (모바일에서만 표시) */
	.tool-menu {
		position: absolute;
		top: -80px;
		right: 0;
		display: flex;
		gap: 8px;
		opacity: 0;
		visibility: hidden;
		transform: translateY(10px);
		transition: all 0.2s ease;
		z-index: 100;
		background: var(--maice-bg-primary);
		border: 1px solid var(--maice-border-secondary);
		border-radius: 12px;
		padding: 8px;
		box-shadow: var(--maice-shadow-lg);
	}

	/* 데스크톱에서는 도구 메뉴 숨김 */
	@media (min-width: 769px) {
		.tool-menu {
			display: none !important;
		}
	}

	/* 모바일에서 도구 메뉴 위치 조정 */
	@media (max-width: 768px) {
		.tool-menu {
			top: -90px;
			right: -10px;
			padding: 10px;
			gap: 10px;
		}
	}

	.tool-menu.show {
		opacity: 1;
		visibility: visible;
		transform: translateY(0);
	}

	.tool-button {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		border: 1px solid var(--maice-border-secondary);
		border-radius: 8px;
		background: var(--maice-bg-secondary);
		color: var(--maice-text-secondary);
		cursor: pointer;
		transition: all 0.2s ease;
		font-size: 12px;
		gap: 2px;
	}

	/* 모바일에서 도구 버튼 크기 조정 */
	@media (max-width: 768px) {
		.tool-button {
			width: 48px;
			height: 48px;
			border-radius: 10px;
			gap: 3px;
		}
	}

	.tool-button:hover:not(:disabled) {
		background: var(--maice-primary);
		color: white;
		transform: translateY(-2px);
		box-shadow: var(--maice-shadow-md);
	}

	.tool-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* 이미지 메뉴 스타일 */
	.image-menu {
		position: absolute;
		bottom: 100%;
		right: 0;
		margin-bottom: 8px;
		display: flex;
		flex-direction: column;
		gap: 4px;
		background: var(--maice-bg-primary);
		border: 1px solid var(--maice-border-secondary);
		border-radius: 12px;
		padding: 8px;
		box-shadow: var(--maice-shadow-lg);
		z-index: 1000;
		min-width: 180px;
	}

	/* 모바일에서 이미지 메뉴 조정 */
	@media (max-width: 768px) {
		.image-menu {
			right: 50px;
			min-width: 160px;
		}
	}

	.image-menu-item {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 14px;
		border: none;
		border-radius: 8px;
		background: var(--maice-bg-secondary);
		color: var(--maice-text-primary);
		font-size: 14px;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s ease;
		white-space: nowrap;
	}

	.image-menu-item:hover {
		background: var(--maice-primary);
		color: white;
		transform: translateX(-2px);
	}

	.image-menu-item .menu-icon {
		width: 18px;
		height: 18px;
		flex-shrink: 0;
	}

	.tool-label {
		font-size: 10px;
		font-weight: 500;
		line-height: 1;
	}

	.tool-button .math-icon,
	.tool-button .image-icon,
	.tool-button .loading-icon,
	.tool-button .send-icon {
		width: 16px;
		height: 16px;
	}

	.input-area {
		flex: 1;
		position: relative;
		border: 1px solid var(--maice-border-secondary);
		border-radius: 12px;
		background: var(--maice-bg-primary);
		transition: all 0.2s ease;
		max-width: 100%; /* 최대 너비 제한 */
		overflow-x: auto; /* 가로 스크롤 허용 */
		overflow-y: hidden;
	}

	/* 데스크톱용 버튼 영역 스타일 */
	.desktop-button-area {
		display: flex;
		flex-direction: row;
		gap: 12px;
		align-items: flex-start;
		flex-shrink: 0;
	}

	/* 왼쪽 버튼 그룹 (수식, 이미지) */
	.left-button-group {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	/* 모바일에서는 데스크톱 버튼 영역 숨김 */
	@media (max-width: 768px) {
		.desktop-button-area {
			display: none !important;
		}
		
		.input-area {
			max-width: 100%; /* 모바일에서는 전체 너비 사용 */
		}
	}

	.editable-input {
		width: 100%;
		min-height: 80px;
		max-height: 300px;
		font-size: 16px;
		line-height: 1.6;
		padding: 16px 18px;
		border: none;
		border-radius: 12px;
		background: var(--maice-bg-primary);
		color: var(--maice-text-primary);
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		transition: all 0.2s ease;
		outline: none;
		overflow-y: auto;
		white-space: pre-wrap;
		word-wrap: break-word;
	}
	
	.editable-input.disabled {
		opacity: 0.6;
		cursor: not-allowed;
		pointer-events: none;
	}
	
	.converting-message {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		background: var(--maice-bg-secondary);
		color: var(--maice-text-secondary);
		padding: 12px 16px;
		border-radius: 8px;
		font-size: 14px;
		box-shadow: var(--maice-shadow-md);
		z-index: 10;
		pointer-events: none;
		animation: pulse 1.5s ease-in-out infinite;
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 0.8; }
		50% { opacity: 1; }
	}

	/* 모바일 화면에서 입력창 크기 세로로 더 늘림 */
	@media (max-width: 768px) {
		.editable-input {
			min-height: 108px;
			font-size: 16px;
			padding: 16px 14px;
		}
	}

	.input-area:focus-within {
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 2px rgba(75, 85, 99, 0.1);
	}

	.editable-input:focus {
		outline: none;
	}

	.editable-input:empty:before {
		content: attr(data-placeholder);
		color: var(--maice-text-muted);
		opacity: 0.7;
		font-style: italic;
		pointer-events: none;
	}

	.editable-input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
		background: var(--maice-bg-secondary);
	}

	/* 인라인 수식 컨테이너 스타일 */
	:global(.inline-math-container) {
		display: inline-block !important;
		margin: 0 2px !important;
		vertical-align: middle !important;
		background: var(--maice-bg-secondary) !important;
		border: 1px solid var(--maice-border-secondary) !important;
		border-radius: 6px !important;
		padding: 8px 12px !important; /* 입력창 패딩과 조화 */
		min-width: 30px !important;
		min-height: 28px !important;
		max-width: 100% !important; /* 입력창 너비의 80%로 제한 */
		overflow-x: auto !important; /* 가로 스크롤 허용 */
		overflow-y: hidden !important;
		word-wrap: break-word !important; /* 긴 수식 줄바꿈 */
		cursor: pointer !important;
		position: relative !important;
		transition: all 0.2s ease !important;
	}

	:global(.inline-math-container:hover) {
		background: var(--maice-bg-secondary-hover) !important;
		border-color: var(--maice-border-secondary-hover) !important;
		transform: translateY(-1px);
		box-shadow: var(--maice-shadow-sm);
	}

	:global(.inline-math-container math-field) {
		border: none !important;
		background: transparent !important;
		font-size: 14px !important;
		min-height: 20px !important;
		padding: 0 !important;
		margin: 0 !important;
		display: inline-block !important;
		width: auto !important;
		min-width: 30px !important;
		outline: none !important;
		
		/* 라이트 테마 수식 색상 */
		color: var(--maice-text-primary) !important;
		--primary-color: var(--maice-primary) !important;
		--caret-color: var(--maice-primary) !important;
		--text-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
	}

	/* 인라인 수식 필드의 가상 키보드 토글 버튼 완전 숨김 */
	:global(.inline-math-container math-field::part(virtual-keyboard-toggle)) {
		display: none !important;
	}

	/* 메뉴 토글 버튼도 숨김 */
	:global(.inline-math-container math-field::part(menu-toggle)) {
		display: none !important;
	}

	/* 데스크톱 버튼 스타일 */
	.desktop-button {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 56px;
		height: 56px;
		border: none;
		border-radius: 12px;
		cursor: pointer;
		transition: all 0.2s ease;
		gap: 4px;
		box-shadow: var(--maice-shadow-sm);
		flex-shrink: 0;
		font-size: 12px;
		font-weight: 500;
	}

	.desktop-button:hover:not(:disabled) {
		transform: translateY(-2px);
		box-shadow: var(--maice-shadow-md);
	}

	.desktop-button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
		transform: none !important;
		box-shadow: none !important;
	}

	.desktop-button .button-label {
		font-size: 10px;
		font-weight: 500;
		opacity: 0.9;
		line-height: 1;
	}

	.desktop-button .math-icon,
	.desktop-button .image-icon,
	.desktop-button .send-icon,
	.desktop-button .loading-icon {
		width: 16px;
		height: 16px;
		color: inherit;
	}

	/* 데스크톱 수식 버튼 스타일 */
	.desktop-button.math-button {
		background: #2D3748; /* 어두운 회색 */
		color: white;
		border: 1px solid #4A5568; /* 미묘한 테두리 */
	}

	.desktop-button.math-button:hover:not(:disabled) {
		background: var(--maice-primary);
		color: white;
	}

	.desktop-button.math-button.keyboard-mode {
		background: var(--maice-primary);
		color: white;
		box-shadow: var(--maice-shadow-md);
	}

	/* 데스크톱 이미지 버튼 스타일 */
	.desktop-button.image-upload-button {
		background: #2D3748; /* 어두운 회색 */
		color: white;
		border: 1px solid #4A5568; /* 미묘한 테두리 */
	}

	.desktop-button.image-upload-button:hover:not(:disabled) {
		background: var(--maice-primary);
		color: white;
	}

	/* 데스크톱 전송 버튼 스타일 */
	.desktop-button.send-button {
		background: #4A5568; /* 약간 푸른빛이 도는 회색 */
		color: white;
		height: 120px; /* 왼쪽 두 버튼 높이 합계 (56px + 8px + 56px) */
		border: 1px solid #718096; /* 미묘한 테두리 */
	}

	.desktop-button.send-button:hover:not(:disabled) {
		background: #5A6578; /* 호버 시 약간 더 밝게 */
	}

	.desktop-button.send-button:disabled {
		background: var(--maice-border-secondary) !important;
		color: var(--maice-text-muted) !important;
	}

	.loading-icon {
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		from { transform: rotate(0deg); }
		to { transform: rotate(360deg); }
	}

	/* 다크 테마 지원 */
	:global(.dark .inline-math-container) {
		background: var(--maice-bg-secondary) !important;
		border-color: var(--maice-border-secondary) !important;
	}

	:global(.dark .inline-math-container:hover) {
		background: var(--maice-bg-secondary-hover) !important;
		border-color: var(--maice-border-secondary-hover) !important;
	}

	/* 다크 테마 수식 텍스트 색상 */
	:global(.dark .inline-math-container math-field) {
		color: var(--maice-text-primary) !important;
		--primary-color: var(--maice-primary) !important;
		--caret-color: var(--maice-primary) !important;
		--text-color: var(--maice-text-primary) !important;
		--latex-color: var(--maice-text-primary) !important;
	}

	/* 다크 테마 수식 내부 요소들 */
	:global(.dark .inline-math-container math-field *) {
		color: var(--maice-text-primary) !important;
	}

	/* 라이트 테마 수식 내부 요소들 */
	:global(.inline-math-container math-field *) {
		color: var(--maice-text-primary) !important;
	}

	/* 다크 테마 input-area 스타일 */
	:global(.dark .input-area) {
		background: var(--maice-bg-primary);
		border-color: var(--maice-border-secondary);
	}

	:global(.dark .input-area:focus-within) {
		border-color: var(--maice-primary);
		box-shadow: 0 0 0 2px rgba(156, 163, 175, 0.2);
	}

	:global(.dark .editable-input) {
		background: transparent;
		color: var(--maice-text-primary);
	}
</style>
