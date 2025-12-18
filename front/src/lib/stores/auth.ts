import { writable, get } from 'svelte/store';
import { getCurrentUser } from '$lib/api';

export interface User {
	id: number;
	username: string;
	role: 'student' | 'teacher' | 'admin';
	access_token: string;
	// 추가 사용자 정보
	email?: string;
	name?: string;
	google_id?: string;
	google_email?: string;
	google_name?: string;
	google_picture?: string;
	google_verified_email?: boolean;
	// 연구 동의 관련 정보
	research_consent?: boolean;
	research_consent_date?: string;
	research_consent_version?: string;
	research_consent_withdrawn_at?: string;
}

interface AuthState {
	isAuthenticated: boolean;
	user: User | null;
	token: string | null;
	loading: boolean;
}

// 초기 상태를 로컬 스토리지에서 복원
const getInitialState = (): AuthState => {
	if (typeof window !== 'undefined') {
		const savedAuth = localStorage.getItem('maice_auth');
		if (savedAuth) {
			try {
				const authData = JSON.parse(savedAuth);
				return {
					isAuthenticated: true,
					user: authData,
					token: authData.access_token || null,
					loading: false
				};
			} catch (error) {
				console.error('저장된 인증 정보를 불러올 수 없습니다:', error);
				localStorage.removeItem('maice_auth');
			}
		}
	}
	
	return {
		isAuthenticated: false,
		user: null,
		token: null,
		loading: false
	};
};

export const authStore = writable<AuthState>(getInitialState());

export const authActions = {
	login: (user: User) => {
		authStore.update(state => ({
			...state,
			isAuthenticated: true,
			user,
			token: user.access_token,
			loading: false
		}));
		
		// 로컬 스토리지에 저장
		if (typeof window !== 'undefined') {
			localStorage.setItem('maice_auth', JSON.stringify(user));
		}
	},
	
	loginWithToken: async (token: string) => {
		try {
			// /me 엔드포인트를 통해 사용자 정보 조회
			const userData = await getCurrentUser(token);
			
			const user: User = {
				id: userData.id,
				username: userData.username,
				role: userData.role as 'student' | 'teacher' | 'admin',
				access_token: token,
				email: userData.email,
				name: userData.name,
				google_id: userData.google_id,
				google_email: userData.google_email,
				google_name: userData.google_name,
				google_picture: userData.google_picture,
				google_verified_email: userData.google_verified_email,
				// 연구 동의 정보 추가
				research_consent: userData.research_consent,
				research_consent_date: userData.research_consent_date,
				research_consent_version: userData.research_consent_version,
				research_consent_withdrawn_at: userData.research_consent_withdrawn_at
			};
			
			authStore.update(state => ({
				...state,
				isAuthenticated: true,
				user,
				token: token,
				loading: false
			}));
			
			// 로컬 스토리지에 저장
			if (typeof window !== 'undefined') {
				localStorage.setItem('maice_auth', JSON.stringify(user));
			}
			
			return user;
		} catch (error) {
			console.error('사용자 정보 조회 오류:', error);
			throw error;
		}
	},
	
	logout: async () => {
		try {
			// 백엔드 로그아웃 API 호출
			const currentState = get(authStore);
			const token = currentState?.user?.access_token;
			if (token) {
				try {
					const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
					
					await fetch(`${apiBaseUrl}/api/auth/logout`, {
						method: 'POST',
						headers: {
							'Authorization': `Bearer ${token}`,
							'Content-Type': 'application/json'
						}
					});
				} catch (error) {
					console.warn('백엔드 로그아웃 API 호출 실패:', error);
				}
			}
		} catch (error) {
			console.warn('로그아웃 처리 중 오류:', error);
		}
		
		// 프론트엔드 상태 초기화
		authStore.update(state => ({
			...state,
			isAuthenticated: false,
			user: null,
			token: null,
			loading: false
		}));
		
		// 모든 로컬 저장소 정리
		if (typeof window !== 'undefined') {
			// 인증 정보 제거
			localStorage.removeItem('maice_auth');
			localStorage.removeItem('auth_token');
			localStorage.removeItem('user_info');
			
			// 세션 스토리지도 정리
			sessionStorage.removeItem('maice_auth');
			sessionStorage.removeItem('auth_token');
			sessionStorage.removeItem('user_info');
			
			// 쿠키도 정리 (가능한 경우)
			document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
			document.cookie = 'maice_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
			
			console.log('✅ 모든 인증 정보가 완전히 정리되었습니다');
		}
	},
	
	setLoading: (loading: boolean) => {
		authStore.update(state => ({
			...state,
			loading
		}));
	},
	
	updateUser: (updates: Partial<User>) => {
		authStore.update(state => {
			if (state.user) {
				const updatedUser = { ...state.user, ...updates };
				
				// 로컬 스토리지 업데이트
				if (typeof window !== 'undefined') {
					localStorage.setItem('maice_auth', JSON.stringify(updatedUser));
				}
				
				return {
					...state,
					user: updatedUser
				};
			}
			return state;
		});
	},
	
	// 토큰 유효성 검증
	checkTokenValidity: async (): Promise<boolean> => {
		try {
			const currentState = get(authStore);
			const token = currentState?.token;
			
			if (!token) {
				console.warn('⚠️ 토큰이 없습니다');
				return false;
			}
			
			const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '';
			
			// 백엔드에서 토큰 검증
			const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
				method: 'GET',
				headers: {
					'Authorization': `Bearer ${token}`,
					'Content-Type': 'application/json'
				}
			});
			
			if (response.ok) {
				console.log('✅ 토큰이 유효합니다');
				return true;
			} else {
				console.warn('⚠️ 토큰이 만료되었거나 유효하지 않습니다');
				return false;
			}
		} catch (error) {
			console.error('❌ 토큰 검증 중 오류 발생:', error);
			return false;
		}
	}
};
