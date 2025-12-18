<script lang="ts">
	function handleClick() {
		alert('버튼이 클릭되었습니다! 🎉');
		console.log('버튼 클릭됨');
	}
</script>

<svelte:head>
	<title>간단한 테스트</title>
</svelte:head>

<div style="padding: 2rem; text-align: center;">
	<h1>🧪 간단한 테스트 페이지</h1>
	
	<button 
		on:click={handleClick}
		style="
			padding: 1rem 2rem;
			font-size: 1.2rem;
			background: #667eea;
			color: white;
			border: none;
			border-radius: 0.5rem;
			cursor: pointer;
			margin: 1rem;
		"
	>
		이 버튼을 클릭하세요!
	</button>
	
	<p>버튼을 클릭하면 알림이 나타납니다.</p>
	
	<div style="margin-top: 2rem; padding: 1rem; background: #f3f4f6; border-radius: 0.5rem;">
		<h3>테스트 결과:</h3>
		<p>버튼이 작동하면 성공입니다! 🎯</p>
	</div>
</div>





























































