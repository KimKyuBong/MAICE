<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';

	let {
		show = $bindable(false)
	}: {
		show?: boolean;
	} = $props();

	const dispatch = createEventDispatcher<{
		capture: { imageUrl: string };
		close: void;
	}>();

	let videoElement: HTMLVideoElement;
	let canvasElement: HTMLCanvasElement;
	let stream: MediaStream | null = null;
	let isCapturing = $state(false);
	let error = $state<string | null>(null);

	// 카메라 시작
	async function startCamera() {
		try {
			error = null;
			// 후면 카메라 우선 사용
			stream = await navigator.mediaDevices.getUserMedia({
				video: {
					facingMode: { ideal: 'environment' }, // 후면 카메라 선호
					width: { ideal: 1920 },
					height: { ideal: 1080 }
				}
			});

			if (videoElement) {
				videoElement.srcObject = stream;
				await videoElement.play();
			}
		} catch (err) {
			console.error('카메라 접근 오류:', err);
			error = '카메라 접근 권한이 필요합니다.';
		}
	}

	// 카메라 정지
	function stopCamera() {
		if (stream) {
			stream.getTracks().forEach(track => track.stop());
			stream = null;
		}
		if (videoElement) {
			videoElement.srcObject = null;
		}
	}

	// 사진 촬영
	async function capturePhoto() {
		if (!videoElement || !canvasElement || isCapturing) return;

		isCapturing = true;

		try {
			// 비디오의 실제 크기로 캔버스 설정
			canvasElement.width = videoElement.videoWidth;
			canvasElement.height = videoElement.videoHeight;

			// 캔버스에 현재 비디오 프레임 그리기
			const ctx = canvasElement.getContext('2d');
			if (ctx) {
				ctx.drawImage(videoElement, 0, 0);

				// 캔버스를 Data URL로 변환하여 크롭 모달로 전달
				const imageUrl = canvasElement.toDataURL('image/jpeg', 0.95);
				
				stopCamera();
				dispatch('capture', { imageUrl });
				show = false;
			}
		} catch (err) {
			console.error('촬영 오류:', err);
			error = '사진 촬영 중 오류가 발생했습니다.';
		} finally {
			isCapturing = false;
		}
	}

	function handleClose() {
		stopCamera();
		dispatch('close');
		show = false;
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	// show가 true로 변경되면 카메라 시작
	$effect(() => {
		if (show) {
			startCamera();
		} else {
			stopCamera();
		}
	});

	onDestroy(() => {
		stopCamera();
	});
</script>

{#if show}
	<div class="camera-modal-backdrop" onclick={handleBackdropClick}>
		<div class="camera-modal-content">
			<div class="camera-header">
				<h3 class="camera-title">수학 문제 촬영</h3>
				<button class="close-button" onclick={handleClose} aria-label="닫기">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="18" y1="6" x2="6" y2="18" />
						<line x1="6" y1="6" x2="18" y2="18" />
					</svg>
				</button>
			</div>

			<div class="camera-container">
				{#if error}
					<!-- 에러 메시지 -->
					<div class="error-message">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="10" />
							<line x1="12" y1="8" x2="12" y2="12" />
							<line x1="12" y1="16" x2="12.01" y2="16" />
						</svg>
						<p>{error}</p>
					</div>
				{:else}
					<!-- 비디오 스트림 -->
					<video
						bind:this={videoElement}
						autoplay
						playsinline
						muted
					></video>

					<!-- 촬영 버튼 -->
					<button
						class="capture-button"
						onclick={capturePhoto}
						disabled={isCapturing}
						aria-label="촬영"
					>
						<div class="capture-ring">
							<div class="capture-inner"></div>
						</div>
					</button>
				{/if}

				<!-- 숨겨진 캔버스 (이미지 캡처용) -->
				<canvas bind:this={canvasElement} style="display: none;"></canvas>
			</div>

			<div class="camera-footer">
				<p class="camera-hint">
					{#if error}
						브라우저 설정에서 카메라 권한을 허용해주세요
					{:else}
						수학 문제가 화면에 잘 보이도록 촬영하세요
					{/if}
				</p>
			</div>
		</div>
	</div>
{/if}

<style>
	.camera-modal-backdrop {
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

	.camera-modal-content {
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

	.camera-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 20px;
		border-bottom: 1px solid var(--maice-border-secondary);
	}

	.camera-title {
		margin: 0;
		font-size: 18px;
		font-weight: 600;
		color: var(--maice-text-primary);
	}

	.close-button {
		width: 36px;
		height: 36px;
		border: none;
		background: var(--maice-bg-secondary);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.2s ease;
		color: var(--maice-text-secondary);
	}

	.close-button:hover {
		background: var(--maice-primary);
		color: white;
		transform: scale(1.05);
	}

	.close-button svg {
		width: 20px;
		height: 20px;
	}

	.camera-container {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #000;
		min-height: 450px;
		position: relative;
		overflow: hidden;
	}

	.camera-container :global(video) {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.camera-footer {
		padding: 16px 20px;
		border-top: 1px solid var(--maice-border-secondary);
		background: var(--maice-bg-secondary);
	}

	.camera-hint {
		margin: 0;
		font-size: 14px;
		color: var(--maice-text-secondary);
		text-align: center;
	}

	/* 촬영 버튼 */
	.capture-button {
		position: absolute;
		bottom: 30px;
		left: 50%;
		transform: translateX(-50%);
		background: transparent;
		border: none;
		cursor: pointer;
		padding: 0;
		z-index: 10;
	}

	.capture-ring {
		width: 70px;
		height: 70px;
		border: 4px solid white;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
	}

	.capture-button:hover .capture-ring {
		transform: scale(1.1);
		box-shadow: 0 0 20px rgba(255, 255, 255, 0.5);
	}

	.capture-button:disabled .capture-ring {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.capture-inner {
		width: 56px;
		height: 56px;
		background: white;
		border-radius: 50%;
	}

	/* 에러 메시지 */
	.error-message {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 16px;
		padding: 40px;
		color: var(--maice-text-secondary);
	}

	.error-message svg {
		width: 60px;
		height: 60px;
		color: #ef4444;
	}

	.error-message p {
		margin: 0;
		font-size: 16px;
		text-align: center;
	}

	/* 모바일 최적화 */
	@media (max-width: 768px) {
		.camera-modal-backdrop {
			padding: 0;
		}

		.camera-modal-content {
			max-width: 100%;
			max-height: 100vh;
			height: 100vh;
			border-radius: 0;
		}

		.camera-container {
			min-height: 60vh;
		}

		.capture-button {
			bottom: 20px;
		}
	}
</style>

