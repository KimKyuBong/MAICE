import { writable, get } from 'svelte/store';
import { getResearchConsentStatus, updateResearchConsent } from '$lib/api';

interface ConsentState {
	hasConsented: boolean;
	consentDate: string | null;
	consentVersion: string | null;
}

interface ConsentData {
	consent: boolean;
	date: string;
	version: string;
}

const CONSENT_STORAGE_KEY = 'maice_research_consent';
const CURRENT_CONSENT_VERSION = '1.0';

// 초기 상태를 로컬 스토리지에서 복원
const getInitialConsentState = (): ConsentState => {
	if (typeof window !== 'undefined') {
		try {
			const savedConsent = localStorage.getItem(CONSENT_STORAGE_KEY);
			if (savedConsent) {
				const consentData: ConsentData = JSON.parse(savedConsent);
				
				// 버전 체크 - 향후 동의서 업데이트 시 새로 동의받을 수 있도록
				if (consentData.consent && consentData.version === CURRENT_CONSENT_VERSION) {
					return {
						hasConsented: true,
						consentDate: consentData.date,
						consentVersion: consentData.version
					};
				} else {
					// 버전이 다르면 이전 동의 무효화
					console.log('이전 버전의 동의서입니다. 새로 동의받습니다.');
					localStorage.removeItem(CONSENT_STORAGE_KEY);
				}
			}
		} catch (error) {
			console.error('저장된 동의 정보를 불러올 수 없습니다:', error);
			localStorage.removeItem(CONSENT_STORAGE_KEY);
		}
	}
	
	return {
		hasConsented: false,
		consentDate: null,
		consentVersion: null
	};
};

export const consentStore = writable<ConsentState>(getInitialConsentState());

export const consentActions = {
	// 동의 상태 저장 (백엔드 API 호출)
	acceptConsent: async (token: string) => {
		try {
			// 백엔드에 동의 상태 전송
			const response = await updateResearchConsent(token, true, CURRENT_CONSENT_VERSION);
			
			if (response) {
				// 성공 시 로컬 스토리지와 스토어 업데이트
				const consentData: ConsentData = {
					consent: true,
					date: new Date().toISOString(),
					version: CURRENT_CONSENT_VERSION
				};
				
				if (typeof window !== 'undefined') {
					localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consentData));
				}
				
				consentStore.update(state => ({
					hasConsented: true,
					consentDate: consentData.date,
					consentVersion: consentData.version
				}));
				
				console.log('✅ 연구 참여 동의 완료:', consentData);
				return true;
			}
			return false;
		} catch (error) {
			console.error('❌ 연구 동의 업데이트 실패:', error);
			throw error;
		}
	},
	
	// 동의 철회 (백엔드 API 호출)
	withdrawConsent: async (token: string) => {
		try {
			// 백엔드에 동의 철회 상태 전송
			const response = await updateResearchConsent(token, false, CURRENT_CONSENT_VERSION);
			
			if (response) {
				// 성공 시 로컬 스토리지와 스토어 업데이트
				if (typeof window !== 'undefined') {
					localStorage.removeItem(CONSENT_STORAGE_KEY);
				}
				
				consentStore.update(state => ({
					hasConsented: false,
					consentDate: null,
					consentVersion: null
				}));
				
				console.log('🔄 연구 참여 동의 철회됨');
				return true;
			}
			return false;
		} catch (error) {
			console.error('❌ 연구 동의 철회 실패:', error);
			throw error;
		}
	},
	
	// 동의 상태 확인
	checkConsent: (): boolean => {
		const currentState = getInitialConsentState();
		return currentState.hasConsented;
	},
	
	// 현재 동의 정보 가져오기
	getConsentInfo: (): ConsentState => {
		return getInitialConsentState();
	},
	
	// 백엔드에서 동의 상태 동기화
	syncConsentFromBackend: async (token: string) => {
		try {
			const response = await getResearchConsentStatus(token);
			
			if (response) {
				const hasConsent = response.research_consent && !response.research_consent_withdrawn_at;
				
				// 백엔드 데이터로 스토어 업데이트
				consentStore.update(state => ({
					hasConsented: hasConsent,
					consentDate: response.research_consent_date,
					consentVersion: response.research_consent_version
				}));
				
				// 로컬 스토리지도 동기화
				if (typeof window !== 'undefined') {
					if (hasConsent) {
						const consentData: ConsentData = {
							consent: true,
							date: response.research_consent_date || new Date().toISOString(),
							version: response.research_consent_version || CURRENT_CONSENT_VERSION
						};
						localStorage.setItem(CONSENT_STORAGE_KEY, JSON.stringify(consentData));
					} else {
						localStorage.removeItem(CONSENT_STORAGE_KEY);
					}
				}
				
				console.log('✅ 백엔드에서 연구 동의 상태 동기화 완료:', hasConsent);
				return hasConsent;
			}
			return false;
		} catch (error) {
			console.error('❌ 백엔드 동의 상태 동기화 실패:', error);
			return false;
		}
	}
};
