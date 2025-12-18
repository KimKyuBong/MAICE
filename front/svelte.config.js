import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://svelte.dev/docs/kit/integrations
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// SPA 모드로 설정 - 정적 파일 생성
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html', // SPA 라우팅을 위한 fallback
			precompress: false,
			strict: true
		}),
		// SPA 모드 설정
		prerender: {
			handleHttpError: 'warn'
		}
	}
};

export default config;
