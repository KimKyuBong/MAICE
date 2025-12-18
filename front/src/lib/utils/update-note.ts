/**
 * 업데이트 노트 관련 유틸리티 함수들
 */

// 현재 업데이트 노트 버전 (공지가 바뀌면 이 값을 변경해야 함)
export const CURRENT_UPDATE_NOTE_VERSION = '1.0';

export interface UpdateNoteStatus {
	read: boolean;
	date: string;
	version: string;
	doNotShowAgain?: boolean;
}

/**
 * 사용자가 업데이트 노트를 읽었는지 확인
 * @param userId 사용자 ID
 * @returns 업데이트 노트 읽음 상태
 */
export function hasUserReadUpdateNote(userId: string): boolean {
	if (typeof window === 'undefined') return false;
	
	try {
		const stored = localStorage.getItem(`maice_update_note_read_${userId}`);
		if (!stored) return false;
		
		const status: UpdateNoteStatus = JSON.parse(stored);
		
		// 버전이 다르면 새 공지로 간주하여 다시 표시
		if (status.version !== CURRENT_UPDATE_NOTE_VERSION) {
			console.log('📋 업데이트 노트 버전 변경 감지:', {
				oldVersion: status.version,
				currentVersion: CURRENT_UPDATE_NOTE_VERSION
			});
			return false;
		}
		
		// 다음에 보지 않기 체크박스를 선택했다면 true 반환
		if (status.doNotShowAgain === true) {
			return true;
		}
		
		return status.read === true;
	} catch (error) {
		console.error('업데이트 노트 상태 확인 오류:', error);
		return false;
	}
}

/**
 * 사용자가 업데이트 노트를 읽었다고 표시
 * @param userId 사용자 ID
 * @param version 업데이트 노트 버전 (기본값: CURRENT_UPDATE_NOTE_VERSION)
 */
export function markUpdateNoteAsRead(userId: string, version: string = CURRENT_UPDATE_NOTE_VERSION): void {
	if (typeof window === 'undefined') return;
	
	try {
		const status: UpdateNoteStatus = {
			read: true,
			date: new Date().toISOString(),
			version
		};
		
		localStorage.setItem(`maice_update_note_read_${userId}`, JSON.stringify(status));
		console.log(`✅ 사용자 ${userId}의 업데이트 노트 읽음 상태 저장됨`);
	} catch (error) {
		console.error('업데이트 노트 상태 저장 오류:', error);
	}
}

/**
 * 사용자의 업데이트 노트 읽음 상태를 초기화 (테스트용)
 * @param userId 사용자 ID
 */
export function resetUpdateNoteStatus(userId: string): void {
	if (typeof window === 'undefined') return;
	
	try {
		localStorage.removeItem(`maice_update_note_read_${userId}`);
		console.log(`🔄 사용자 ${userId}의 업데이트 노트 상태 초기화됨`);
	} catch (error) {
		console.error('업데이트 노트 상태 초기화 오류:', error);
	}
}

/**
 * 모든 사용자의 업데이트 노트 상태를 초기화 (관리자용)
 */
export function resetAllUpdateNoteStatus(): void {
	if (typeof window === 'undefined') return;
	
	try {
		const keys = Object.keys(localStorage);
		const updateNoteKeys = keys.filter(key => key.startsWith('maice_update_note_read_'));
		
		updateNoteKeys.forEach(key => {
			localStorage.removeItem(key);
		});
		
		console.log(`🔄 모든 사용자의 업데이트 노트 상태 초기화됨 (${updateNoteKeys.length}개)`);
	} catch (error) {
		console.error('모든 업데이트 노트 상태 초기화 오류:', error);
	}
}

/**
 * 현재 로그인된 사용자 ID 가져오기
 * @returns 사용자 ID 또는 null
 */
export function getCurrentUserId(): string | null {
	if (typeof window === 'undefined') return null;
	
	try {
		const savedAuth = localStorage.getItem('maice_auth');
		if (!savedAuth) return null;
		
		const authData = JSON.parse(savedAuth);
		return authData.id || null;
	} catch (error) {
		console.error('현재 사용자 ID 가져오기 오류:', error);
		return null;
	}
}
