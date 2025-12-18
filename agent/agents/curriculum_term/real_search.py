#!/usr/bin/env python3
"""
실제 DB(unified_corpus.db)를 사용하는 커리큘럼/교과서 검색 실행기
원문(content)을 그대로 출력합니다. (가짜 목데이터 사용 안 함)

사용법 예시:
  python real_search.py --query "미분" --k 5
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict


def ensure_project_root_on_syspath():
    # 프로젝트 루트 추가해서 상대 import 문제 방지
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(this_dir, "..", "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


async def run_search(query: str, k: int) -> Dict[str, Any]:
    from agent.agents.curriculum_term.tools.curriculum_term_tool import CurriculumTermTool

    tool = CurriculumTermTool()
    result = await tool.search(query, k)
    return result


def print_full_result(result: Dict[str, Any]) -> None:
    if "error" in result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    def print_items(title: str, items_key: str) -> None:
        print(f"\n=== {title} (총 {len(result.get(items_key, []))}건) ===")
        for idx, item in enumerate(result.get(items_key, []), start=1):
            print(f"\n[{idx}] id={item.get('id')} | type={item.get('chunk_type')} | title={item.get('title')}")
            print("- 메타:")
            meta_keys = [
                "grade_level",
                "subject",
                "topic",
                "achievement_code",
                "unit_number",
                "subunit_number",
            ]
            for key in meta_keys:
                if key in item and item.get(key) is not None:
                    print(f"  {key}: {item.get(key)}")
            print("- 키워드:")
            print(json.dumps(item.get("keywords", []), ensure_ascii=False))
            matched = item.get("matched_sentences")
            if matched:
                print("- 매칭 문장:")
                for s in matched:
                    print(f"  • {s}")
            print("- 원문:")
            # 원문 그대로 출력 (절대 자르지 않음)
            print(item.get("content", ""))

    print(f"Query: {result.get('query')}")
    print_items("교과과정 결과", "curriculum_results")
    print_items("교과서 결과", "textbook_results")
    print(f"\n총합: {result.get('total', 0)}건")


def main():
    ensure_project_root_on_syspath()

    parser = argparse.ArgumentParser(description="실제 DB로 커리큘럼/교과서 검색")
    parser.add_argument("--query", required=False, default="미분", help="검색어")
    parser.add_argument("--k", type=int, required=False, default=5, help="최대 결과 수")
    args = parser.parse_args()

    result = asyncio.run(run_search(args.query, args.k))
    print_full_result(result)


if __name__ == "__main__":
    main()


