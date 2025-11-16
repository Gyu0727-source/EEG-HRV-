"""
ARC 파일 파싱 결과와 BrainBay TXT 변환 결과 비교 검증

목표: ARC 직접 파싱으로 TXT와 동일한 결과를 얻을 수 있는지 확인
"""

import pandas as pd
import numpy as np
from arc_reader import ARCReader
import os


def compare_arc_and_txt(arc_path, txt_path):
    """
    ARC 파싱 결과와 TXT 파일 비교

    Parameters:
    -----------
    arc_path : str
        ARC 파일 경로
    txt_path : str
        BrainBay TXT 파일 경로
    """
    print("=" * 80)
    print("ARC 파싱 vs BrainBay TXT 비교 검증")
    print("=" * 80)

    # 1. ARC 파일 파싱
    print("\n[1단계] ARC 파일 파싱...")
    arc_reader = ARCReader(arc_path)
    arc_df = arc_reader.read()

    print(f"\nARC 파싱 결과:")
    print(f"  - 행 개수: {len(arc_df):,}")
    print(f"  - 컬럼: {arc_df.columns.tolist()}")
    print(f"\n첫 10행:")
    print(arc_df.head(10))

    # 2. TXT 파일 읽기 (헤더 없음)
    print("\n[2단계] BrainBay TXT 파일 읽기...")
    txt_df = pd.read_csv(txt_path, header=None)

    print(f"\nTXT 파일 내용:")
    print(f"  - 행 개수: {len(txt_df):,}")
    print(f"  - 컬럼 개수: {len(txt_df.columns)}")
    print(f"\n첫 10행:")
    print(txt_df.head(10))

    # 3. 통계 비교
    print("\n[3단계] 통계 비교")
    print("=" * 80)

    # ARC의 첫 3개 채널 (Channel 0, 1, 2 = Fp1, Fp2, PPG 추정)
    arc_ch0 = arc_df['EEG Channel 0'].values
    arc_ch1 = arc_df['EEG Channel 1'].values
    arc_ch2 = arc_df['EEG Channel 2'].values

    # TXT의 첫 3개 컬럼
    txt_col0 = txt_df.iloc[:, 0].values
    txt_col1 = txt_df.iloc[:, 1].values
    txt_col2 = txt_df.iloc[:, 2].values

    print("\n채널 0 (Fp1 추정) 비교:")
    print(f"  ARC: 평균={np.mean(arc_ch0):.2f}, 표준편차={np.std(arc_ch0):.2f}, 범위=[{np.min(arc_ch0):.2f}, {np.max(arc_ch0):.2f}]")
    print(f"  TXT: 평균={np.mean(txt_col0):.2f}, 표준편차={np.std(txt_col0):.2f}, 범위=[{np.min(txt_col0):.2f}, {np.max(txt_col0):.2f}]")

    print("\n채널 1 (Fp2 추정) 비교:")
    print(f"  ARC: 평균={np.mean(arc_ch1):.2f}, 표준편차={np.std(arc_ch1):.2f}, 범위=[{np.min(arc_ch1):.2f}, {np.max(arc_ch1):.2f}]")
    print(f"  TXT: 평균={np.mean(txt_col1):.2f}, 표준편차={np.std(txt_col1):.2f}, 범위=[{np.min(txt_col1):.2f}, {np.max(txt_col1):.2f}]")

    print("\n채널 2 (PPG 추정) 비교:")
    print(f"  ARC: 평균={np.mean(arc_ch2):.2f}, 표준편차={np.std(arc_ch2):.2f}, 범위=[{np.min(arc_ch2):.2f}, {np.max(arc_ch2):.2f}]")
    print(f"  TXT: 평균={np.mean(txt_col2):.2f}, 표준편차={np.std(txt_col2):.2f}, 범위=[{np.min(txt_col2):.2f}, {np.max(txt_col2):.2f}]")

    # 4. 행 개수 차이
    print("\n[4단계] 행 개수 차이 분석")
    print("=" * 80)
    row_diff = len(arc_df) - len(txt_df)
    row_diff_pct = (row_diff / len(arc_df)) * 100 if len(arc_df) > 0 else 0

    print(f"  ARC 행 개수: {len(arc_df):,}")
    print(f"  TXT 행 개수: {len(txt_df):,}")
    print(f"  차이: {row_diff:,}행 ({row_diff_pct:.1f}%)")

    # 5. 값 범위 차이
    print("\n[5단계] 값 범위 차이 분석")
    print("=" * 80)

    arc_range = np.max(arc_ch0) - np.min(arc_ch0)
    txt_range = np.max(txt_col0) - np.min(txt_col0)
    range_ratio = arc_range / txt_range if txt_range > 0 else 0

    print(f"  ARC 값 범위: {arc_range:.2f}")
    print(f"  TXT 값 범위: {txt_range:.2f}")
    print(f"  비율: {range_ratio:.1f}배")

    # 6. 샘플링 테스트
    print("\n[6단계] 패턴 일치도 테스트")
    print("=" * 80)

    # TXT 길이에 맞춰 ARC 다운샘플링
    if len(arc_df) > len(txt_df):
        sample_indices = np.linspace(0, len(arc_df)-1, len(txt_df), dtype=int)
        arc_sampled = arc_ch0[sample_indices]

        # 상관계수 계산
        correlation = np.corrcoef(arc_sampled, txt_col0)[0, 1]
        print(f"  다운샘플링 후 상관계수: {correlation:.4f}")

        if correlation > 0.9:
            print("  → 패턴이 매우 유사합니다! (스케일만 다를 수 있음)")
        elif correlation > 0.7:
            print("  → 패턴이 유사합니다 (일부 처리 차이 존재)")
        else:
            print("  → 패턴이 다릅니다 (추가 변환 필요)")

    # 7. 스케일 팩터 추정
    print("\n[7단계] 스케일 팩터 추정")
    print("=" * 80)

    # 중앙값 기준으로 스케일 추정
    arc_median = np.median(arc_ch0)
    txt_median = np.median(txt_col0)

    if txt_median != 0:
        estimated_scale = arc_median / txt_median
        print(f"  ARC 중앙값: {arc_median:.2f}")
        print(f"  TXT 중앙값: {txt_median:.2f}")
        print(f"  추정 스케일 팩터: {estimated_scale:.4f}")

        # 스케일 적용 테스트
        arc_scaled = arc_ch0 / estimated_scale
        scaled_median = np.median(arc_scaled)
        print(f"\n  스케일 적용 후 ARC 중앙값: {scaled_median:.2f}")
        print(f"  목표 TXT 중앙값: {txt_median:.2f}")
        print(f"  차이: {abs(scaled_median - txt_median):.2f}")

    # 8. 결론
    print("\n[8단계] 결론")
    print("=" * 80)

    if row_diff_pct > 10:
        print("[X] 행 개수 차이가 10% 이상입니다.")
        print("   -> BrainBay가 다운샘플링 또는 필터링을 적용한 것으로 보입니다.")

    if range_ratio > 10:
        print("[X] 값 범위가 10배 이상 차이 납니다.")
        print("   -> 스케일 팩터가 잘못되었거나 추가 변환이 필요합니다.")

    print("\n권장 사항:")
    if row_diff_pct > 5 or range_ratio > 5:
        print("  1. BrainBay TXT 변환 사용 권장 (검증된 방법)")
        print("  2. ARC 직접 파싱은 추가 연구 필요")
        print("  3. txt_to_excel_converter.py 사용")
    else:
        print("  [OK] ARC 직접 파싱 가능!")
        print("  -> arc_reader.py 보완 후 바로 사용 가능")

    return {
        'arc_rows': len(arc_df),
        'txt_rows': len(txt_df),
        'row_diff_pct': row_diff_pct,
        'range_ratio': range_ratio
    }


if __name__ == "__main__":
    # 테스트 파일 경로
    base_path = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일"

    arc_file = os.path.join(base_path, "07.이찬희 호흡.arc")
    txt_file = os.path.join(base_path, "07.이찬희 호흡.txt")

    results = compare_arc_and_txt(arc_file, txt_file)

    print("\n" + "=" * 80)
    print("검증 완료!")
    print("=" * 80)
