"""
ARC 파일 파싱 정확도 검증 스크립트

ARC 파서로 읽은 결과와 BrainBay에서 변환한 TXT 파일을 비교하여
정확도를 검증합니다.
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from sklearn.metrics import mean_squared_error, mean_absolute_error
import arc_reader_v5_sync as arc_reader


def load_brainbay_txt(txt_path):
    """
    BrainBay에서 생성한 TXT 파일 로드

    Parameters:
    -----------
    txt_path : str
        TXT 파일 경로

    Returns:
    --------
    df : pandas.DataFrame
        채널별 데이터
    """
    try:
        # BrainBay TXT 형식: 쉼표 구분, 여러 채널
        df = pd.read_csv(txt_path, sep=',', header=None)

        # 컬럼명 설정 (OpenBCI 8채널 + 가속도계 등)
        # 첫 8개 컬럼이 EEG 채널
        channel_names = [f'Ch{i+1}' for i in range(df.shape[1])]
        df.columns = channel_names

        # EEG 8채널만 추출
        eeg_columns = [f'Ch{i+1}' for i in range(min(8, df.shape[1]))]
        df = df[eeg_columns]

        return df

    except Exception as e:
        print(f"TXT 파일 로드 실패: {e}")
        return None


def calculate_accuracy_metrics(data1, data2, channel_name=""):
    """
    두 데이터 간의 정확도 지표 계산

    Parameters:
    -----------
    data1, data2 : numpy.ndarray
        비교할 두 데이터
    channel_name : str
        채널 이름

    Returns:
    --------
    metrics : dict
        정확도 지표들
    """
    # 데이터 타입을 float으로 변환
    data1 = np.array(data1, dtype=float)
    data2 = np.array(data2, dtype=float)

    # 길이 맞추기 (짧은 것 기준)
    min_len = min(len(data1), len(data2))
    data1 = data1[:min_len]
    data2 = data2[:min_len]

    # NaN 제거
    mask = ~(np.isnan(data1) | np.isnan(data2))
    data1_clean = data1[mask]
    data2_clean = data2[mask]

    if len(data1_clean) == 0:
        return None

    # 상관계수 (Pearson)
    corr, p_value = pearsonr(data1_clean, data2_clean)

    # RMSE (Root Mean Square Error)
    rmse = np.sqrt(mean_squared_error(data1_clean, data2_clean))

    # MAE (Mean Absolute Error)
    mae = mean_absolute_error(data1_clean, data2_clean)

    # NRMSE (Normalized RMSE) - 범위로 정규화
    data_range = np.max(data2_clean) - np.min(data2_clean)
    nrmse = rmse / data_range if data_range > 0 else 0

    # MAPE (Mean Absolute Percentage Error)
    # 0으로 나누기 방지
    mask_nonzero = data2_clean != 0
    if np.sum(mask_nonzero) > 0:
        mape = np.mean(np.abs((data1_clean[mask_nonzero] - data2_clean[mask_nonzero]) /
                              data2_clean[mask_nonzero])) * 100
    else:
        mape = 0

    # R² (결정계수)
    ss_res = np.sum((data1_clean - data2_clean) ** 2)
    ss_tot = np.sum((data2_clean - np.mean(data2_clean)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    metrics = {
        'channel': channel_name,
        'correlation': corr,
        'p_value': p_value,
        'rmse': rmse,
        'mae': mae,
        'nrmse': nrmse,
        'mape': mape,
        'r2': r2,
        'n_samples': len(data1_clean)
    }

    return metrics


def validate_arc_file(arc_path, txt_path):
    """
    ARC 파일과 BrainBay TXT 파일 비교 검증

    Parameters:
    -----------
    arc_path : str
        ARC 파일 경로
    txt_path : str
        BrainBay TXT 파일 경로

    Returns:
    --------
    results : dict
        검증 결과
    """
    print(f"\n{'='*80}")
    print(f"검증 시작: {os.path.basename(arc_path)}")
    print(f"{'='*80}")

    # 1. ARC 파일 파싱
    print("1. ARC 파일 파싱 중...")
    reader = arc_reader.ARCReaderV5(arc_path)
    arc_data = reader.read()

    if arc_data is None:
        print("❌ ARC 파일 파싱 실패")
        return None

    # EEG 채널만 추출 (Channel 1~8)
    eeg_columns = [f'Channel {i+1}' for i in range(8)]
    arc_data = arc_data[eeg_columns]

    print(f"   ✓ ARC 데이터: {arc_data.shape[0]} 샘플, {arc_data.shape[1]} 채널")

    # 2. BrainBay TXT 파일 로드
    print("2. BrainBay TXT 파일 로드 중...")
    txt_data = load_brainbay_txt(txt_path)

    if txt_data is None:
        print("❌ TXT 파일 로드 실패")
        return None

    print(f"   ✓ TXT 데이터: {txt_data.shape[0]} 샘플, {txt_data.shape[1]} 채널")

    # 3. 채널별 정확도 계산
    print("\n3. 채널별 정확도 계산 중...")

    results = {
        'arc_file': os.path.basename(arc_path),
        'txt_file': os.path.basename(txt_path),
        'arc_samples': arc_data.shape[0],
        'txt_samples': txt_data.shape[0],
        'channels': []
    }

    # 사용 가능한 채널 수 (최소값 기준)
    n_channels = min(arc_data.shape[1], txt_data.shape[1])

    for ch_idx in range(n_channels):
        channel_name = f"Ch{ch_idx + 1}"

        # ARC 데이터
        arc_ch_data = arc_data.iloc[:, ch_idx].values

        # TXT 데이터
        txt_ch_data = txt_data.iloc[:, ch_idx].values

        # 정확도 계산
        metrics = calculate_accuracy_metrics(arc_ch_data, txt_ch_data, channel_name)

        if metrics:
            results['channels'].append(metrics)

            print(f"\n   📊 {channel_name}:")
            print(f"      상관계수: {metrics['correlation']:.6f}")
            print(f"      R²: {metrics['r2']:.6f}")
            print(f"      RMSE: {metrics['rmse']:.2f}")
            print(f"      NRMSE: {metrics['nrmse']:.4f} ({metrics['nrmse']*100:.2f}%)")
            print(f"      MAE: {metrics['mae']:.2f}")
            print(f"      샘플 수: {metrics['n_samples']:,}")

    # 4. 전체 평균 계산
    if results['channels']:
        avg_corr = np.mean([ch['correlation'] for ch in results['channels']])
        avg_r2 = np.mean([ch['r2'] for ch in results['channels']])
        avg_nrmse = np.mean([ch['nrmse'] for ch in results['channels']])

        results['average'] = {
            'correlation': avg_corr,
            'r2': avg_r2,
            'nrmse': avg_nrmse
        }

        print(f"\n{'='*80}")
        print(f"📈 전체 평균 정확도:")
        print(f"{'='*80}")
        print(f"평균 상관계수: {avg_corr:.6f}")
        print(f"평균 R²: {avg_r2:.6f}")
        print(f"평균 NRMSE: {avg_nrmse:.4f} ({avg_nrmse*100:.2f}%)")

        # 정확도 판정
        if avg_corr >= 0.999:
            grade = "🌟 탁월함 (99.9% 이상)"
        elif avg_corr >= 0.99:
            grade = "✅ 매우 우수 (99% 이상)"
        elif avg_corr >= 0.95:
            grade = "✓ 우수 (95% 이상)"
        elif avg_corr >= 0.90:
            grade = "○ 양호 (90% 이상)"
        else:
            grade = "⚠ 개선 필요 (90% 미만)"

        print(f"정확도 등급: {grade}")

    return results


def batch_validate(arc_txt_pairs):
    """
    여러 ARC-TXT 쌍을 일괄 검증

    Parameters:
    -----------
    arc_txt_pairs : list of tuple
        [(arc_path, txt_path), ...]

    Returns:
    --------
    all_results : list of dict
        모든 검증 결과
    """
    all_results = []

    for arc_path, txt_path in arc_txt_pairs:
        if not os.path.exists(arc_path):
            print(f"⚠ ARC 파일 없음: {arc_path}")
            continue

        if not os.path.exists(txt_path):
            print(f"⚠ TXT 파일 없음: {txt_path}")
            continue

        result = validate_arc_file(arc_path, txt_path)

        if result:
            all_results.append(result)

    return all_results


def generate_summary_report(all_results):
    """
    전체 검증 결과 요약 보고서 생성

    Parameters:
    -----------
    all_results : list of dict
        모든 검증 결과
    """
    if not all_results:
        print("\n검증 결과가 없습니다.")
        return

    print(f"\n\n")
    print(f"{'='*80}")
    print(f"🎯 ARC 파일 파싱 정확도 검증 최종 보고서")
    print(f"{'='*80}")

    print(f"\n총 검증 파일 수: {len(all_results)}개")

    # 파일별 요약
    print(f"\n{'='*80}")
    print(f"📋 파일별 정확도 요약")
    print(f"{'='*80}")
    print(f"{'파일명':<30} {'상관계수':>12} {'R²':>10} {'NRMSE':>10}")
    print(f"{'-'*80}")

    for result in all_results:
        if 'average' in result:
            avg = result['average']
            print(f"{result['arc_file']:<30} {avg['correlation']:>12.6f} {avg['r2']:>10.6f} {avg['nrmse']:>10.4f}")

    # 전체 통계
    print(f"\n{'='*80}")
    print(f"📊 전체 통계")
    print(f"{'='*80}")

    all_corrs = [r['average']['correlation'] for r in all_results if 'average' in r]
    all_r2s = [r['average']['r2'] for r in all_results if 'average' in r]
    all_nrmses = [r['average']['nrmse'] for r in all_results if 'average' in r]

    if all_corrs:
        print(f"\n상관계수 (Correlation):")
        print(f"  평균: {np.mean(all_corrs):.6f}")
        print(f"  최소: {np.min(all_corrs):.6f}")
        print(f"  최대: {np.max(all_corrs):.6f}")
        print(f"  표준편차: {np.std(all_corrs):.6f}")

        print(f"\nR² (결정계수):")
        print(f"  평균: {np.mean(all_r2s):.6f}")
        print(f"  최소: {np.min(all_r2s):.6f}")
        print(f"  최대: {np.max(all_r2s):.6f}")

        print(f"\nNRMSE (정규화 RMSE):")
        print(f"  평균: {np.mean(all_nrmses):.4f} ({np.mean(all_nrmses)*100:.2f}%)")
        print(f"  최소: {np.min(all_nrmses):.4f} ({np.min(all_nrmses)*100:.2f}%)")
        print(f"  최대: {np.max(all_nrmses):.4f} ({np.max(all_nrmses)*100:.2f}%)")

        # 최종 판정
        avg_corr = np.mean(all_corrs)
        print(f"\n{'='*80}")
        print(f"🏆 최종 판정")
        print(f"{'='*80}")

        if avg_corr >= 0.9999:
            grade = "🌟🌟🌟 탁월함"
            accuracy_pct = "99.99% 이상"
        elif avg_corr >= 0.999:
            grade = "🌟🌟 매우 우수"
            accuracy_pct = "99.9% 이상"
        elif avg_corr >= 0.99:
            grade = "🌟 우수"
            accuracy_pct = "99% 이상"
        elif avg_corr >= 0.95:
            grade = "✅ 양호"
            accuracy_pct = "95% 이상"
        else:
            grade = "⚠ 개선 필요"
            accuracy_pct = f"{avg_corr*100:.2f}%"

        print(f"평균 정확도: {accuracy_pct}")
        print(f"등급: {grade}")
        print(f"\n✓ ARC 파서는 BrainBay 결과와 평균 {avg_corr:.4%} 일치합니다.")


def main():
    """메인 함수"""

    # 검증할 ARC-TXT 파일 쌍 정의
    base_path = "참고 개발코드/밴드형 및 이어형 디바이스 기기 연결 및 사용방법/ARC파일"

    arc_txt_pairs = [
        (f"{base_path}/01.이선미 호흡.arc", f"{base_path}/01.이선미 호흡.txt"),
        (f"{base_path}/02.방지수 호흡.arc", f"{base_path}/02.방지수 호흡.txt"),
        (f"{base_path}/07.이찬희 호흡.arc", f"{base_path}/07.이찬희 호흡.txt"),
    ]

    # 일괄 검증
    all_results = batch_validate(arc_txt_pairs)

    # 요약 보고서
    generate_summary_report(all_results)

    print(f"\n{'='*80}")
    print("검증 완료!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
