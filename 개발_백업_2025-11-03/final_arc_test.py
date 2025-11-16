"""
최종 ARC 파싱 테스트

결론: ARC 직접 파싱이 가능한지 최종 판단
"""

import struct
import pandas as pd
import numpy as np


def parse_arc_simple(arc_path):
    """가장 간단한 방식: 16-bit little-endian, 연속 읽기"""

    with open(arc_path, 'rb') as f:
        f.seek(256)  # 헤더 건너뛰기
        raw_data = f.read()

    # 32바이트 블록, 처음 16바이트가 8채널 × 2바이트
    block_size = 32
    num_blocks = len(raw_data) // block_size

    data = []
    for i in range(num_blocks):
        block_start = i * block_size
        block = raw_data[block_start:block_start+16]  # 처음 16바이트만

        # 8채널 × 2바이트 (little-endian signed int16)
        row = []
        for ch in range(8):
            value = struct.unpack('<h', block[ch*2:ch*2+2])[0]
            row.append(value)

        data.append(row)

    df = pd.DataFrame(data, columns=[f'Ch{i}' for i in range(8)])

    # 스케일 적용 (BrainBay 공식)
    for col in df.columns:
        df[col] = df[col] / 2.23

    return df


def compare_with_txt(arc_df, txt_path):
    """TXT 파일과 비교"""

    txt_df = pd.read_csv(txt_path, header=None)

    print("=" * 80)
    print("최종 비교 결과")
    print("=" * 80)

    print(f"\n행 개수:")
    print(f"  ARC: {len(arc_df):,}")
    print(f"  TXT: {len(txt_df):,}")
    print(f"  차이: {abs(len(arc_df) - len(txt_df)):,}행 ({abs(len(arc_df) - len(txt_df)) / len(arc_df) * 100:.1f}%)")

    # 각 채널별로 비교
    for ch_idx in range(min(3, len(txt_df.columns))):
        print(f"\n채널 {ch_idx} 비교 (Fp1/Fp2/PPG):")

        arc_data = arc_df[f'Ch{ch_idx}'].values
        txt_data = txt_df.iloc[:, ch_idx].values

        # 길이 맞추기
        min_len = min(len(arc_data), len(txt_data))
        arc_data = arc_data[:min_len]
        txt_data = txt_data[:min_len]

        # 통계
        print(f"  ARC: 평균={np.mean(arc_data):.2f}, 표준편차={np.std(arc_data):.2f}, 범위=[{np.min(arc_data):.2f}, {np.max(arc_data):.2f}]")
        print(f"  TXT: 평균={np.mean(txt_data):.2f}, 표준편차={np.std(txt_data):.2f}, 범위=[{np.min(txt_data):.2f}, {np.max(txt_data):.2f}]")

        # 상관계수
        if len(arc_data) > 100:
            # 다운샘플링 (너무 많으면 느림)
            sample_indices = np.linspace(0, len(arc_data)-1, min(len(arc_data), 10000), dtype=int)
            arc_sampled = arc_data[sample_indices]
            txt_sampled = txt_data[sample_indices]

            corr = np.corrcoef(arc_sampled, txt_sampled)[0, 1]
            print(f"  상관계수: {corr:.4f}")

            if corr > 0.95:
                print(f"  ✓ 매우 높은 일치도!")
            elif corr > 0.8:
                print(f"  ○ 높은 일치도 (일부 차이)")
            elif corr > 0.5:
                print(f"  △ 중간 일치도 (처리 차이)")
            else:
                print(f"  × 낮은 일치도 (구조 다름)")

    # 첫 20개 값 직접 비교
    print(f"\n첫 20개 값 직접 비교 (Ch0 vs Col0):")
    print(f"  ARC: {arc_df['Ch0'].head(20).values}")
    print(f"  TXT: {txt_df.iloc[:20, 0].values}")

    # 최종 판정
    print("\n" + "=" * 80)
    print("최종 결론")
    print("=" * 80)

    # 가장 단순한 테스트: 0이 아닌 값 비율
    ch0_nonzero = (arc_df['Ch0'] != 0).sum() / len(arc_df) * 100
    txt0_nonzero = (txt_df.iloc[:, 0] != 0).sum() / len(txt_df) * 100

    print(f"\n0이 아닌 값 비율:")
    print(f"  ARC Ch0: {ch0_nonzero:.1f}%")
    print(f"  TXT Col0: {txt0_nonzero:.1f}%")

    if ch0_nonzero < 10:
        print("\n❌ ARC Channel 0에 데이터가 거의 없습니다.")
        print("   → 채널 매핑이 잘못되었거나 데이터 구조가 다릅니다.")
        return False
    else:
        print("\n✓ ARC Channel 0에 충분한 데이터가 있습니다.")

        if abs(len(arc_df) - len(txt_df)) / len(arc_df) < 0.05:
            print("✓ 행 개수가 거의 일치합니다 (5% 이내).")

        # 상관계수 체크
        if len(arc_data) > 100:
            if corr > 0.9:
                print("✓ 데이터 패턴이 매우 유사합니다.")
                print("\n→ ARC 직접 파싱 가능! 추가 보정만 필요합니다.")
                return True
            else:
                print("△ 데이터 패턴이 다릅니다.")
                print("\n→ BrainBay TXT 변환 사용 권장.")
                return False


if __name__ == "__main__":
    arc_path = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 호흡.arc"
    txt_path = arc_path.replace('.arc', '.txt')

    print("=" * 80)
    print("ARC 파일 직접 파싱 최종 테스트")
    print("=" * 80)

    print("\n[1단계] ARC 파일 파싱 (단순 방식)...")
    arc_df = parse_arc_simple(arc_path)

    print(f"\n파싱 결과:")
    print(f"  행 개수: {len(arc_df):,}")
    print(f"  컬럼: {arc_df.columns.tolist()}")
    print(f"\n첫 10행:")
    print(arc_df.head(10))

    print(f"\n통계:")
    print(arc_df.describe())

    print("\n[2단계] TXT 파일과 비교...")
    result = compare_with_txt(arc_df, txt_path)

    if result:
        print("\n" + "=" * 80)
        print("SUCCESS: ARC 직접 파싱으로 진행 가능!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("FAIL: BrainBay TXT 변환 사용 필요")
        print("=" * 80)
