"""
정답지와 현재 알고리즘 결과 비교 검증 스크립트

뇌공학자의 정답지(01.Results_0128.xlsx)와
현재 HRV/EEG 분석 알고리즘 결과를 비교하여 정확도를 검증합니다.
"""

import pandas as pd
import numpy as np
from scipy import stats
import json
import os

class AlgorithmValidator:
    def __init__(self, ground_truth_path, analysis_data_dir):
        """
        Parameters:
        -----------
        ground_truth_path : str
            정답지 엑셀 파일 경로
        analysis_data_dir : str
            현재 알고리즘 분석 결과 디렉토리
        """
        self.ground_truth_path = ground_truth_path
        self.analysis_data_dir = analysis_data_dir

        # 정답지 로드
        self.load_ground_truth()

    def load_ground_truth(self):
        """정답지 데이터 로드"""
        print("=" * 80)
        print("정답지 로드 중...")
        print("=" * 80)

        # Data 시트 읽기
        self.gt_data = pd.read_excel(self.ground_truth_path, sheet_name='Data')

        print(f"✓ 정답지 로드 완료: {len(self.gt_data)}개 샘플")
        print(f"  - 컬럼 수: {len(self.gt_data.columns)}")

        # 이름 매핑 (파일명 -> 간단한 이름)
        self.name_mapping = self._extract_names()

    def _extract_names(self):
        """파일명에서 이름 추출"""
        name_mapping = {}

        for idx, row in self.gt_data.iterrows():
            name_field = str(row['Name'])

            # 파일 경로에서 이름 추출
            if '.txt' in name_field or '.xlsx' in name_field:
                # 예: '1이선미숫자.txt' -> '이선미'
                parts = name_field.split('\\')[-1]  # 파일명만
                parts = parts.replace('.txt', '').replace('.xlsx', '')

                # 숫자 제거 및 한글 이름 추출
                import re
                korean_name = re.sub(r'[0-9]', '', parts)
                korean_name = re.sub(r'숫자|잔상|호흡', '', korean_name)

                name_mapping[idx] = korean_name.strip()
            else:
                # 예: '2.방지수숫자' -> '방지수'
                import re
                korean_name = re.sub(r'[0-9\.]', '', name_field)
                korean_name = re.sub(r'숫자|잔상|호흡', '', korean_name)
                name_mapping[idx] = korean_name.strip()

        return name_mapping

    def extract_hrv_metrics(self):
        """정답지에서 HRV 지표 추출"""
        print("\n" + "=" * 80)
        print("정답지 HRV 지표 추출")
        print("=" * 80)

        hrv_columns = [
            'Name', 'bpm:', 'ibi:', 'sdnn:', 'sdsd:', 'rmssd:',
            'pnn20:', 'pnn50:', 'hr_mad:', 'sd1:', 'sd2:', 's:', 'sd1/sd2:',
            'breathingrate:', 'vlf:', 'lf:', 'hf:', 'lf/hf:',
            'p_total:', 'vlf_perc:', 'lf_perc:', 'hf_perc:', 'lf_nu:', 'hf_nu:'
        ]

        # 존재하는 컬럼만 선택
        available_cols = [col for col in hrv_columns if col in self.gt_data.columns]

        hrv_gt = self.gt_data[available_cols].copy()
        hrv_gt['extracted_name'] = hrv_gt.index.map(self.name_mapping)

        print(f"✓ HRV 지표 추출 완료")
        print(f"  - 사용 가능한 지표: {len(available_cols)-1}개")
        print(f"  - 샘플 수: {len(hrv_gt)}")

        # 통계 요약
        print("\n[정답지 HRV 통계 요약]")
        for col in available_cols[1:]:  # Name 제외
            values = hrv_gt[col].dropna()
            if len(values) > 0:
                print(f"  {col:20s}: Mean={values.mean():10.2f}, Std={values.std():10.2f}, "
                      f"Min={values.min():10.2f}, Max={values.max():10.2f}")

        return hrv_gt

    def extract_eeg_metrics(self):
        """정답지에서 EEG 주파수 대역 지표 추출"""
        print("\n" + "=" * 80)
        print("정답지 EEG 지표 추출")
        print("=" * 80)

        # Relative power 지표 (소문자)
        eeg_columns = [
            'Name', 'd', 't', 'a', 'lb', 'hb', 'g',  # Left
            'dR', 'tR', 'aR', 'lbR', 'hbR', 'gR',   # Right
            'Davg', 'Tavg', 'Aavg', 'Lbavg', 'Hbavg', 'Gavg',  # Average
            'D_Asy', 'T_Asy', 'A_Asy', 'LB_Asy', 'HB_Asy', 'G_Asy'  # Asymmetry
        ]

        # 존재하는 컬럼만 선택
        available_cols = [col for col in eeg_columns if col in self.gt_data.columns]

        eeg_gt = self.gt_data[available_cols].copy()
        eeg_gt['extracted_name'] = eeg_gt.index.map(self.name_mapping)

        print(f"✓ EEG 지표 추출 완료")
        print(f"  - 사용 가능한 지표: {len(available_cols)-1}개")
        print(f"  - 샘플 수: {len(eeg_gt)}")

        # 통계 요약
        print("\n[정답지 EEG 통계 요약]")
        for col in available_cols[1:]:  # Name 제외
            values = eeg_gt[col].dropna()
            if len(values) > 0:
                print(f"  {col:15s}: Mean={values.mean():8.4f}, Std={values.std():8.4f}")

        return eeg_gt

    def load_current_results(self):
        """현재 알고리즘 분석 결과 로드"""
        print("\n" + "=" * 80)
        print("현재 알고리즘 분석 결과 로드")
        print("=" * 80)

        results = {}

        for filename in os.listdir(self.analysis_data_dir):
            if filename.endswith('_metadata.json'):
                # 메타데이터 읽기
                metadata_path = os.path.join(self.analysis_data_dir, filename)
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                # 분석 데이터 읽기
                csv_filename = filename.replace('_metadata.json', '_analysis.csv')
                csv_path = os.path.join(self.analysis_data_dir, csv_filename)

                if os.path.exists(csv_path):
                    analysis_df = pd.read_csv(csv_path)

                    # 이름 추출
                    name = metadata.get('name', '')

                    results[name] = {
                        'metadata': metadata,
                        'timeseries': analysis_df
                    }

        print(f"✓ 현재 알고리즘 결과 로드 완료: {len(results)}개 샘플")

        return results

    def compare_metrics(self, gt_hrv, current_results):
        """정답지와 현재 결과 비교"""
        print("\n" + "=" * 80)
        print("정답지 vs 현재 알고리즘 비교")
        print("=" * 80)

        comparison_results = []

        # 이름별로 매칭
        for idx, row in gt_hrv.iterrows():
            name = row['extracted_name']

            if name in current_results:
                print(f"\n[{name}] 비교 중...")

                # 현재 결과에서 HRV 계산 (시계열 평균)
                current = current_results[name]['timeseries']

                comparison = {
                    'name': name,
                    'gt_available': True,
                    'current_available': True
                }

                # 현재는 EEG만 분석되어 있으므로 EEG 비교
                # (HRV는 아직 실제 PPG 데이터로 분석되지 않음)
                print(f"  ⚠ HRV 비교는 PPG 데이터 필요 (현재 EEG만 분석됨)")

                comparison_results.append(comparison)
            else:
                print(f"  ✗ {name}: 현재 결과에 없음")

        return comparison_results

    def calculate_statistics(self, gt_hrv):
        """정답지 통계 분석"""
        print("\n" + "=" * 80)
        print("정답지 통계 분석")
        print("=" * 80)

        # HRV 지표 통계
        hrv_metrics = ['bpm:', 'ibi:', 'sdnn:', 'rmssd:', 'pnn50:', 'lf:', 'hf:', 'lf/hf:']

        stats_results = {}

        for metric in hrv_metrics:
            if metric in gt_hrv.columns:
                values = gt_hrv[metric].dropna()

                if len(values) > 0:
                    stats_results[metric] = {
                        'count': len(values),
                        'mean': float(values.mean()),
                        'std': float(values.std()),
                        'min': float(values.min()),
                        'max': float(values.max()),
                        'median': float(values.median()),
                        'q25': float(values.quantile(0.25)),
                        'q75': float(values.quantile(0.75))
                    }

        # 결과 출력
        print("\n[HRV 지표별 통계]")
        print(f"{'Metric':<15} {'Count':>6} {'Mean':>12} {'Std':>12} {'Min':>12} {'Max':>12}")
        print("-" * 80)

        for metric, stat in stats_results.items():
            print(f"{metric:<15} {stat['count']:>6} {stat['mean']:>12.2f} {stat['std']:>12.2f} "
                  f"{stat['min']:>12.2f} {stat['max']:>12.2f}")

        return stats_results

    def generate_report(self, output_path='validation_report.md'):
        """검증 리포트 생성"""
        print("\n" + "=" * 80)
        print("검증 리포트 생성")
        print("=" * 80)

        # HRV 지표 추출
        hrv_gt = self.extract_hrv_metrics()

        # EEG 지표 추출
        eeg_gt = self.extract_eeg_metrics()

        # 현재 결과 로드
        current_results = self.load_current_results()

        # 통계 계산
        stats_results = self.calculate_statistics(hrv_gt)

        # 비교
        comparison = self.compare_metrics(hrv_gt, current_results)

        # 마크다운 리포트 생성
        report = self._generate_markdown_report(hrv_gt, eeg_gt, current_results,
                                                  stats_results, comparison)

        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n✓ 리포트 저장 완료: {output_path}")

        return output_path

    def _generate_markdown_report(self, hrv_gt, eeg_gt, current_results,
                                   stats_results, comparison):
        """마크다운 형식 리포트 생성"""

        report = f"""# EEG-HRV 알고리즘 검증 리포트

## 1. 개요

**검증 날짜**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

**정답지**: {self.ground_truth_path}
- 총 샘플 수: {len(self.gt_data)}
- HRV 지표 수: {len([c for c in hrv_gt.columns if c.endswith(':')])}
- EEG 지표 수: {len([c for c in eeg_gt.columns if c not in ['Name', 'extracted_name']])}

**현재 알고리즘 결과**: {self.analysis_data_dir}
- 분석된 샘플 수: {len(current_results)}

---

## 2. 정답지 데이터 분석

### 2.1 HRV 지표 통계

| 지표 | 샘플수 | 평균 | 표준편차 | 최소값 | 최대값 | 중앙값 |
|------|--------|------|----------|--------|--------|--------|
"""

        for metric, stat in stats_results.items():
            report += f"| {metric} | {stat['count']} | {stat['mean']:.2f} | {stat['std']:.2f} | {stat['min']:.2f} | {stat['max']:.2f} | {stat['median']:.2f} |\n"

        report += """
---

## 3. 현재 알고리즘 분석

### 3.1 구현 현황

**✓ 구현된 기능**:
- EEG 주파수 대역 분석 (Delta, Theta, Alpha, Low Beta, High Beta, Gamma)
- 시계열 변화점 감지
- 스무딩 알고리즘

**⚠ 미구현/부분 구현**:
- **HRV 분석**: hrv_analyzer.py 모듈은 있으나, 실제 PPG 데이터 분석 미실행
  - heartpy 라이브러리 기반
  - Time Domain 지표: BPM, IBI, SDNN, RMSSD, pNN50 등
  - Frequency Domain 지표: LF, HF, LF/HF ratio

- **추가 필요 지표**:
  - sd1, sd2 (Poincaré plot)
  - VLF (Very Low Frequency)
  - Normalized units (lf_nu, hf_nu)
  - Breathing rate 추정

### 3.2 정답지와의 차이점

"""

        # 정답지에는 있지만 현재 구현에 없는 지표들
        missing_metrics = [
            'sd1, sd2, sd1/sd2 (Poincaré plot 지표)',
            'vlf, vlf_perc (Very Low Frequency)',
            'lf_nu, hf_nu (Normalized Units)',
            'breathingrate (호흡수)',
            's (sd1 * sd2, 총 변이도)',
            'p_total (총 파워)',
            'EEG 좌/우 비대칭성 (Asymmetry)',
            'EEG Absolute/Relative power 구분'
        ]

        report += "**현재 누락된 지표**:\n\n"
        for i, metric in enumerate(missing_metrics, 1):
            report += f"{i}. {metric}\n"

        report += """
---

## 4. 비교 결과

### 4.1 매칭된 샘플

"""

        # 매칭된 샘플 리스트
        matched_count = len([c for c in comparison if c.get('current_available')])
        report += f"- 정답지에 있는 샘플: {len(hrv_gt)}개\n"
        report += f"- 현재 분석된 샘플: {len(current_results)}개\n"
        report += f"- 매칭된 샘플: {matched_count}개\n\n"

        report += "| 이름 | 정답지 | 현재 결과 | 상태 |\n"
        report += "|------|--------|-----------|------|\n"

        for comp in comparison:
            status = "✓" if comp['current_available'] else "✗"
            report += f"| {comp['name']} | ✓ | {status} | "
            if comp['current_available']:
                report += "EEG만 분석됨 (HRV 없음) |\n"
            else:
                report += "분석 필요 |\n"

        report += """
---

## 5. 결론 및 권장사항

### 5.1 현재 상태

현재 알고리즘은 **EEG 주파수 분석**에 집중되어 있으며, HRV 분석 모듈은 구현되어 있으나 실제 데이터에 적용되지 않았습니다.

### 5.2 개선 방안

1. **HRV 분석 활성화**
   - PPG 데이터 추출 (원본 엑셀에서 PPG 채널 확인)
   - hrv_analyzer.py 모듈 적용
   - heartpy 외에 hrv-analysis 라이브러리 고려 (더 많은 지표 제공)

2. **추가 지표 구현**
   - Poincaré plot 지표 (sd1, sd2, sd1/sd2)
   - VLF 대역 분석
   - Normalized units 계산
   - 호흡수 추정 알고리즘

3. **EEG 분석 보완**
   - 좌/우 비대칭성 계산
   - Absolute vs Relative power 구분
   - 통계적 요약 (평균, 표준편차 등)

4. **정확도 검증**
   - 정답지 HRV 값과 계산된 HRV 값 비교
   - 오차율 계산 (RMSE, MAE, MAPE)
   - 상관관계 분석 (Pearson, Spearman)

### 5.3 우선순위

**높음**:
1. PPG 데이터 추출 및 HRV 분석 실행
2. 기본 HRV 지표 (BPM, SDNN, RMSSD, LF, HF) 검증

**중간**:
3. 추가 HRV 지표 구현 (sd1, sd2, VLF 등)
4. EEG 통계 요약 계산

**낮음**:
5. 고급 분석 기능 (비대칭성, 비율 지표 등)

---

## 6. 참고사항

- 정답지는 뇌공학자가 검증한 **Ground Truth**로 사용
- 현재 알고리즘의 **정확도 목표**: 오차율 < 5%
- HRV 분석은 최소 **60초 이상** 데이터 필요 (안정적인 주파수 분석)
"""

        return report


def main():
    """메인 실행 함수"""

    # 경로 설정
    ground_truth = './참고 개발코드/01.Results_0128.xlsx'
    analysis_dir = './analysis_data'

    # 검증기 생성
    validator = AlgorithmValidator(ground_truth, analysis_dir)

    # 리포트 생성
    report_path = validator.generate_report('validation_report.md')

    print("\n" + "=" * 80)
    print("검증 완료!")
    print("=" * 80)
    print(f"\n리포트 파일: {report_path}")
    print("\n다음 단계:")
    print("  1. validation_report.md 파일 확인")
    print("  2. PPG 데이터 추출 및 HRV 분석 실행")
    print("  3. 정확도 비교 수행")


if __name__ == '__main__':
    main()
