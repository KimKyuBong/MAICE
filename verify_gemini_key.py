import os
import sys

import google.generativeai as genai


def main() -> int:
    """
    GEMINI_API_KEY 유효성(Generative Language API 호출 가능 여부)을 간단히 검증합니다.

    사용법:
      GEMINI_API_KEY="..." python verify_gemini_key.py
      GEMINI_MODEL="gemini-2.5-flash-lite" GEMINI_API_KEY="..." python verify_gemini_key.py
    """
    key = os.getenv("GEMINI_API_KEY", "")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    print("GEMINI_API_KEY len:", len(key))
    print("GEMINI_API_KEY prefix/suffix:", key[:6], key[-4:])
    print("GEMINI_MODEL:", model_name)

    if not key:
        print("ERROR: GEMINI_API_KEY is empty")
        return 2

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content("ping")
        text = getattr(resp, "text", "") or ""
        print("OK:", text[:200])
        return 0
    except Exception as e:
        print("FAIL:", type(e).__name__, str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


