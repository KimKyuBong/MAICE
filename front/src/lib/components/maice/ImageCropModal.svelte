<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	let {
		show = $bindable(false),
		imageUrl = ''
	}: {
		show?: boolean;
		imageUrl?: string;
	} = $props();

	const dispatch = createEventDispatcher<{
		confirm: { blob: Blob };
		cancel: void;
	}>();

	let cropCanvas: HTMLCanvasElement;
	let previewImageElement: HTMLImageElement;
	let imageWrapperElement: HTMLDivElement;
	let previewContainerElement: HTMLDivElement;
	
	// 크롭 관련 상태
	let isDragging = $state(false);
	let cropArea = $state<{ x: number; y: number; width: number; height: number } | null>(null);
	let startPoint = $state<{ x: number; y: number } | null>(null);
	
	// 줌 관련 상태
	let scale = $state(1);
	let translateX = $state(0);
	let translateY = $state(0);
	let lastDistance = $state(0);
	let isPinching = $state(false);

	// 줌 리셋
	function resetZoom() {
		scale = 1;
		translateX = 0;
		translateY = 0;
		lastDistance = 0;
		isPinching = false;
	}

	// 취소
	function handleCancel() {
		cropArea = null;
		startPoint = null;
		isDragging = false;
		resetZoom();
		dispatch('cancel');
		show = false;
	}

	// 전송
	async function handleConfirm() {
		let blobToSend: Blob | null = null;

		// 크롭 영역이 선택되어 있으면 해당 영역만 잘라내기
		if (cropArea && previewImageElement && cropCanvas) {
			blobToSend = await cropImage();
		} else {
			// 크롭 영역이 없으면 원본 이미지 사용
			blobToSend = await convertImageUrlToBlob(imageUrl);
		}

		if (blobToSend) {
			dispatch('confirm', { blob: blobToSend });
			cropArea = null;
			startPoint = null;
			isDragging = false;
			resetZoom();
			show = false;
		}
	}

	// 이미지 URL을 Blob으로 변환
	async function convertImageUrlToBlob(url: string): Promise<Blob | null> {
		try {
			const response = await fetch(url);
			return await response.blob();
		} catch (err) {
			console.error('이미지 변환 오류:', err);
			return null;
		}
	}

	// 이미지 크롭
	async function cropImage(): Promise<Blob | null> {
		if (!cropArea || !previewImageElement || !cropCanvas || !imageWrapperElement || !previewContainerElement) return null;

		const img = previewImageElement;
		const containerRect = previewContainerElement.getBoundingClientRect();
		const wrapperRect = imageWrapperElement.getBoundingClientRect();
		
		// 컨테이너 기준 크롭 영역을 이미지 기준으로 변환
		const imageOffsetX = wrapperRect.left - containerRect.left;
		const imageOffsetY = wrapperRect.top - containerRect.top;
		
		// 이미지 내부 좌표로 변환
		const relX = cropArea.x - imageOffsetX;
		const relY = cropArea.y - imageOffsetY;
		
		// 스케일 적용된 이미지 크기
		const displayedWidth = wrapperRect.width;
		const displayedHeight = wrapperRect.height;
		
		// 실제 이미지와의 비율 계산
		const scaleX = img.naturalWidth / displayedWidth;
		const scaleY = img.naturalHeight / displayedHeight;

		// 실제 이미지 좌표로 변환
		const sx = Math.max(0, relX * scaleX);
		const sy = Math.max(0, relY * scaleY);
		const sWidth = Math.min(cropArea.width * scaleX, img.naturalWidth - sx);
		const sHeight = Math.min(cropArea.height * scaleY, img.naturalHeight - sy);

		// 크롭 캔버스 설정
		cropCanvas.width = sWidth;
		cropCanvas.height = sHeight;

		const ctx = cropCanvas.getContext('2d');
		if (!ctx) return null;

		// 선택 영역만 그리기
		ctx.drawImage(img, sx, sy, sWidth, sHeight, 0, 0, sWidth, sHeight);

		// Blob으로 변환
		return new Promise((resolve) => {
			cropCanvas.toBlob((blob) => {
				resolve(blob);
			}, 'image/jpeg', 0.95);
		});
	}

	// 두 터치 포인트 간 거리 계산
	function getDistance(touch1: Touch, touch2: Touch): number {
		const dx = touch1.clientX - touch2.clientX;
		const dy = touch1.clientY - touch2.clientY;
		return Math.sqrt(dx * dx + dy * dy);
	}

	// 드래그 시작
	function handleMouseDown(event: MouseEvent | TouchEvent) {
		if (!previewContainerElement || !imageWrapperElement) return;

		// 터치 이벤트인 경우 핀치 줌 처리
		if ('touches' in event && event.touches.length === 2) {
			isPinching = true;
			lastDistance = getDistance(event.touches[0], event.touches[1]);
			event.preventDefault();
			return;
		}

		// 단일 터치 또는 마우스인 경우 크롭 드래그
		const containerRect = previewContainerElement.getBoundingClientRect();
		const clientX = 'touches' in event ? event.touches[0].clientX : event.clientX;
		const clientY = 'touches' in event ? event.touches[0].clientY : event.clientY;

		// 컨테이너 기준 좌표
		startPoint = {
			x: clientX - containerRect.left,
			y: clientY - containerRect.top
		};
		isDragging = true;
		cropArea = null;
	}

	// 드래그 중
	function handleMouseMove(event: MouseEvent | TouchEvent) {
		if (!previewContainerElement || !imageWrapperElement) return;

		// 핀치 줌 처리
		if ('touches' in event && event.touches.length === 2 && isPinching) {
			const currentDistance = getDistance(event.touches[0], event.touches[1]);
			const delta = currentDistance - lastDistance;
			
			// 줌 스케일 조정 (0.5배 ~ 3배)
			const newScale = Math.max(0.5, Math.min(3, scale + delta * 0.01));
			scale = newScale;
			
			lastDistance = currentDistance;
			event.preventDefault();
			return;
		}

		// 크롭 드래그 처리
		if (!isDragging || !startPoint) return;

		const containerRect = previewContainerElement.getBoundingClientRect();
		const clientX = 'touches' in event ? event.touches[0].clientX : event.clientX;
		const clientY = 'touches' in event ? event.touches[0].clientY : event.clientY;

		// 현재 마우스 위치 (컨테이너 기준)
		const currentX = clientX - containerRect.left;
		const currentY = clientY - containerRect.top;

		// 드래그 영역 계산
		const x = Math.min(startPoint.x, currentX);
		const y = Math.min(startPoint.y, currentY);
		const width = Math.abs(currentX - startPoint.x);
		const height = Math.abs(currentY - startPoint.y);

		// 컨테이너 범위 내로 제한
		cropArea = {
			x: Math.max(0, Math.min(x, containerRect.width)),
			y: Math.max(0, Math.min(y, containerRect.height)),
			width: Math.min(width, containerRect.width - x),
			height: Math.min(height, containerRect.height - y)
		};
	}

	// 드래그 종료
	function handleMouseUp() {
		isDragging = false;
		isPinching = false;
		startPoint = null;
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleCancel();
		}
	}
</script>

{#if show}
	<div class="crop-modal-backdrop" onclick={handleBackdropClick}>
		<div class="crop-modal-content">
			<div class="crop-header">
				<h3 class="crop-title">이미지 편집</h3>
				<div class="header-actions">
					<button class="header-button cancel-button" onclick={handleCancel}>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="18" y1="6" x2="6" y2="18" />
							<line x1="6" y1="6" x2="18" y2="18" />
						</svg>
						<span>취소</span>
					</button>
					<button class="header-button confirm-button" onclick={handleConfirm}>
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
							<polyline points="22 4 12 14.01 9 11.01"/>
						</svg>
						<span>{cropArea ? '선택 영역 전송' : '전송'}</span>
					</button>
				</div>
			</div>

			<div class="crop-container">
				<div 
					bind:this={previewContainerElement}
					class="preview-container"
					onmousedown={handleMouseDown}
					onmousemove={handleMouseMove}
					onmouseup={handleMouseUp}
					onmouseleave={handleMouseUp}
					ontouchstart={handleMouseDown}
					ontouchmove={handleMouseMove}
					ontouchend={handleMouseUp}
				>
					<div 
						bind:this={imageWrapperElement}
						class="image-wrapper"
						style="
							transform: scale({scale}) translate({translateX}px, {translateY}px);
							transform-origin: center;
						"
					>
						<img 
							bind:this={previewImageElement}
							src={imageUrl} 
							alt="업로드된 이미지" 
							class="preview-image"
							draggable="false"
						/>
					</div>
					
					<!-- 크롭 영역 표시 -->
					{#if cropArea}
						<div 
							class="crop-overlay"
							style="
								left: {cropArea.x}px;
								top: {cropArea.y}px;
								width: {cropArea.width}px;
								height: {cropArea.height}px;
							"
						></div>
					{/if}
					
					<!-- 줌 컨트롤 -->
					<div class="zoom-controls">
						<button 
							class="zoom-button"
							onclick={() => scale = Math.max(0.5, scale - 0.2)}
							disabled={scale <= 0.5}
							aria-label="축소"
						>
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="11" cy="11" r="8"/>
								<line x1="8" y1="11" x2="14" y2="11"/>
								<line x1="21" y1="21" x2="16.65" y2="16.65"/>
							</svg>
						</button>
						<span class="zoom-level">{Math.round(scale * 100)}%</span>
						<button 
							class="zoom-button"
							onclick={() => scale = Math.min(3, scale + 0.2)}
							disabled={scale >= 3}
							aria-label="확대"
						>
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="11" cy="11" r="8"/>
								<line x1="11" y1="8" x2="11" y2="14"/>
								<line x1="8" y1="11" x2="14" y2="11"/>
								<line x1="21" y1="21" x2="16.65" y2="16.65"/>
							</svg>
						</button>
					{#if scale !== 1}
						<button 
							class="zoom-reset-button"
							onclick={resetZoom}
							aria-label="원래 크기"
						>
							리셋
						</button>
					{/if}
				</div>
				</div>

				<!-- 숨겨진 캔버스 (크롭용) -->
				<canvas bind:this={cropCanvas} style="display: none;"></canvas>
			</div>

			<div class="crop-footer">
				<p class="crop-hint">
					{cropArea ? '선택한 영역이 전송됩니다' : '드래그해서 문제 영역을 선택하거나 전체 전송하세요'}
				</p>
			</div>
		</div>
	</div>
{/if}

<style>
	.crop-modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.9);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: 20px;
	}

	.crop-modal-content {
		background: var(--maice-bg-primary);
		border-radius: 16px;
		max-width: 600px;
		width: 100%;
		max-height: 90vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	.crop-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--maice-border-secondary);
		background: var(--maice-bg-primary);
		flex-shrink: 0;
		z-index: 20;
		position: relative;
	}

	.crop-title {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
		color: var(--maice-text-primary);
	}

	.header-actions {
		display: flex;
		gap: 10px;
	}

	.header-button {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 16px;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		font-size: 14px;
		font-weight: 600;
		transition: all 0.2s ease;
	}

	.header-button svg {
		width: 18px;
		height: 18px;
	}

	.header-button.cancel-button {
		background: var(--maice-bg-secondary);
		color: var(--maice-text-secondary);
	}

	.header-button.cancel-button:hover {
		background: #6b7280;
		color: white;
	}

	.header-button.confirm-button {
		background: #3b82f6;
		color: white;
	}

	.header-button.confirm-button:hover {
		background: #2563eb;
		transform: translateY(-1px);
		box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
	}

	.crop-container {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #000;
		min-height: 450px;
		position: relative;
		overflow: hidden;
	}

	.preview-container {
		width: 100%;
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		position: relative;
		cursor: crosshair;
		user-select: none;
		-webkit-user-select: none;
		touch-action: none;
		overflow: hidden;
	}

	.image-wrapper {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: transform 0.1s ease-out;
		will-change: transform;
	}

	.preview-image {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
		pointer-events: none;
		display: block;
	}

	.crop-overlay {
		position: absolute;
		border: 2px solid #3b82f6;
		background: rgba(59, 130, 246, 0.15);
		pointer-events: none;
		z-index: 5;
		box-shadow: 
			0 0 0 9999px rgba(0, 0, 0, 0.5),
			inset 0 0 0 1px rgba(255, 255, 255, 0.5);
	}

	.crop-overlay::before {
		content: '';
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		width: 20px;
		height: 20px;
		border: 2px solid white;
		border-radius: 50%;
		background: rgba(59, 130, 246, 0.8);
		pointer-events: none;
	}

	.zoom-controls {
		position: absolute;
		top: 20px;
		right: 20px;
		display: flex;
		align-items: center;
		gap: 8px;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(8px);
		border-radius: 12px;
		padding: 8px 12px;
		z-index: 10;
	}

	.zoom-button {
		width: 32px;
		height: 32px;
		border: none;
		background: transparent;
		color: white;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 6px;
		transition: all 0.2s ease;
	}

	.zoom-button:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.1);
	}

	.zoom-button:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.zoom-button svg {
		width: 20px;
		height: 20px;
	}

	.zoom-level {
		color: white;
		font-size: 13px;
		font-weight: 600;
		min-width: 45px;
		text-align: center;
	}

	.zoom-reset-button {
		padding: 4px 10px;
		border: none;
		background: rgba(59, 130, 246, 0.8);
		color: white;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.zoom-reset-button:hover {
		background: rgba(37, 99, 235, 0.9);
	}

	.crop-footer {
		padding: 16px 20px;
		border-top: 1px solid var(--maice-border-secondary);
		background: var(--maice-bg-secondary);
		flex-shrink: 0;
		z-index: 20;
		position: relative;
	}

	.crop-hint {
		margin: 0;
		font-size: 14px;
		color: var(--maice-text-secondary);
		text-align: center;
	}

	/* 모바일 최적화 */
	@media (max-width: 768px) {
		.crop-modal-backdrop {
			padding: 0;
		}

		.crop-modal-content {
			max-width: 100%;
			max-height: 100vh;
			height: 100vh;
			border-radius: 0;
		}

		.crop-container {
			min-height: 60vh;
		}

		.zoom-controls {
			top: 10px;
			right: 10px;
			padding: 6px 10px;
		}

		.zoom-button {
			width: 28px;
			height: 28px;
		}

		.zoom-button svg {
			width: 18px;
			height: 18px;
		}

		.zoom-level {
			font-size: 12px;
			min-width: 40px;
		}

		.header-button {
			padding: 6px 12px;
			font-size: 13px;
		}

		.header-button svg {
			width: 16px;
			height: 16px;
		}
	}
</style>

