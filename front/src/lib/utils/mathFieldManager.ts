import type { MathfieldElement } from "mathlive";

// MathField 상태 관리 인터페이스
export interface MathFieldState {
	readonly isMathFieldFocused: boolean;
	readonly currentMathField: MathfieldElement | null;
	readonly isTransitioning: boolean;
	focusDebounceTimer: any;
	lastFocusTime: number;
	lastBlurTime: number;
	isForceClearingFocus: boolean;
}

// MathField 콜백 인터페이스
export interface MathFieldCallbacks {
	onFocusChange?: (isFocused: boolean, mathField: MathfieldElement | null) => void;
	onVirtualKeyboardShow?: (mathField: MathfieldElement) => void;
	onVirtualKeyboardHide?: (mathField: MathfieldElement) => void;
	onMathFieldRemove?: (mathField: MathfieldElement) => void;
	onStateUpdate?: (updates: Partial<MathFieldState>) => void;
	isTransitioning?: () => boolean;
	isForceClearingFocus?: () => boolean;
	getLastBlurTime?: () => number;
	handleDebouncedFocus?: (mathField: MathfieldElement) => boolean;
}

// 커스텀 가상 키보드 레이아웃 설정
export function setupCustomVirtualKeyboard() {
	if (typeof window === 'undefined') return;
	
	try {
		// MathLive 가상 키보드 레이아웃 설정
		const mathLive = (window as any).MathLive;
		if (mathLive && mathLive.configure) {
			mathLive.configure({
				virtualKeyboardMode: 'manual',
				virtualKeyboards: 'all',
				virtualKeyboardTheme: 'material',
				virtualKeyboardLayout: 'auto'
			});
		}
	} catch (error) {
		console.log('가상 키보드 설정 실패:', error);
	}
}

// MathLive API 안전 호출
export function safeMathLiveCall(mathField: MathfieldElement, command: string): boolean {
	try {
		if (!mathField || typeof (mathField as any).executeCommand !== 'function') {
			console.log('MathField가 준비되지 않음:', command);
			return false;
		}
	
		(mathField as any).executeCommand(command);
		return true;
	} catch (error) {
		console.log(`MathLive ${command} 실패:`, error);
		return false;
	}
}

// 수식 컨테이너 생성 (삽입용)
export async function createMathContainerForInsertion(latex: string = ''): Promise<HTMLElement> {
	const mathContainer = document.createElement('div');
	mathContainer.className = 'inline-math-container';
	mathContainer.style.display = 'inline-block';
	mathContainer.style.margin = '0 2px';
	mathContainer.style.verticalAlign = 'middle';
	mathContainer.style.background = 'var(--maice-bg-secondary)';
	mathContainer.style.border = '1px solid var(--maice-border-secondary)';
	mathContainer.style.borderRadius = '6px';
	mathContainer.style.padding = '4px 8px';
	mathContainer.style.minWidth = '50px';
	mathContainer.style.minHeight = '28px';
	mathContainer.style.cursor = 'pointer';
	mathContainer.style.position = 'relative';
	mathContainer.style.transition = 'all 0.2s ease';
	
	// MathField 생성
	const mathField = await createInlineMathField(latex, mathContainer);
	
	return mathContainer;
}

// 인라인 수식 필드 생성
export async function createInlineMathField(
	latex: string = '', 
	container?: HTMLElement,
	mathCounter?: { value: number },
	editableElement?: HTMLElement,
	mathFieldState?: MathFieldState,
	mathFieldCallbacks?: MathFieldCallbacks
): Promise<MathfieldElement> {
	return new Promise((resolve) => {
		const mathField = document.createElement('math-field') as MathfieldElement;
		
		// 고유 ID 설정
		const id = `math-${mathCounter?.value || Date.now()}`;
		mathField.id = id;
		mathField.setAttribute('data-math-field-id', id);
		
		// 기본 설정
		mathField.setAttribute('contenteditable', 'true');
		mathField.style.border = 'none';
		mathField.style.background = 'transparent';
		mathField.style.fontSize = '14px';
		mathField.style.minHeight = '20px';
		mathField.style.padding = '0';
		mathField.style.margin = '0';
		mathField.style.display = 'inline-block';
		mathField.style.width = 'auto';
		mathField.style.minWidth = '30px';
		mathField.style.outline = 'none';
		mathField.style.color = 'var(--maice-text-primary)';
		
		// LaTeX 설정
		if (latex) {
			mathField.value = latex;
		}
		
		// 컨테이너에 추가
		if (container) {
			container.appendChild(mathField);
		}
		
		// 이벤트 리스너 설정
		setupMathFieldEventListeners(mathField, mathFieldState, mathFieldCallbacks);
		
		// MathLive 초기화 대기
		setTimeout(() => {
			resolve(mathField);
		}, 50);
	});
}

// MathField 이벤트 리스너 설정
function setupMathFieldEventListeners(
	mathField: MathfieldElement,
	mathFieldState?: MathFieldState,
	mathFieldCallbacks?: MathFieldCallbacks
) {
	let focusTimeout: any = null;
	let blurTimeout: any = null;
	let lastFocusAttempt = 0;
	
	// 포커스 이벤트
	mathField.addEventListener('focus', () => {
		const now = Date.now();
		
		// 포커스 차단 확인
		if (mathFieldState?.isForceClearingFocus || (mathField as any).__isFocusBlocked) {
			console.log('포커스 차단됨:', mathField.id);
			mathField.blur();
			return;
		}
		
		// 연속 포커스 시도 방지
		if (now - lastFocusAttempt < 500) {
			console.log('연속 포커스 시도 방지:', mathField.id, now - lastFocusAttempt, 'ms');
			mathField.blur();
			return;
		}
		lastFocusAttempt = now;
		
		// 디바운스된 포커스 처리
		if (!mathFieldCallbacks?.handleDebouncedFocus?.(mathField)) {
			return;
		}
		
		console.log('MathField 포커스됨:', mathField.id);
		
		// 포커스 상태 업데이트
		mathFieldCallbacks?.onFocusChange?.(true, mathField);
		
		// 가상 키보드 표시를 즉시 처리 (지연 제거)
		// 재검증: 여전히 포커스가 유효한지 확인
		if (!mathFieldCallbacks?.isForceClearingFocus?.() && !mathFieldCallbacks?.isTransitioning?.() && document.activeElement === mathField) {
			// 가상키보드가 이미 표시되어 있는지 확인
			const virtualKeyboard = document.querySelector('.ML__virtual-keyboard') as HTMLElement;
			if (virtualKeyboard && virtualKeyboard.style.display !== 'none') {
				console.log('가상키보드가 이미 표시됨, 중복 표시 방지:', mathField.id);
				return;
			}
			
			try {
				// 커스텀 가상 키보드 레이아웃 설정
				setupCustomVirtualKeyboard();
				
				if (mathField.executeCommand) {
					mathField.executeCommand('showVirtualKeyboard');
					console.log('가상키보드 표시됨:', mathField.id);
					
					// 가상키보드 표시 콜백 호출
					mathFieldCallbacks?.onVirtualKeyboardShow?.(mathField);
				}
			} catch (error) {
				console.log('가상키보드 표시 실패:', error);
			}
		} else {
			console.log('포커스 상태 변경으로 가상키보드 표시 취소:', mathField.id);
		}
		
		focusTimeout = null;
	});
	
	// 블러 이벤트
	mathField.addEventListener('blur', () => {
		// 가짜 블러 이벤트 필터링
		if (document.activeElement === mathField) {
			console.log('가짜 블러 이벤트 무시 (가상키보드 표시로 인한 DOM 변경):', mathField.id);
			return;
		}
		
		blurTimeout = setTimeout(() => {
			console.log('MathField 블러됨:', mathField.id);
			
			// 포커스 해제 시간 기록 (재포커스 방지용)
			mathFieldCallbacks?.onStateUpdate?.({ lastBlurTime: Date.now() });
			
			// 포커스 상태만 업데이트 (가상키보드는 전역 클릭에서 처리)
			mathFieldCallbacks?.onFocusChange?.(false, mathField);
			
			// 가상키보드 숨김은 제거 (무한 루프 방지)
			// 가상키보드는 전역 클릭 이벤트에서만 숨김
		}, 100);
	});
	
	// 컨테이너 클릭 이벤트 - 단일 클릭으로 수식 편집 모드 진입
	const mathContainer = mathField.closest('.inline-math-container');
	if (mathContainer) {
		mathContainer.addEventListener('click', (e) => {
			e.preventDefault();
			e.stopPropagation();
			
			const now = Date.now();
			
			// 최근 블러 후 500ms 이내면 재포커스 방지
			if (mathFieldCallbacks?.getLastBlurTime?.() && now - mathFieldCallbacks.getLastBlurTime() < 500) {
				console.log('최근 블러 후 재포커스 방지:', mathField.id);
				return;
			}
			
			// 강제 포커스 해제 중이면 무시
			if (mathFieldState?.isForceClearingFocus) {
				console.log('강제 포커스 해제 중, 클릭 무시:', mathField.id);
				return;
			}
			
			console.log('수식 컨테이너 클릭, 포커스 설정:', mathField.id);
			mathField.focus();
		});
	}
	
	// 키보드 이벤트
	mathField.addEventListener('keydown', (e) => {
		// Escape 키로 포커스 해제
		if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			mathField.blur();
			// 포커스 해제 후 editableElement로 포커스 이동
			const editableElement = mathField.closest('.editable-input') as HTMLElement;
			if (editableElement) {
				editableElement.focus();
			}
		}
	});
}

// 포커스 강제 해제
export function forceClearMathFocus(
	editableElement: HTMLElement,
	mathFieldState: MathFieldState,
	mathFieldCallbacks: MathFieldCallbacks
) {
	console.log('강제 포커스 해제 실행 - 현재 상태:', {
		isMathFieldFocused: mathFieldState.isMathFieldFocused,
		currentMathField: mathFieldState.currentMathField?.id || null,
		activeElement: document.activeElement?.tagName || null
	});
	
	// 강제 포커스 해제 플래그 설정
	mathFieldState.isForceClearingFocus = true;
	
	// 모든 수식 필드에 포커스 차단 플래그 설정
	const allMathFieldsForBlocking = editableElement?.querySelectorAll('math-field');
	allMathFieldsForBlocking?.forEach(field => {
		try {
			const mathField = field as any;
			mathField.__isFocusBlocked = true;
		} catch (e) {
			// 무시
		}
	});
	
	// 현재 포커스된 수식 필드가 있으면 포커스 해제
	if (mathFieldState.currentMathField) {
		console.log('현재 활성 수식 필드 포커스 해제');
		
		// 지연 처리로 DOM 변경 최소화
		setTimeout(() => {
			try {
				mathFieldState.currentMathField?.blur();
				console.log('수식 필드 포커스 해제:', mathFieldState.currentMathField?.id);
			} catch (e) {
				console.log('포커스 해제 실패:', e);
			}
		}, 50);
		
		// 가상 키보드 숨기기 (DOM 변경으로 인한 포커스 이벤트 방지를 위해 더 지연)
		setTimeout(() => {
			try {
				mathFieldState.currentMathField?.executeCommand('hideVirtualKeyboard');
				console.log('가상 키보드 숨기기:', mathFieldState.currentMathField?.id);
			} catch (e) {
				console.log('가상 키보드 숨기기 실패:', e);
			}
		}, 100);
	}
	
	// 상태 초기화
	mathFieldCallbacks?.onStateUpdate?.({ 
		isMathFieldFocused: false, 
		currentMathField: null 
	});
	
	// 가상 키보드 숨기기 (지연 처리)
	setTimeout(() => {
		try {
			mathFieldState.currentMathField?.executeCommand('hideVirtualKeyboard');
		} catch (e) {
			// 무시
		}
	}, 200);
	
	// 포커스 차단 해제 (더 긴 시간으로 재포커스 방지)
	setTimeout(() => {
		mathFieldState.isForceClearingFocus = false;
		
		// 모든 수식 필드의 포커스 차단 플래그 해제
		const allMathFieldsForUnblocking = editableElement?.querySelectorAll('math-field');
		allMathFieldsForUnblocking?.forEach(field => {
			try {
				const mathField = field as any;
				mathField.__isFocusBlocked = false;
			} catch (e) {
				// 무시
			}
		});
		
		console.log('강제 포커스 해제 완료');
	}, 1000);
}

// 수식 삽입 처리
export async function insertMathAtCursor(
	editableElement: HTMLElement,
	mathCounter: { value: number },
	mathFieldState: MathFieldState,
	virtualKeyboardState: any,
	virtualKeyboardCallbacks: any,
	callbacks: {
		setupVirtualKeyboardLayout: () => void;
		updateTextValue: (element: HTMLElement) => string;
		handleDebouncedFocus: (mathField: MathfieldElement) => boolean;
		safeMathLiveCall: (mathField: MathfieldElement, command: string) => boolean;
		onStateUpdate?: (updates: Partial<MathFieldState>) => void;
	}
) {
	if (!editableElement) return;
	
	try {
		// 수식 컨테이너 생성
		const mathContainer = await createMathContainerForInsertion();
		
		// 현재 커서 위치에 삽입
		const selection = window.getSelection();
		if (selection && selection.rangeCount > 0) {
			const range = selection.getRangeAt(0);
			range.insertNode(mathContainer);
			range.collapse(false);
			selection.removeAllRanges();
			selection.addRange(range);
		} else {
			editableElement.appendChild(mathContainer);
		}
		
		// MathField 생성 및 설정
		const mathField = await createInlineMathField('', mathContainer, mathCounter, editableElement, mathFieldState, {
			onFocusChange: (isFocused, field) => {
				callbacks.onStateUpdate?.({ 
					isMathFieldFocused: isFocused, 
					currentMathField: field 
				});
			},
			onVirtualKeyboardShow: (field) => {
				virtualKeyboardState.isVisible = true;
				virtualKeyboardState.currentMathField = field;
				virtualKeyboardCallbacks?.onShow?.(field);
			},
			onVirtualKeyboardHide: (field) => {
				virtualKeyboardState.isVisible = false;
				virtualKeyboardState.currentMathField = null;
				virtualKeyboardCallbacks?.onHide?.(field);
			},
			onMathFieldRemove: (field) => {
				if (mathFieldState.currentMathField === field) {
					callbacks.onStateUpdate?.({ 
						isMathFieldFocused: false, 
						currentMathField: null 
					});
				}
			},
			onStateUpdate: callbacks.onStateUpdate,
			isTransitioning: () => mathFieldState.isTransitioning,
			isForceClearingFocus: () => mathFieldState.isForceClearingFocus,
			getLastBlurTime: () => mathFieldState.lastBlurTime,
			handleDebouncedFocus: callbacks.handleDebouncedFocus
		});
		
		// 가상 키보드 레이아웃 설정
		callbacks.setupVirtualKeyboardLayout();
		
		// 약간의 지연 후 포커스 설정
		setTimeout(() => {
			mathField.focus();
		}, 50);
		
		// 텍스트 값 업데이트
		callbacks.updateTextValue(editableElement);
		
	} catch (error) {
		console.log('수식 삽입 실패:', error);
	}
}