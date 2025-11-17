"""
HRV 정확도 비교 스크립트

PPG 데이터로 HRV를 계산하고 정답지와 비교하여 정확도를 측정합니다.
"""

import pandas as pd
import numpy as np
import heartpy as hp
import os
import re
from scipy import stats

class HRVAccuracyComparer:
    def __init__(self, raw_data_dir, ground_truth_path):
        self.raw_data_dir = raw_data_dir
        self.ground_truth_path = ground_truth_path
        self.sample_rate = 250  # Hz

        # 정답지 로드
        self.df_gt = pd.read_excel(ground_truth_path, sheet_name='Data')

        # 매칭 가능한 이름들
        self.matched_names = ['방지수', '변미정', '이찬희', '한진우']

    def analyze_ppg_hrv(self, file_path):
        """PPG 데이터로 HRV 분석"""
        try:
            # 엑셀 읽기 (헤더 없음)
            df = pd.read_excel(file_path, header=None)
            ppg_signal = df[2].values  # 세 번째 열 = PPG

            # 노이즈 제거
            filtered = hp.filter_signal(ppg_signal, cutoff=0.05,
                                         sample_rate=self.sample_rate,
                                         order=3, filtertype='highpass')

            # HRV 분석
            wd, m = hp.process(filtered, sample_rate=self.sample_rate, calc_freq=True)

            # 주요 지표 추출
            hrv_results = {
                'bpm': m.get('bpm', np.nan),
                'ibi': m.get('ibi', np.nan),
                'sdnn': m.get('sdnn', np.nan),
                'sdsd': m.get('sdsd', np.nan),
                'rmssd': m.get('rmssd', np.nan),
                'pnn20': m.get('pnn20', np.nan),
                'pnn50': m.get('pnn50', np.nan),
                'hr_mad': m.get('hr_mad', np.nan),
                'sd1': m.get('sd1', np.nan),
                'sd2': m.get('sd2', np.nan),
                's': m.get('s', np.nan),
                'sd1/sd2': m.get('sd1/sd2', np.nan),
                'breathingrate': m.get('breathingrate', np.nan),
                'vlf': m.get('vlf', np.nan),
                'lf': m.get('lf', np.nan),
                'hf': m.get('hf', np.nan),
                'lf/hf': m.get('lf/hf', np.nan),
                'lf_nu': m.get('lf_nu', np.nan),
                'hf_nu': m.get('hf_nu', np.nan),
                'p_total': m.get('p_total', np.nan),
                'vlf_perc': m.get('vlf_perc', np.nan),
                'lf_perc': m.get('lf_perc', np.nan),
                'hf_perc': m.get('hf_perc', np.nan)
            }

            return {'status': 'success', 'hrv': hrv_results, 'measures': m, 'working_data': wd}

        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    def get_ground_truth(self, name, task_type='숫자'):
        """정답지에서 해당 이름의 HRV 값 가져오기"""
        # 정답지에서 이름 찾기
        mask = self.df_gt['Name'].astype(str).str.contains(name, case=False, na=False)

        if task_type:
            # 숫자/잔상/호흡 구분
            mask = mask & self.df_gt['Name'].astype(str).str.contains(task_type, case=False, na=False)

        matched = self.df_gt[mask]

        if len(matched) == 0:
            return None

        # 첫 번째 매칭 사용
        row = matched.iloc[0]

        gt_hrv = {
            'bpm': row.get('bpm:', np.nan),
            'ibi': row.get('ibi:', np.nan),
            'sdnn': row.get('sdnn:', np.nan),
            'sdsd': row.get('sdsd:', np.nan),
            'rmssd': row.get('rmssd:', np.nan),
            'pnn20': row.get('pnn20:', np.nan),
            'pnn50': row.get('pnn50:', np.nan),
            'hr_mad': row.get('hr_mad:', np.nan),
            'sd1': row.get('sd1:', np.nan),
            'sd2': row.get('sd2:', np.nan),
            's': row.get('s:', np.nan),
            'sd1/sd2': row.get('sd1/sd2:', np.nan),
            'breathingrate': row.get('breathingrate:', np.nan),
            'vlf': row.get('vlf:', np.nan),
            'lf': row.get('lf:', np.nan),
            'hf': row.get('hf:', np.nan),
            'lf/hf': row.get('lf/hf:', np.nan),
            'lf_nu': row.get('lf_nu:', np.nan),
            'hf_nu': row.get('hf_nu:', np.nan),
            'p_total': row.get('p_total:', np.nan),
            'vlf_perc': row.get('vlf_perc:', np.nan),
            'lf_perc': row.get('lf_perc:', np.nan),
            'hf_perc': row.get('hf_perc:', np.nan)
        }

        return gt_hrv

    def calculate_accuracy(self, computed, ground_truth):
        """정확도 계산 (RMSE, MAE, MAPE, 상관계수)"""
        metrics_to_compare = ['bpm', 'ibi', 'sdnn', 'rmssd', 'pnn50', 'sd1', 'sd2', 'lf', 'hf', 'lf/hf']

        comparisons = {}

        for metric in metrics_to_compare:
            comp_val = computed.get(metric, np.nan)
            gt_val = ground_truth.get(metric, np.nan)

            if not np.isnan(comp_val) and not np.isnan(gt_val) and gt_val != 0:
                error = comp_val - gt_val
                abs_error = abs(error)
                pct_error = abs_error / abs(gt_val) * 100

                comparisons[metric] = {
                    'computed': comp_val,
                    'ground_truth': gt_val,
                    'error': error,
                    'abs_error': abs_error,
                    'pct_error': pct_error
                }

        return comparisons

    def compare_all_samples(self):
        """모든 매칭된 샘플 비교"""
        print("=" * 80)
        print("매칭된 샘플들 HRV 분석 및 정답지 비교")
        print("=" * 80)

        all_results = []

        for name in self.matched_names:
            # raw_data 파일 찾기
            raw_files = [f for f in os.listdir(self.raw_data_dir)
                         if f.startswith(name) and f.endswith('.xlsx')]

            if len(raw_files) == 0:
                print(f"\n✗ {name}: raw_data 파일 없음")
                continue

            file_path = os.path.join(self.raw_data_dir, raw_files[0])

            print(f"\n{'='*80}")
            print(f"[{name}] 분석 중...")
            print(f"{'='*80}")
            print(f"파일: {raw_files[0]}")

            # PPG로 HRV 분석
            result = self.analyze_ppg_hrv(file_path)

            if result['status'] != 'success':
                print(f"✗ HRV 분석 실패: {result['error']}")
                continue

            computed_hrv = result['hrv']

            # 정답지 가져오기 (숫자 태스크 우선)
            ground_truth = self.get_ground_truth(name, '숫자')

            if ground_truth is None:
                # 숫자가 없으면 이름만으로 검색
                ground_truth = self.get_ground_truth(name, None)

            if ground_truth is None:
                print(f"✗ 정답지에서 {name} 데이터를 찾을 수 없습니다.")
                continue

            # 정확도 계산
            comparisons = self.calculate_accuracy(computed_hrv, ground_truth)

            # 결과 출력
            print(f"\n[주요 HRV 지표 비교]")
            print(f"{'지표':<15} {'계산값':>12} {'정답값':>12} {'오차':>12} {'오차율':>10}")
            print("-" * 70)

            for metric, comp in comparisons.items():
                print(f"{metric:<15} {comp['computed']:>12.2f} {comp['ground_truth']:>12.2f} "
                      f"{comp['error']:>12.2f} {comp['pct_error']:>9.1f}%")

            # 전체 결과 저장
            all_results.append({
                'name': name,
                'computed': computed_hrv,
                'ground_truth': ground_truth,
                'comparisons': comparisons
            })

        return all_results

    def generate_statistics(self, all_results):
        """전체 통계 분석"""
        print(f"\n\n" + "=" * 80)
        print("전체 정확도 통계")
        print("=" * 80)

        # 지표별로 모든 오차율 수집
        metrics = ['bpm', 'sdnn', 'rmssd', 'sd1', 'sd2', 'lf', 'hf', 'lf/hf']

        stats_summary = {}

        for metric in metrics:
            errors = []
            pct_errors = []

            for result in all_results:
                if metric in result['comparisons']:
                    comp = result['comparisons'][metric]
                    errors.append(comp['error'])
                    pct_errors.append(comp['pct_error'])

            if len(pct_errors) > 0:
                stats_summary[metric] = {
                    'n': len(pct_errors),
                    'mean_pct_error': np.mean(pct_errors),
                    'std_pct_error': np.std(pct_errors),
                    'min_pct_error': np.min(pct_errors),
                    'max_pct_error': np.max(pct_errors),
                    'median_pct_error': np.median(pct_errors),
                    'rmse': np.sqrt(np.mean(np.array(errors)**2)),
                    'mae': np.mean(np.abs(errors))
                }

        # 결과 출력
        print(f"\n{'지표':<15} {'샘플수':>8} {'평균오차율':>12} {'중앙값':>10} {'범위':>20}")
        print("-" * 80)

        for metric, stat in stats_summary.items():
            print(f"{metric:<15} {stat['n']:>8} {stat['mean_pct_error']:>11.1f}% "
                  f"{stat['median_pct_error']:>9.1f}% "
                  f"{stat['min_pct_error']:>8.1f}%-{stat['max_pct_error']:>8.1f}%")

        return stats_summary


def main():
    """메인 실행 함수"""

    raw_data_dir = './raw_data'
    ground_truth = './참고 개발코드/01.Results_0128.xlsx'

    # 비교기 생성
    comparer = HRVAccuracyComparer(raw_data_dir, ground_truth)

    # 모든 샘플 비교
    results = comparer.compare_all_samples()

    # 통계 분석
    stats = comparer.generate_statistics(results)

    print(f"\n\n" + "=" * 80)
    print("분석 완료!")
    print("=" * 80)
    print(f"\n총 {len(results)}개 샘플 비교 완료")
    print(f"\n평균 정확도:")
    for metric, stat in stats.items():
        if metric in ['bpm', 'sdnn', 'rmssd']:
            print(f"  {metric}: 오차율 {stat['mean_pct_error']:.1f}%")


if __name__ == '__main__':
    main()
