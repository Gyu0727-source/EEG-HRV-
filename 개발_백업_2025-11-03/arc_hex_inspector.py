"""
ARC 파일의 실제 바이너리 구조 확인
"""

import struct


def inspect_arc_file(arc_path, num_blocks=20):
    """ARC 파일의 처음 몇 블록을 hex dump"""

    with open(arc_path, 'rb') as f:
        # 헤더 건너뛰기
        f.seek(256)

        print("=" * 80)
        print("ARC 파일 바이너리 구조 분석")
        print("=" * 80)

        for block_idx in range(num_blocks):
            # 32바이트 블록 읽기
            block = f.read(32)

            if len(block) < 32:
                break

            print(f"\n블록 #{block_idx}:")
            print(f"  Hex: {block.hex()}")

            # 8개 채널 파싱 시도 (big-endian)
            print("  Big-endian 해석:")
            for ch in range(8):
                offset = ch * 2
                value = struct.unpack('>h', block[offset:offset+2])[0]
                print(f"    Channel {ch}: {value:6d} (0x{block[offset:offset+2].hex()})")

            # Little-endian 시도
            print("  Little-endian 해석:")
            for ch in range(8):
                offset = ch * 2
                value = struct.unpack('<h', block[offset:offset+2])[0]
                print(f"    Channel {ch}: {value:6d} (0x{block[offset:offset+2].hex()})")


if __name__ == "__main__":
    arc_file = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 호흡.arc"

    inspect_arc_file(arc_file, num_blocks=10)
