'use client';

import { useState } from 'react';
import Image from 'next/image';
import TextEvaluation from './components/TextEvaluation';
import ImageEvaluation from './components/ImageEvaluation';

export default function Home() {
  const [evaluationType, setEvaluationType] = useState<'text' | 'image'>(
    'text'
  );

  return (
    <div className="grid grid-rows-[auto_1fr_auto] min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
      <header>
        <Image
          className="dark:invert mx-auto"
          src="https://nextjs.org/icons/next.svg"
          alt="Next.js logo"
          width={180}
          height={38}
          priority
        />
      </header>
      <main className="flex flex-col gap-8 items-center">
        <h1 className="text-4xl font-bold mb-8 text-center">
          수학 답변 평가 앱
        </h1>

        <div className="mb-8 text-center">
          <button
            className={`mr-4 px-4 py-2 rounded ${
              evaluationType === 'text'
                ? 'bg-foreground text-background'
                : 'bg-background text-foreground border border-foreground'
            }`}
            onClick={() => setEvaluationType('text')}
          >
            텍스트 평가
          </button>
          <button
            className={`px-4 py-2 rounded ${
              evaluationType === 'image'
                ? 'bg-foreground text-background'
                : 'bg-background text-foreground border border-foreground'
            }`}
            onClick={() => setEvaluationType('image')}
          >
            이미지 평가
          </button>
        </div>

        {evaluationType === 'text' ? <TextEvaluation /> : <ImageEvaluation />}
      </main>
      <footer className="text-center text-sm">© 2024 수학 답변 평가 앱</footer>
    </div>
  );
}
