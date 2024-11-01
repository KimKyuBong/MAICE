import aiohttp
import asyncio
import json
import os
from typing import Dict, Any, List
from pathlib import Path

class GradingAPITester:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url.rstrip('/')
        self.criteria = self.load_grading_criteria()
        
    def load_grading_criteria(self, path: str = 'grading_criteria.json') -> Dict:
        """채점 기준 로드"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading grading criteria: {e}")
            return {}
        
    async def submit_solution(self, image_path: str, problem_key: str, student_id: str) -> Dict[str, Any]:
        """학생 답안 이미지 제출 및 채점 요청"""
        url = f"{self.base_url}/submissions/"
        
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
            
        async with aiohttp.ClientSession() as session:
            with open(image_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file',
                             f,
                             filename=os.path.basename(image_path),
                             content_type='image/png')
                data.add_field('problem_key', problem_key)
                data.add_field('student_id', student_id)
                
                try:
                    async with session.post(url, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
                except aiohttp.ClientError as e:
                    print(f"Error submitting solution: {e}")
                    return {"error": str(e)}

    async def get_student_results(self, student_id: str) -> Dict[str, Any]:
        """학생의 모든 채점 결과 조회"""
        url = f"{self.base_url}/students/{student_id}"  # 변경된 엔드포인트
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error getting student results: {e}")
                return {"error": str(e)}

    async def register_grading_criteria(self, problem_key: str, criteria: Dict) -> Dict:
        """채점 기준 등록"""
        url = f"{self.base_url}/criteria/"  # 변경된 엔드포인트
        
        payload = {
            "problem_key": problem_key,
            "total_points": criteria["배점"],
            "correct_answer": criteria["정답"],
            "detailed_criteria": [
                {
                    "item": item["항목"],
                    "points": item["배점"],
                    "description": item["설명"]
                }
                for item in criteria["세부기준"]
            ]
        }
        
        print(f"Sending payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 422:
                        error_detail = await response.json()
                        print(f"Validation error: {error_detail}")
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error registering grading criteria: {e}")
                if hasattr(e, 'status'):
                    print(f"Status code: {e.status}")
                return {"error": str(e)}

    async def get_grading_result(self, grading_id: int) -> Dict[str, Any]:
        """특정 채점 결과 조회"""
        url = f"{self.base_url}/gradings/{grading_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error getting grading result: {e}")
                return {"error": str(e)}

    async def update_grading(self, grading_id: int, updates: Dict) -> Dict[str, Any]:
        """채점 결과 업데이트"""
        url = f"{self.base_url}/gradings/{grading_id}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.patch(url, json=updates) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Error updating grading: {e}")
                return {"error": str(e)}

async def process_student(tester: GradingAPITester, student_folder: str):
    """개별 학생의 답안 처리"""
    student_id = os.path.basename(student_folder)
    image_files = [f for f in os.listdir(student_folder) if f.endswith('.png')]
    
    print(f"\n=== 학생 {student_id} 답안 제출 테스트 시작 ===\n")
    
    # 모든 제출을 동시에 처리
    tasks = []
    for image_file in image_files:
        image_path = os.path.join(student_folder, image_file)
        problem_key = f"문항{os.path.splitext(image_file)[0]}"
        
        print(f"\n제출 준비 중: {image_file}")
        print(f"문항: {problem_key}")
        
        task = tester.submit_solution(
            image_path=image_path,
            problem_key=problem_key,
            student_id=student_id
        )
        tasks.append((image_file, task))
    
    # 모든 제출 동시 처리
    results = []
    for image_file, task in tasks:
        try:
            result = await task
            results.append((image_file, result))
        except Exception as e:
            print(f"Error processing {image_file} for student {student_id}: {e}")
            results.append((image_file, {"error": str(e)}))
    
    # 결과 출력
    for image_file, result in results:
        print(f"\n{student_id} - {image_file} 제출 결과:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 잠시 대기 후 전체 결과 조회
    await asyncio.sleep(0)  # 채점 완료를 위한 대기
    print(f"\n=== 학생 {student_id} 전체 채점 결과 조회 ===\n")
    all_results = await tester.get_student_results(student_id)
    print(json.dumps(all_results, indent=2, ensure_ascii=False))
    
    return student_id, all_results

async def main():
    # API 테스터 인스턴스 생성
    tester = GradingAPITester()
    
    # 먼저 채점 기준 등록
    print("채점 기준 등록 시작...")
    await register_all_criteria(tester)
    
    # 채점 기준이 적용될 시간을 주기 위해 잠시 대기
    print("채점 기준 등록 후 3초 대기...")
    await asyncio.sleep(3)
    
    # students 폴더 내의 모든 학생 폴더 검색
    base_path = "image/students"
    student_folders = [os.path.join(base_path, f) for f in os.listdir(base_path) 
                      if os.path.isdir(os.path.join(base_path, f))]
    
    print(f"총 {len(student_folders)}명의 학생 답안 처리 시작")
    
    # 동시 처리할 학생 수 제한 (서버 부하 고려)
    MAX_CONCURRENT = 1
    
    # 세마포어를 사용하여 동시 처리 제한
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def process_with_semaphore(folder):
        async with semaphore:
            return await process_student(tester, folder)
    
    # 모든 학생 처리
    tasks = [process_with_semaphore(folder) for folder in student_folders]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 최종 결과 요약
    print("\n=== 전체 처리 결과 요약 ===\n")
    for student_id, results in all_results:
        if isinstance(results, dict) and "error" not in results:
            total_score = results.get("current_scores", {}).get("total_score", 0)
            max_score = results.get("current_scores", {}).get("max_total_score", 0)
            avg_score = results.get("current_scores", {}).get("average_score", 0)
            print(f"학생 {student_id}: 총점 {total_score}/{max_score} (평균: {avg_score}%)")
        else:
            print(f"학생 {student_id}: 처리 중 오류 발생")
    
    # 결과를 JSON 파일로 저장
    output_file = "grading_results.json"
    results_dict = {student_id: results for student_id, results in all_results}
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        print(f"\n전체 결과가 {output_file}에 저장되었습니다.")
    except Exception as e:
        print(f"결과 저장 중 오류 발생: {e}")

async def register_all_criteria(tester: GradingAPITester):
    """모든 채점 기준을 병렬로 등록"""
    with open('grading_criteria.json', 'r', encoding='utf-8') as f:
        criteria_data = json.load(f)
    
    print("\n=== 채점 기준 일괄 등록 시작 ===\n")
    
    # 모든 채점 기준을 동시에 등록
    tasks = [
        tester.register_grading_criteria(problem_key, criteria)
        for problem_key, criteria in criteria_data.items()
    ]
    
    # 병렬로 모든 등록 처리
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 결과 확인
    for (problem_key, _), result in zip(criteria_data.items(), results):
        if isinstance(result, Exception):
            print(f"❌ {problem_key} 등록 실패: {str(result)}")
        elif "error" in result:
            print(f"❌ {problem_key} 등록 실패: {result['error']}")
        else:
            print(f"✅ {problem_key} 등록 성공")
    
    print("\n=== 채점 기준 등록 완료 ===\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
    finally:
        print("\n테스트 완료")