/**
 * 환경별 로거 유틸리티
 * 개발 환경에서만 로그를 출력하고, 프로덕션에서는 무시
 */

const isDevelopment = import.meta.env.DEV || import.meta.env.VITE_ENVIRONMENT === 'development';

// 로그 레벨 정의
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 4
}

// 현재 로그 레벨 설정 (환경 변수로 제어 가능)
const currentLogLevel = isDevelopment ? LogLevel.DEBUG : LogLevel.ERROR;

class Logger {
  private context?: string;

  constructor(context?: string) {
    this.context = context;
  }

  private formatMessage(level: string, ...args: any[]): any[] {
    if (this.context) {
      return [`[${this.context}] ${level}:`, ...args];
    }
    return [`${level}:`, ...args];
  }

  debug(...args: any[]): void {
    if (currentLogLevel <= LogLevel.DEBUG) {
      console.log(...this.formatMessage('DEBUG', ...args));
    }
  }

  info(...args: any[]): void {
    if (currentLogLevel <= LogLevel.INFO) {
      console.info(...this.formatMessage('INFO', ...args));
    }
  }

  warn(...args: any[]): void {
    if (currentLogLevel <= LogLevel.WARN) {
      console.warn(...this.formatMessage('WARN', ...args));
    }
  }

  error(...args: any[]): void {
    if (currentLogLevel <= LogLevel.ERROR) {
      console.error(...this.formatMessage('ERROR', ...args));
    }
  }

  // 특정 이모지 로그 (개발 환경에서만)
  emoji(emoji: string, ...args: any[]): void {
    if (currentLogLevel <= LogLevel.DEBUG) {
      console.log(emoji, ...args);
    }
  }
}

// 기본 로거
export const logger = new Logger();

// 컨텍스트별 로거 생성
export const createLogger = (context: string): Logger => {
  return new Logger(context);
};

// 편의 함수들 (기존 console.log 대체용)
export const log = {
  debug: (...args: any[]) => logger.debug(...args),
  info: (...args: any[]) => logger.info(...args),
  warn: (...args: any[]) => logger.warn(...args),
  error: (...args: any[]) => logger.error(...args),
  
  // 이모지 로그 (개발용)
  success: (...args: any[]) => logger.emoji('✅', ...args),
  error_emoji: (...args: any[]) => logger.emoji('❌', ...args),
  warning: (...args: any[]) => logger.emoji('⚠️', ...args),
  rocket: (...args: any[]) => logger.emoji('🚀', ...args),
  search: (...args: any[]) => logger.emoji('🔍', ...args),
  message: (...args: any[]) => logger.emoji('📨', ...args),
  write: (...args: any[]) => logger.emoji('📝', ...args),
  connected: (...args: any[]) => logger.emoji('🔗', ...args),
  complete: (...args: any[]) => logger.emoji('🎉', ...args),
  processing: (...args: any[]) => logger.emoji('⚙️', ...args),
  sending: (...args: any[]) => logger.emoji('📤', ...args),
  receiving: (...args: any[]) => logger.emoji('📥', ...args),
  refresh: (...args: any[]) => logger.emoji('🔄', ...args),
  delete: (...args: any[]) => logger.emoji('🗑️', ...args),
  create: (...args: any[]) => logger.emoji('🆕', ...args),
  update: (...args: any[]) => logger.emoji('🔄', ...args),
  key: (...args: any[]) => logger.emoji('🔑', ...args),
  id: (...args: any[]) => logger.emoji('🆔', ...args),
  chart: (...args: any[]) => logger.emoji('📊', ...args),
  boom: (...args: any[]) => logger.emoji('💥', ...args),
  disconnect: (...args: any[]) => logger.emoji('🔌', ...args),
};

export default logger;
