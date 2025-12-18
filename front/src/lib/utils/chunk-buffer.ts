/**
 * 청크 순서 보장을 위한 프론트엔드 버퍼링 유틸리티
 */

export interface ChunkData {
  chunk_index: number;
  content: string;
  is_final: boolean;
  timestamp: string;
  received_at: number;
}

export class ChunkBuffer {
  private chunks: Map<number, ChunkData> = new Map();
  private nextExpectedIndex = 0;  // 0부터 시작하도록 수정
  private lastSentIndex = -1;  // -1부터 시작하도록 수정
  private timeout = 2000; // 2초 타임아웃
  private maxGap = 20; // 최대 허용 청크 간격
  private lastChunkTime = Date.now();
  private isComplete = false;

  constructor(private sessionId: number) {}

  /**
   * 청크 추가 및 정렬된 텍스트 반환
   */
  addChunk(chunk_index: number, content: string, is_final: boolean, timestamp: string): string {
    const currentTime = Date.now();
    
    // 청크 저장
    this.chunks.set(chunk_index, {
      chunk_index,
      content,
      is_final,
      timestamp,
      received_at: currentTime
    });
    
    this.lastChunkTime = currentTime;
    
    if (is_final) {
      this.isComplete = true;
      console.log(`🏁 최종 청크 수신: 세션 ${this.sessionId}, 인덱스 ${chunk_index}`);
    }
    
    console.log(`📥 청크 버퍼에 추가: 세션 ${this.sessionId}, 인덱스 ${chunk_index}, 다음 예상 ${this.nextExpectedIndex}`);
    
    // 정렬된 텍스트 반환
    return this.getOrderedText();
  }
  
  /**
   * 순서대로 정렬된 전체 텍스트 반환
   */
  getOrderedText(): string {
    const currentTime = Date.now();
    
    // 전송 가능한 청크들 수집 (이 과정에서 lastSentIndex가 업데이트됨)
    const sendableChunks = this.getSendableChunks(currentTime);
    
    // sendableChunks가 비어있으면 이미 전송된 청크들만 반환
    if (sendableChunks.length === 0) {
      const alreadySent = Array.from(this.chunks.values())
        .filter(chunk => chunk.chunk_index <= this.lastSentIndex)
        .sort((a, b) => a.chunk_index - b.chunk_index);
      return alreadySent.map(chunk => chunk.content).join('');
    }
    
    // 순서대로 정렬된 전체 텍스트 반환 (이미 전송된 것 + 새로 전송 가능한 것)
    const allSentChunks = Array.from(this.chunks.values())
      .filter(chunk => chunk.chunk_index <= this.lastSentIndex)
      .sort((a, b) => a.chunk_index - b.chunk_index);
    
    return allSentChunks.map(chunk => chunk.content).join('');
  }
  
  private getSendableChunks(currentTime: number): ChunkData[] {
    const sendableChunks: ChunkData[] = [];
    
    // 다음 예상 인덱스부터 연속된 청크들 찾기
    let index = this.nextExpectedIndex;
    while (this.chunks.has(index)) {
      const chunk = this.chunks.get(index)!;
      sendableChunks.push(chunk);
      this.lastSentIndex = index;
      index++;
    }
    
    // 다음 예상 인덱스 업데이트
    if (sendableChunks.length > 0) {
      this.nextExpectedIndex = this.lastSentIndex + 1;
    }
    
    // 타임아웃 또는 완료 상태인 경우 누락된 청크 건너뛰기
    if (this.shouldSkipMissingChunks(currentTime)) {
      const skippedChunks = this.skipMissingChunks();
      sendableChunks.push(...skippedChunks);
    }
    
    return sendableChunks;
  }
  
  private shouldSkipMissingChunks(currentTime: number): boolean {
    // 타임아웃 체크
    const timeSinceLastChunk = currentTime - this.lastChunkTime;
    if (timeSinceLastChunk > this.timeout) {
      return true;
    }
    
    // 최대 간격 체크
    if (this.chunks.size > 0) {
      const maxReceivedIndex = Math.max(...this.chunks.keys());
      const gap = maxReceivedIndex - this.lastSentIndex;
      if (gap > this.maxGap) {
        return true;
      }
    }
    
    // 완료 상태인 경우
    if (this.isComplete) {
      return true;
    }
    
    return false;
  }
  
  private skipMissingChunks(): ChunkData[] {
    if (this.chunks.size === 0) {
      return [];
    }
    
    // 받은 청크들 중 아직 전송하지 않은 것들을 순서대로 반환
    const availableIndices = Array.from(this.chunks.keys())
      .filter(index => index > this.lastSentIndex)
      .sort((a, b) => a - b);
    
    const skippedChunks: ChunkData[] = [];
    for (const index of availableIndices) {
      const chunk = this.chunks.get(index)!;
      skippedChunks.push(chunk);
      this.lastSentIndex = index;
    }
    
    if (skippedChunks.length > 0) {
      this.nextExpectedIndex = this.lastSentIndex + 1;
      console.warn(`⚠️ 누락된 청크 건너뛰기: 세션 ${this.sessionId}, ${skippedChunks.length}개 청크`);
    }
    
    return skippedChunks;
  }
  
  /**
   * 버퍼 상태 정보 반환
   */
  getStatus() {
    return {
      sessionId: this.sessionId,
      nextExpectedIndex: this.nextExpectedIndex,
      lastSentIndex: this.lastSentIndex,
      bufferedChunks: this.chunks.size,
      isComplete: this.isComplete,
      chunksInBuffer: Array.from(this.chunks.keys()).sort((a, b) => a - b)
    };
  }
  
  /**
   * 버퍼 정리
   */
  clear() {
    this.chunks.clear();
    this.nextExpectedIndex = 0;
    this.lastSentIndex = -1;
    this.isComplete = false;
  }
}

export class ChunkBufferManager {
  private buffers: Map<number, ChunkBuffer> = new Map();
  
  /**
   * 세션별 청크 버퍼 반환 (없으면 생성)
   */
  getBuffer(sessionId: number): ChunkBuffer {
    if (!this.buffers.has(sessionId)) {
      this.buffers.set(sessionId, new ChunkBuffer(sessionId));
      console.log(`🆕 새 청크 버퍼 생성: 세션 ${sessionId}`);
    }
    return this.buffers.get(sessionId)!;
  }
  
  /**
   * 세션 버퍼 제거
   */
  removeBuffer(sessionId: number) {
    if (this.buffers.has(sessionId)) {
      this.buffers.delete(sessionId);
      console.log(`🗑️ 청크 버퍼 제거: 세션 ${sessionId}`);
    }
  }
  
  /**
   * 모든 버퍼 정리
   */
  clearAll() {
    this.buffers.clear();
    console.log('🧹 모든 청크 버퍼 정리 완료');
  }
}

// 전역 청크 버퍼 매니저
export const chunkBufferManager = new ChunkBufferManager();
