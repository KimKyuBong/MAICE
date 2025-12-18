#!/usr/bin/env python3
"""
MAICE 아이콘 생성 스크립트
SVG 파일을 기반으로 다양한 크기의 PNG 아이콘을 생성합니다.

필요한 패키지:
- pip install cairosvg pillow
"""

import sys
import os

def generate_icons():
    try:
        import cairosvg
        from PIL import Image
    except ImportError:
        print("필요한 패키지를 설치하세요:")
        print("pip install cairosvg pillow")
        sys.exit(1)
    
    # 아이콘 크기 정의
    sizes = [
        (192, "icon-192.png"),
        (512, "icon-512.png"),
    ]
    
    # 입력 파일 확인
    svg_file = "front/static/favicon.svg"
    if not os.path.exists(svg_file):
        print(f"SVG 파일을 찾을 수 없습니다: {svg_file}")
        sys.exit(1)
    
    # 각 크기의 PNG 생성
    for size, filename in sizes:
        output_path = f"front/static/{filename}"
        
        print(f"{size}x{size} 아이콘 생성 중: {filename}...")
        
        # SVG를 PNG로 변환
        png_bytes = cairosvg.svg2png(
            url=svg_file,
            output_width=size,
            output_height=size
        )
        
        # PNG 저장
        with open(output_path, 'wb') as f:
            f.write(png_bytes)
        
        print(f"✅ 생성 완료: {output_path}")
    
    print("\n✨ 모든 아이콘 생성 완료!")
    print("이제 빌드하면 MAICE 아이콘이 표시됩니다.")

if __name__ == "__main__":
    generate_icons()

