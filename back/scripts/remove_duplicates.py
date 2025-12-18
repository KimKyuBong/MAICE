import json
from collections import defaultdict

def remove_duplicates(file_path):
    # JSON 파일 읽기
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 질문과 답변을 기준으로 중복 체크
    seen_qa = defaultdict(list)
    responses = data.get('responses', [])
    
    for idx, item in enumerate(responses):
        # 질문과 답변을 키로 사용
        qa_key = (item.get('question', ''), item.get('response', ''))
        seen_qa[qa_key].append(idx)

    # 중복된 항목의 인덱스 찾기 (첫 번째 항목은 유지)
    duplicates = []
    for indices in seen_qa.values():
        if len(indices) > 1:
            # 첫 번째 항목을 제외한 나머지를 중복으로 처리
            duplicates.extend(indices[1:])

    # 중복 개수 출력
    print(f"발견된 중복 항목 수: {len(duplicates)}")

    # 중복을 제외한 새로운 데이터 생성
    unique_responses = [item for idx, item in enumerate(responses) if idx not in duplicates]

    # 결과를 새 파일에 저장
    output_file = file_path.replace('.json', '_unique.json')
    output_data = {'responses': unique_responses}
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"원본 데이터 개수: {len(responses)}")
    print(f"중복 제거 후 데이터 개수: {len(unique_responses)}")
    print(f"중복 제거된 데이터가 {output_file}에 저장되었습니다.")

if __name__ == "__main__":
    file_path = "maice_data_2025-04-02.json"  # 파일 경로
    remove_duplicates(file_path) 