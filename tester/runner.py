import asyncio
import json
import os
import random
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

# 로깅 설정 추가
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/output/tester.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    import orjson as jsonlib
except Exception:
    jsonlib = None

import redis.asyncio as redis

# 선택적 LLM 활용
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore

QUESTION_SUBMITTED = "question.submitted"
ANSWER_COMPLETED = "answer.completed"
ANSWER_REQUESTED = "answer.requested"

TOPICS = ["수열", "점화식", "귀납법"]

PERSONAS: List[Dict[str, Any]] = [
    {"id": "model_student", "name": "모범학생", "style": "정중한 존댓말, 군더더기 없이 명확하게 질문. 수학기호/용어 정확히 사용. 이모지/은어 없음."},
    {"id": "shy_inquisitive", "name": "소심한 꼬리질문러", "style": "조심스러운 존댓말, 말끝 흐림(…요?), 확신 없는 톤. 간단히 재확인 질문 자주."},
    {"id": "free_spirited", "name": "자유분방한 학생", "style": "반말 위주, 가벼운 구어체. 짧게 끊어 말함. 이모지/은어 과용 금지."},
    {"id": "curious_gamer", "name": "겜잘알 호기심 학생", "style": "게임/레벨 비유 가볍게 1회 이하, 질문형 끝맺음. 반존대 혼용 가능."},
    {"id": "gamer_kid", "name": "겜잘알 학생(세컨)", "style": "게임 시스템 비유 1회 이하. 반말 위주, 장황함 금지."},
    {"id": "kpop_fan", "name": "K-POP 덕후", "style": "가벼운 팬심 비유 1회 이하. 핵심은 수학. 말투는 밝고 경쾌."},
    {"id": "sports_captain", "name": "운동부 주장", "style": "직설적/간결, 체감 위주 표현. 존댓말 기본이지만 딱딱하진 않음."},
    {"id": "math_olympiad", "name": "경시 준비생", "style": "정밀한 용어/기호 사용, 반례/조건 집착. 존댓말, 문장 길어도 논리적."},
    {"id": "artsy_poet", "name": "문학적 비유형", "style": "직관/이미지화 비유 1회 이하. 온화한 반말·반존대. 핵심 수학은 정확히."},
    {"id": "meme_speaker", "name": "밈 섞어 말하는 학생", "style": "라이트한 인터넷 밈 1회 이하, 과한 신조어/이모지 금지. 반말 중심."},
    {"id": "busan_dialect", "name": "부산 사투리 학생", "style": "경상 방언 살짝(끝음 처리 정도). 반말. 과도한 방언 표현은 피함."},
    {"id": "jeolla_dialect", "name": "전라 사투리 학생", "style": "전라 방언 티 살짝, 부드러운 말투. 반말 위주."},
    {"id": "nocturnal_crammer", "name": "밤샘 벼락치기", "style": "피곤/급함 드러남. 짧고 직설. 존댓말/반말 섞임."},
    {"id": "pragmatic_skeptic", "name": "현실적인 회의론자", "style": "효율/시험 대응 위주 질문. 존댓말, 단호하지만 예의 지킴."},
    {"id": "anxious_test_taker", "name": "불안한 수험생", "style": "확인성 질문 많음. 조심스런 존댓말, 말줄임표 간간히."},
    {"id": "class_clown", "name": "분위기메이커", "style": "장난 섞인 톤 1회 이하. 핵심은 바로 묻기. 반말."},
    {"id": "transfer_student", "name": "전학생(영단어 섞임)", "style": "간단한 영어 단어 1회 이하 혼용. 존댓말/반말 혼재 가능. 과한 콩글리시 금지."},
    {"id": "science_nerd", "name": "과학덕후", "style": "물리/컴퓨터 비유 1회 이하. 논리 정연, 존댓말."},
    {"id": "humanities_leaning", "name": "문과톤 수포자", "style": "직관/예시 위주. 쉬운 표현 선호, 존댓말. 자기비하 금지."},
    {"id": "perfectionist", "name": "완벽주의자", "style": "정의/조건/반례 끝까지 확인. 존댓말, 문장 길어지지만 정리해서 묻기."},
    {"id": "slangy_hothead", "name": "거친 말투(라이트 욕 허용)", "style": "반말, 가벼운 비속어 0~1회 허용(예: ‘개어렵다’, ‘빡세다’). 인신공격/혐오 금지. 과한 욕설 금지."},
    {"id": "tilted_gamer", "name": "랭크 기 tilted 게이머", "style": "반말, 배배 꼬인 톤. 라이트 욕 0~1회(예: ‘현타 온다’, ‘멘붕’). 공격적 표현 금지."},
    {"id": "absurdist_daydreamer", "name": "엉뚱한 몽상가", "style": "뜬금없는 상상 비유 1회 이하 후 바로 핵심으로 복귀. 말투는 부드러운 반말. 불필요한 장문 금지."},
    {"id": "nonsense_jester", "name": "드립치는 어수선이", "style": "가벼운 드립/말장난 1회 이하. 의미 없으면 곧장 본론. 과한 밈/이모지 금지."},
    {"id": "self_deprecating_soft", "name": "가벼운 자조형", "style": "소심한 존댓말. 가벼운 자조 0~1회 허용(심한 자기비하·자해 암시 금지). 마지막엔 요점 질문."},
    {"id": "imposter_vibes", "name": "자신감 부족형", "style": "확인성 질문 잦음. ‘제가 놓친 걸까요?’ 같은 표현 사용. 공손한 존댓말, 장황함 지양."},
    {"id": "irritated_shortfuse", "name": "쉽게 짜증내는 단답형", "style": "짧고 퉁명. 군더더기 없이 핵심만 묻기. 비속어는 사용하지 않음. 이모지/밈 금지."},
    {"id": "angry_time_crunched", "name": "시간압박 받는 버럭형", "style": "초조/짜증 드러남. 라이트 비속어 0~1회 허용(예: ‘빡세다’). 인신공격/혐오 금지. 짧고 직설."},
    {"id": "contrarian_debater", "name": "딴지거는 토론러", "style": "반문/반례로 시작. 정중하지만 날카롭게 논점 확인. 불필요한 공격적 표현 금지."},
    {"id": "sarcastic_dry", "name": "건조한 냉소가", "style": "건조한 비꼼 0~1회 허용. 모욕/조롱 금지. 핵심은 명확히 질문."},
    {"id": "scatter_brained", "name": "산만한 TMI형", "style": "맥락 튐 1회까지 허용 후 ‘요점’ 한 줄로 정리 요청. 반말 위주, 장황함 금지."},
    {"id": "whiny_but_curious", "name": "징징대는 호기심형", "style": "가벼운 푸념 0~1회, 결국 호기심으로 요점 묻기. 반존대 혼용 가능. 과한 불평 금지."},
]

LEVELS: List[Dict[str, Any]] = [
    {
        "id": "naive",
        "name": "완전 기초",
        "style": "아주 기초 개념부터 묻는 톤, 정의/의미 위주, 한두 문장",
        "prompt": "가장 기초적인 정의나 개념을 묻고, 왜 그런지 간단히 확인하려는 톤으로 1~2문장으로 표현.",
    },
    {
        "id": "basic",
        "name": "기초 응용",
        "style": "쉬운 예시를 원하고, 시험에서 바로 쓰는 요령 선호",
        "prompt": "간단한 예시나 직관적 설명을 요청. 시험에서 바로 쓰는 팁/요령을 한 줄로 물어보기.",
    },
    {
        "id": "intermediate",
        "name": "중간 난이도",
        "style": "핵심 원리나 일반항/증명 아이디어를 함께 묻는 톤",
        "prompt": "개념 이해와 함께 일반항/귀납 아이디어 등 핵심 원리를 간단히 확인하는 식으로 1~2문장.",
    },
    {
        "id": "advanced",
        "name": "심화",
        "style": "조건/예외/반례 가능성까지 짚는 분석적 톤",
        "prompt": "조건과 예외, 반례 가능성, 경계 상황을 짚어보는 심화 질문으로 1~2문장. 지나친 장문 금지.",
    },
    {
        "id": "olympiad",
        "name": "경시/증명",
        "style": "증명 관점, 엄밀/간결, 핵심 조건 정리",
        "prompt": "증명 관점에서 핵심 조건과 구조를 물으며, 필요시 반례/경계도 한 줄로 요청. 1~2문장.",
    },
]

def _parse_level_weights(spec: str) -> Dict[str, float]:
    default = {"naive": 0.2, "basic": 0.3, "intermediate": 0.25, "advanced": 0.2, "olympiad": 0.05}
    try:
        if not spec:
            return default
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        weights: Dict[str, float] = {}
        for part in parts:
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            k = k.strip()
            w = float(v.strip())
            if k:
                weights[k] = max(0.0, w)
        total = sum(weights.values())
        if total <= 0:
            return default
        # normalize
        for k in list(weights.keys()):
            weights[k] = weights[k] / total
        # ensure all ids exist at least with tiny weight for stability
        ids = {lvl["id"] for lvl in LEVELS}
        for i in ids:
            weights.setdefault(i, 0.0)
        return weights
    except Exception:
        return default

def _sample_level(weights: Dict[str, float]) -> Dict[str, Any]:
    try:
        r = random.random()
        cum = 0.0
        by_id = {lvl["id"]: lvl for lvl in LEVELS}
        for lvl_id, w in weights.items():
            cum += w
            if r <= cum:
                return by_id.get(lvl_id, LEVELS[0])
        # fallback
        return LEVELS[-1]
    except Exception:
        return LEVELS[0]

SAMPLE_UTTER_TEMPLATES = [
    "{persona} 톤으로 [{topic}] 관련해서 이런 느낌으로 물어볼래요: {utter}",
]

SEED_UTTERS = {
    "수열": [
        "등차수열이랑 등비수열 구분할 때, 초항/공차만 보면 되는 거 맞죠?",
        "수열 a_n이 2n+1이면, n이 커질수록 대충 어떻게 변하는지 감이 안 와요.",
        "수열 그래프 그려보면 더 빠르게 이해할 수 있는 포인트가 뭐예요?",
    ],
    "점화식": [
        "a_{n+1} = 2a_n + 1 이런 거 풀 때, 일반항 바로 찾는 팁 있나요?",
        "피보나치 점화식이랑 비슷한 문제 만들 수 있어요? 난이도 중간으로!",
        "점화식에서 초기값이 왜 그렇게 중요한지 예시로 설명해주세요.",
    ],
    "귀납법": [
        "수학적 귀납법으로 n^2 - n이 항상 짝수라는 걸 쉽게 보여줄 수 있나요?",
        "귀납 가정에서 자꾸 막히는데, 다음 단계로 넘어가는 연결 고리가 헷갈려요.",
        "귀납법으로 증명하면 직관이 더 생기나요, 아니면 그냥 형식적인가요?",
    ],
}


MISTAKE_MAP = [
    ("등차수열", "등비수열"),
    ("등비수열", "등차수열"),
    ("점화식", "정화식"),
    ("귀납법", "귀남법"),
    ("일반항", "일방항"),
    ("귀납 가정", "귀납 과정"),
    ("공차", "공치"),
    ("공비", "공피"),
]


def _fast_json_loads(line: str) -> Any:
    if jsonlib is not None:
        try:
            return jsonlib.loads(line)
        except Exception:
            return None
    try:
        return json.loads(line)
    except Exception:
        return None


def load_questions_from_dataset(path: str, max_items: int = 2000) -> List[str]:
    questions: List[str] = []
    if not path or not os.path.exists(path):
        return questions
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= max_items:
                    break
                obj = _fast_json_loads(line)
                if not isinstance(obj, dict):
                    continue
                for key in ("question", "query", "utterance", "student_question", "content", "text"):
                    val = obj.get(key)
                    if isinstance(val, str) and 5 <= len(val) <= 500:
                        questions.append(val.strip())
                        break
    except Exception:
        pass
    return questions


def inject_mistake(text: str, probability: float) -> Tuple[str, Dict[str, Any]]:
    """텍스트에 경미한 말실수를 0~1회 주입하고 메타데이터를 함께 반환"""
    meta: Dict[str, Any] = {"applied": False}
    try:
        if random.random() >= probability:
            return text, meta
        candidates = [pair for pair in MISTAKE_MAP if pair[0] in text]
        pair = random.choice(candidates) if candidates else random.choice(MISTAKE_MAP)
        new_text = text.replace(pair[0], pair[1], 1)
        meta = {"applied": True, "from": pair[0], "to": pair[1]}
        return new_text, meta
    except Exception:
        return text, meta


def llm_paraphrase(base: str, persona: Dict[str, Any], topic: str, allow_mistakes: bool, style_intensity: float, level: Dict[str, Any]) -> str:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return base
    try:
        client = OpenAI()
        sys_prompt = (
            "너는 한국의 10대 학생처럼 말하는 스타일러야. 주어진 문장을 더 자연스럽고 실제 학생 같게 1~2문장으로 바꿔. "
            "문장은 웹 UI에 곧바로 노출될 수 있으니 간결하고 말투 중심으로. 과장된 이모지/은어는 금지."
        )
        user_prompt = (
            f"페르소나: {persona['name']} ({persona['style']})\n"
            f"주제: {topic} (수열/점화식/귀납법 범위)\n"
            f"문장: {base}\n"
            f"스타일 강도: {style_intensity:.1f}\n"
            f"수준: {level['name']} ({level['style']})\n"
            f"수준 지침: {level['prompt']}\n"
            f"말실수 허용: {'약간' if allow_mistakes else '불가'}\n"
            "요구사항:\n"
            "- 학생 말투로 자연스럽게 재작성 (1~2문장).\n"
            "- 수학 용어/표현은 대체로 유지하되, 허용 시 아주 가벼운 실수(용어 살짝 헷갈림/오타) 0~1회만.\n"
            "- 따옴표/머리말/불필요한 설명 없이 결과 문장만 출력."
        )
        resp = client.chat.completions.create(
            model=os.getenv("STUDENT_AGENT_MODEL", "gpt-4o-mini"),
            max_completion_tokens=120,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        out = (resp.choices[0].message.content or base).strip()
        return out
    except Exception:
        return base

def adjust_by_level(base: str, level_id: str, topic: str) -> str:
    try:
        if level_id == "naive":
            return f"{base} 이거 기초부터 쉽게 설명해줄 수 있어요?"
        if level_id == "basic":
            return f"{base} 간단한 예시로 바로 이해할 수 있게 알려주세요."
        if level_id == "intermediate":
            return f"{base} 원리나 일반항 아이디어도 함께 설명 가능할까요?"
        if level_id == "advanced":
            return f"{base} 조건/예외나 반례 가능성까지 짚어주실 수 있나요?"
        if level_id == "olympiad":
            return f"{base} 증명 관점에서 핵심 조건과 경계 경우까지 간결히 부탁드려요."
        return base
    except Exception:
        return base


async def publish(client: redis.Redis, channel: str, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False)
    await client.publish(channel, data)


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _update_summary(path: str, persona_id: str, topic: str, mistake_meta: Dict[str, Any]) -> None:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        else:
            summary = {"total": 0, "by_persona": {}, "by_topic": {}, "mistakes": {"applied": 0, "by_pair": {}}}
        summary["total"] = int(summary.get("total", 0)) + 1
        byp = summary.setdefault("by_persona", {})
        byp[persona_id] = int(byp.get(persona_id, 0)) + 1
        byt = summary.setdefault("by_topic", {})
        byt[topic] = int(byt.get(topic, 0)) + 1
        if mistake_meta.get("applied"):
            mist = summary.setdefault("mistakes", {"applied": 0, "by_pair": {}})
            mist["applied"] = int(mist.get("applied", 0)) + 1
            pair_key = f"{mistake_meta.get('from','')}->{mistake_meta.get('to','')}"
            mist.setdefault("by_pair", {})
            mist["by_pair"][pair_key] = int(mist["by_pair"].get(pair_key, 0)) + 1
        summary["updated_at"] = datetime.utcnow().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


async def run_student_agent():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    personas_env = os.getenv("PERSONAS", "all")
    num_samples = int(os.getenv("NUM_SAMPLES", "5"))
    output_dir = os.getenv("OUTPUT_DIR", "/app/output")
    dataset_path = os.getenv("DATASET_PATH", "")
    paraphrase_with_llm = os.getenv("PARAPHRASE_WITH_LLM", "0") == "1"
    mistake_prob = float(os.getenv("MISTAKE_PROB", "0.3"))
    style_intensity = float(os.getenv("STYLE_INTENSITY", "0.7"))
    clarify_loop = os.getenv("CLARIFY_LOOP", "1") == "1"
    clarify_mode = os.getenv("CLARIFY_MODE", "augment")  # augment | rewrite
    clarify_max_rounds = int(os.getenv("CLARIFY_MAX_ROUNDS", "1"))
    level_weights = _parse_level_weights(os.getenv("LEVEL_WEIGHTS", ""))

    logger.info(f"🚀 Tester 시작 - Redis: {redis_url}, 샘플 수: {num_samples}, 페르소나: {personas_env}")
    logger.info(f"📊 설정 - 말실수 확률: {mistake_prob}, 스타일 강도: {style_intensity}, 명료화 루프: {clarify_loop}")

    client = redis.from_url(redis_url)
    await client.ping()
    logger.info("✅ Redis 연결 성공")

    if personas_env == "all":
        personas = PERSONAS
    else:
        ids = [p.strip() for p in personas_env.split(",") if p.strip()]
        personas = [p for p in PERSONAS if p["id"] in ids] or PERSONAS

    logger.info(f"👥 사용 페르소나: {len(personas)}개 - {[p['name'] for p in personas[:3]]}{'...' if len(personas) > 3 else ''}")
    logger.info(f"📚 레벨 가중치: {level_weights}")

    dataset_questions = load_questions_from_dataset(dataset_path, max_items=5000)
    logger.info(f"📖 데이터셋 질문: {len(dataset_questions)}개 로드됨")

    os.makedirs(output_dir, exist_ok=True)
    run_ts = int(datetime.utcnow().timestamp())
    dialogue_id = f"d{run_ts}"
    dialogue_path = os.path.join(output_dir, f"student_dialog_{run_ts}.jsonl")
    conv_path = os.path.join(output_dir, "conversations", f"{dialogue_id}.jsonl")
    summary_path = os.path.join(output_dir, "summary.json")

    async with client.pubsub() as sub:
        await sub.subscribe(ANSWER_COMPLETED)

        async def wait_answer(request_id: str, timeout: float = 120.0) -> Dict[str, Any]:
            """answer.completed 전역 채널과 per-request 채널을 동시에 청취하여 유실을 줄임"""
            start = datetime.utcnow()
            last_payload: Dict[str, Any] = {}
            per_request_channel = f"{ANSWER_COMPLETED}:{request_id}"
            # per-request 채널 추가 구독 (이미 구독되어 있어도 안전)
            try:
                await sub.subscribe(per_request_channel)
            except Exception:
                pass
            try:
                while (datetime.utcnow() - start).total_seconds() < timeout:
                    msg = await sub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if not msg or msg.get("type") != "message":
                        await asyncio.sleep(0.1)
                        continue
                    try:
                        data = msg.get("data")
                        payload = json.loads(data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data)
                    except Exception:
                        continue
                    # per-request 채널 또는 페이로드의 request_id 매칭
                    ch = msg.get("channel")
                    ch = ch.decode("utf-8") if isinstance(ch, (bytes, bytearray)) else ch
                    if ch == per_request_channel or payload.get("request_id") == request_id:
                        meta = (payload.get("metadata") or {})
                        if meta.get("type") == "answer":
                            return payload
                        last_payload = payload
                return last_payload
            finally:
                try:
                    await sub.unsubscribe(per_request_channel)
                except Exception:
                    pass

        def refine_question(original: str, clarification_text: str) -> str:
            """clarification을 반영해 질문을 보강/재작성"""
            if clarify_mode == "rewrite" and OpenAI and os.getenv("OPENAI_API_KEY"):
                try:
                    client = OpenAI()
                    sys = "학생 질문을 더 명확하게 한 문장으로 재작성. 질문을 반복 설명하지 말고, 필요한 정보(조건/목표/출력형식)를 포함."
                    user = (
                        f"원문: {original}\n명료화 피드백: {clarification_text}\n"
                        "한 문장으로 재작성. 불필요한 인사/머리말 금지."
                    )
                    resp = client.chat.completions.create(
                        model=os.getenv("STUDENT_AGENT_MODEL", "gpt-5-mini"),
                        max_completion_tokens=120,
                        messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
                    )
                    out = (resp.choices[0].message.content or original).strip()
                    return out
                except Exception:
                    pass
            # 기본 보강(augment): 조건/요구사항을 덧붙여 한 문장 강화
            safe_text = (clarification_text or "").strip()
            first_line = safe_text.splitlines()[0] if safe_text.splitlines() else ""
            clipped = first_line[:160]
            if clipped:
                return f"{original} (추가 조건: {clipped})"
            return original

        samples = 0
        logger.info(f"🔄 테스트 시작 - 총 {num_samples}개 샘플")
        with open(dialogue_path, "a", encoding="utf-8") as f:
            while samples < num_samples:
                persona = random.choice(personas)
                level = _sample_level(level_weights)
                if dataset_questions:
                    base_q = random.choice(dataset_questions)
                    topic = next((t for t in TOPICS if t in base_q), random.choice(TOPICS))
                    utter = base_q
                else:
                    topic = random.choice(TOPICS)
                    utter = random.choice(SEED_UTTERS[topic])

                logger.info(f"📝 샘플 {samples + 1}/{num_samples} - 페르소나: {persona['name']}, 레벨: {level['name']}, 주제: {topic}")
                logger.info(f"💬 원본 질문: {utter[:100]}{'...' if len(utter) > 100 else ''}")

                # 페르소나 스타일로 자연스럽게 재작성 + 말실수 주입
                transformed = utter
                if paraphrase_with_llm:
                    logger.info("🤖 LLM을 사용한 질문 변환 시작")
                    transformed = llm_paraphrase(utter, persona, topic, allow_mistakes=True, style_intensity=style_intensity, level=level)
                    logger.info(f"🤖 LLM 변환 결과: {transformed[:100]}{'...' if len(transformed) > 100 else ''}")
                else:
                    logger.info("📝 기본 레벨 조정 사용")
                    transformed = adjust_by_level(utter, level.get("id", "basic"), topic)
                    logger.info(f"📝 레벨 조정 결과: {transformed[:100]}{'...' if len(transformed) > 100 else ''}")
                
                transformed, mistake_meta = inject_mistake(transformed, mistake_prob)
                if mistake_meta.get("applied"):
                    logger.info(f"🔧 말실수 주입: '{mistake_meta.get('from')}' → '{mistake_meta.get('to')}'")

                question_text = transformed
                request_id = f"stu_{int(datetime.utcnow().timestamp()*1000)}_{samples}"
                logger.info(f"🆔 요청 ID 생성: {request_id}")

                record = {
                    "ts": datetime.utcnow().isoformat(),
                    "role": "student",
                    "dialogue_id": dialogue_id,
                    "persona": persona["id"],
                    "level": level["id"],
                    "topic": topic,
                    "request_id": request_id,
                    "utterance": question_text,
                    "paraphrased": paraphrase_with_llm,
                    "style_intensity": style_intensity,
                    "mistake": mistake_meta,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()

                # 추가 로그: 대화별/페르소나별 파일에도 기록
                _append_jsonl(conv_path, record)
                _append_jsonl(os.path.join(output_dir, "persona", persona["id"], "dialogue.jsonl"), record)
                _update_summary(summary_path, persona["id"], topic, mistake_meta)

                logger.info(f"📤 Redis로 질문 전송: {QUESTION_SUBMITTED}")
                logger.info(f"📋 전송 내용: {question_text[:100]}{'...' if len(question_text) > 100 else ''}")
                
                await publish(client, QUESTION_SUBMITTED, {
                    "request_id": request_id,
                    "question": question_text,
                    "context": {
                        "topic": topic,
                        "ui_hint": "웹 인터페이스 출력용 문장 중심",
                    },
                })
                logger.info("✅ 질문 전송 완료")

                # clarify → refine → resend 루프
                rounds = 0
                current_req = request_id
                logger.info(f"⏳ 응답 대기 시작: {current_req}")
                response = await wait_answer(current_req)
                logger.info(f"📨 응답 수신: {response.get('metadata', {}).get('type', 'unknown') if isinstance(response, dict) else 'unknown'}")
                
                while clarify_loop and rounds < clarify_max_rounds and (response.get("metadata") or {}).get("type") == "clarification":
                    clar_text = response.get("answer", "")
                    logger.info(f"🔍 명료화 요청 수신 (라운드 {rounds + 1}): {clar_text[:100]}{'...' if len(clar_text) > 100 else ''}")
                    
                    refined = refine_question(question_text, clar_text)
                    logger.info(f"✏️ 질문 개선: {refined[:100]}{'...' if len(refined) > 100 else ''}")
                    
                    # 로그 기록(clarification 수신)
                    clar_rec = {
                        "ts": datetime.utcnow().isoformat(),
                        "role": "agent",
                        "dialogue_id": dialogue_id,
                        "request_id": current_req,
                        "response": response,
                        "clarification": True,
                    }
                    f.write(json.dumps(clar_rec, ensure_ascii=False) + "\n")
                    f.flush()
                    _append_jsonl(conv_path, clar_rec)
                    _append_jsonl(os.path.join(output_dir, "persona", persona["id"], "dialogue.jsonl"), clar_rec)

                    # 재전송
                    rounds += 1
                    question_text = refined
                    current_req = f"{request_id}_r{rounds}"
                    logger.info(f"🔄 명료화 후 재전송 (라운드 {rounds}): {current_req}")
                    
                    resend_rec = {
                        "ts": datetime.utcnow().isoformat(),
                        "role": "student",
                        "dialogue_id": dialogue_id,
                        "persona": persona["id"],
                        "level": level["id"],
                        "topic": topic,
                        "request_id": current_req,
                        "utterance": question_text,
                        "refined_from": request_id,
                        "clarify_round": rounds,
                    }
                    f.write(json.dumps(resend_rec, ensure_ascii=False) + "\n")
                    f.flush()
                    _append_jsonl(conv_path, resend_rec)
                    _append_jsonl(os.path.join(output_dir, "persona", persona["id"], "dialogue.jsonl"), resend_rec)

                    logger.info(f"📤 개선된 질문 재전송: {current_req}")
                    await publish(client, QUESTION_SUBMITTED, {
                        "request_id": current_req,
                        "question": question_text,
                        "context": {
                            "topic": topic,
                            "ui_hint": "웹 인터페이스 출력용 문장 중심",
                        },
                    })
                    logger.info("✅ 개선된 질문 전송 완료")
                    
                    response = await wait_answer(current_req)
                    logger.info(f"📨 개선된 질문 응답 수신: {response.get('metadata', {}).get('type', 'unknown') if isinstance(response, dict) else 'unknown'}")
                # 명료화 루프 종료 후에도 최종 답변이 없으면(또는 루프를 사용하지 않으면),
                # 테스트 편의상 한 번 강제로 답변을 요청해 기록을 남길 수 있다.
                force_answer = os.getenv("TEST_FORCE_ANSWER_ON_TIMEOUT", "1") == "1"
                meta_type = (response.get("metadata") or {}).get("type") if isinstance(response, dict) else None
                if force_answer and meta_type != "answer":
                    await publish(client, ANSWER_REQUESTED, {
                        "request_id": current_req,
                        "question": question_text,
                        "context": {"topic": topic, "ui_hint": "테스트 강제 답변 요청"},
                        "metadata": {"from": "tester", "reason": "force_answer"}
                    })
                    response = await wait_answer(current_req)

                resp_rec = {
                    "ts": datetime.utcnow().isoformat(),
                    "role": "agent",
                    "dialogue_id": dialogue_id,
                    "request_id": current_req,
                    "response": response,
                }
                f.write(json.dumps(resp_rec, ensure_ascii=False) + "\n")
                f.flush()
                _append_jsonl(conv_path, resp_rec)
                _append_jsonl(os.path.join(output_dir, "persona", persona["id"], "dialogue.jsonl"), resp_rec)

                samples += 1
                logger.info(f"✅ 샘플 {samples}/{num_samples} 완료 - {persona['name']} ({topic})")
                logger.info(f"📊 진행률: {(samples/num_samples)*100:.1f}%")

    await client.close()
    logger.info("🎉 모든 테스트 완료!")
    logger.info(f"📁 결과 저장 위치: {output_dir}")

if __name__ == "__main__":
    asyncio.run(run_student_agent())
