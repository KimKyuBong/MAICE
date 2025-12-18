import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => ({
	plugins: [sveltekit(), tailwindcss()],
	esbuild: {
		// 프로덕션 빌드 시 console.log 제거
		drop: mode === 'production' ? ['console', 'debugger'] : [],
	},
	ssr: {
		// SSR에서 외부 의존성을 제외하여 순환 의존성 문제 해결
		external: ['svelte/internal'],
		noExternal: []
	},
	optimizeDeps: {
		// 의존성 사전 번들링에서 제외할 패키지들
		exclude: ['svelte/internal']
	},
	server: {
		host: '0.0.0.0',
		port: 5173,
		proxy: {
			// API 요청을 백엔드로 프록시
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				secure: false,
				// CORS 헤더 설정
				configure: (proxy, _options) => {
					proxy.on('error', (err, _req, _res) => {
						console.log('프록시 오류:', err);
					});
					proxy.on('proxyReq', (proxyReq, req, _res) => {
						console.log('프록시 요청:', req.method, req.url);
					});
					proxy.on('proxyRes', (proxyRes, req, _res) => {
						console.log('프록시 응답:', proxyRes.statusCode, req.url);
					});
				}
			}
		}
	}
}));
