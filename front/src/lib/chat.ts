import { submitQuestionStream } from './api';

/**
 * MAICE 챗봇 실시간 통신 클래스
 * SSE를 통해 진행 상황과 답변을 실시간으로 수신
 */

export interface ProgressData {
  request_id: string;
  stage: string;
  message: string;
  progress: number;
  timestamp: string;
}

export interface AnswerChunk {
  chunk: string;
  order: number;
  timestamp: string;
}

export interface StreamData {
  type: 'update' | 'error';
  request_id: string;
  timestamp: string;
  progress?: ProgressData;
  answer_chunks?: AnswerChunk[];
  error?: string;
}

export class ChatService {
  private eventSource: EventSource | null = null;
  private isConnected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    private onProgressUpdate?: (progress: ProgressData) => void,
    private onAnswerUpdate?: (chunks: AnswerChunk[]) => void,
    private onError?: (error: string) => void,
    private onComplete?: () => void
  ) {}

  /**
   * 질문 전송 및 SSE 스트리밍 시작
   */
  async sendQuestion(question: string, sessionId?: number, token?: string): Promise<void> {
    try {
      // SSE 스트리밍으로 직접 질문 전송
      await submitQuestionStream(
        token || '',
        question,
        sessionId,
        (data) => {
          console.log('📨 SSE 메시지 수신:', data);
          console.log('📨 메시지 타입:', data.type);
          
          // 메시지 타입에 따른 처리
          switch (data.type) {
            case 'connected':
              console.log('✅ MAICE 채팅 연결됨:', data.message);
              break;
              
            case 'processing':
              if (this.onProgressUpdate) {
                this.onProgressUpdate({
                  request_id: data.request_id,
                  stage: 'processing',
                  message: data.message,
                  progress: data.progress,
                  timestamp: new Date().toISOString()
                });
              }
              break;
              
            case 'clarification_questions':
              if (this.onAnswerUpdate) {
                // 명료화 질문을 배열로 받아서 처리
                const questions = data.questions || [data.message];
                const questionText = Array.isArray(questions) ? questions.join('\n') : questions;
                
                this.onAnswerUpdate([{
                  chunk: questionText,
                  order: 0,
                  timestamp: new Date().toISOString()
                }]);
              }
              break;
              
            case 'answer_chunk':
              if (this.onAnswerUpdate) {
                this.onAnswerUpdate([{
                  chunk: data.chunk,
                  order: data.chunk_index,
                  timestamp: new Date().toISOString()
                }]);
              }
              break;
              
            case 'streaming_start':
              if (this.onProgressUpdate) {
                this.onProgressUpdate({
                  request_id: data.request_id || 'unknown',
                  stage: 'streaming',
                  message: data.message,
                  progress: data.progress || 70,
                  timestamp: new Date().toISOString()
                });
              }
              break;
              
            case 'streaming_complete':
              if (this.onComplete) {
                this.onComplete();
              }
              break;
              
            case 'answer_complete':
              if (this.onComplete) {
                this.onComplete();
              }
              break;
              
            case 'error':
              if (this.onError) {
                this.onError(data.message);
              }
              break;
              
            default:
              console.log('알 수 없는 메시지 타입:', data.type);
          }
        },
        (error) => {
          if (this.onError) {
            this.onError(error.message);
          }
        },
        () => {
          if (this.onComplete) {
            this.onComplete();
          }
        }
      );
      
    } catch (error) {
      console.error('질문 전송 실패:', error);
      if (this.onError) {
        this.onError(error.message);
      }
    }
  }

  /**
   * SSE 스트리밍 시작
   */
  startStreaming(requestId: string): void {
    if (this.eventSource) {
      this.eventSource.close();
    }

    const url = `/api/v1/student/chat/stream/${requestId}`;
    this.eventSource = new EventSource(url);
    
    this.isConnected = true;
    this.reconnectAttempts = 0;

    this.eventSource.onopen = () => {
      console.log('SSE 연결 성공');
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data: StreamData = JSON.parse(event.data);
        this.handleStreamData(data);
      } catch (error) {
        console.error('스트림 데이터 파싱 오류:', error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE 연결 오류:', error);
      this.isConnected = false;
      this.handleReconnect(requestId);
    };
  }

  /**
   * 스트림 데이터 처리
   */
  private handleStreamData(data: StreamData): void {
    switch (data.type) {
      case 'update':
        if (data.progress) {
          this.onProgressUpdate?.(data.progress);
          
          // 완료 체크
          if (data.progress.stage === 'completed') {
            this.onComplete?.();
            this.close();
          }
        }
        
        if (data.answer_chunks && data.answer_chunks.length > 0) {
          this.onAnswerUpdate?.(data.answer_chunks);
        }
        break;
        
      case 'error':
        this.onError?.(data.error || '알 수 없는 오류가 발생했습니다');
        this.close();
        break;
    }
  }

  /**
   * 재연결 처리
   */
  private handleReconnect(requestId: string): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
      
      setTimeout(() => {
        this.startStreaming(requestId);
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('최대 재연결 시도 횟수 초과');
      this.onError?.('연결이 끊어졌습니다. 페이지를 새로고침해주세요.');
    }
  }

  /**
   * 연결 종료
   */
  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnected = false;
  }

  /**
   * 연결 상태 확인
   */
  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

/**
 * 채팅 UI 상태 관리
 */
export class ChatState {
  private messages: Array<{
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
  }> = [];
  
  private currentAnswer: string = '';
  private isProcessing = false;

  constructor(
    private onMessageUpdate?: (messages: any[]) => void,
    private onAnswerUpdate?: (answer: string) => void,
    private onProcessingUpdate?: (isProcessing: boolean) => void
  ) {}

  /**
   * 사용자 메시지 추가
   */
  addUserMessage(content: string): void {
    const message = {
      id: Date.now().toString(),
      type: 'user' as const,
      content,
      timestamp: new Date(),
    };
    
    this.messages.push(message);
    this.onMessageUpdate?.(this.messages);
  }

  /**
   * 답변 조각 추가
   */
  addAnswerChunk(chunk: string): void {
    this.currentAnswer += chunk;
    this.onAnswerUpdate?.(this.currentAnswer);
  }

  /**
   * 답변 완성
   */
  completeAnswer(): void {
    if (this.currentAnswer) {
      const message = {
        id: Date.now().toString(),
        type: 'assistant' as const,
        content: this.currentAnswer,
        timestamp: new Date(),
      };
      
      this.messages.push(message);
      this.currentAnswer = '';
      this.onMessageUpdate?.(this.messages);
    }
  }

  /**
   * 처리 상태 업데이트
   */
  setProcessing(isProcessing: boolean): void {
    this.isProcessing = isProcessing;
    this.onProcessingUpdate?.(isProcessing);
  }

  /**
   * 메시지 목록 반환
   */
  getMessages(): any[] {
    return this.messages;
  }

  /**
   * 현재 답변 반환
   */
  getCurrentAnswer(): string {
    return this.currentAnswer;
  }

  /**
   * 처리 상태 반환
   */
  getProcessingStatus(): boolean {
    return this.isProcessing;
  }
}
