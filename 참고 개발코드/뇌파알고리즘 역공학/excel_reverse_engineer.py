import numpy as np
import pandas as pd
import scipy.signal
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class ExcelReverseEngineer:
    def __init__(self, sampling_rate=250):
        self.sampling_rate = sampling_rate
        # 과학자가 사용한 주파수 대역 (결과표 기준)
        self.frequency_bands = {
            'delta': (0, 4),
            'theta': (4, 8),
            'alpha': (8, 12),
            'low_beta': (12, 18),
            'high_beta': (18, 30),
            'gamma': (30, 50)
        }

    def load_excel_data(self, excel_file):
        """Excel 로우 데이터 로드"""
        print(f"Excel 데이터 로딩: {excel_file}")

        data = pd.read_excel(excel_file, header=None)
        print(f"데이터 형태: {data.shape}")

        # 숫자 변환 (이미 숫자인 경우가 많지만 안전장치)
        eeg1 = pd.to_numeric(data.iloc[:, 0], errors='coerce').fillna(0).values
        eeg2 = pd.to_numeric(data.iloc[:, 1], errors='coerce').fillna(0).values
        ppg = pd.to_numeric(data.iloc[:, 2], errors='coerce').fillna(0).values

        print(f"EEG1: {np.min(eeg1):.2f} ~ {np.max(eeg1):.2f}, mean={np.mean(eeg1):.2f}")
        print(f"EEG2: {np.min(eeg2):.2f} ~ {np.max(eeg2):.2f}, mean={np.mean(eeg2):.2f}")
        print(f"PPG: {np.min(ppg):.2f} ~ {np.max(ppg):.2f}, mean={np.mean(ppg):.2f}")

        return {'EEG1': eeg1, 'EEG2': eeg2, 'PPG': ppg}

    def load_target_results(self, results_file, subject_name, condition):
        """목표 결과값 로드"""
        df = pd.read_excel(results_file)

        # 해당 피험자와 조건 찾기
        target_row = None
        for idx, row in df.iterrows():
            name_str = str(row['Name']).lower()
            if subject_name.lower() in name_str and condition.lower() in name_str:
                target_row = row
                print(f"목표 데이터 발견 [Row {idx}]: {row['Name']}")
                break

        if target_row is None:
            print(f"'{subject_name} {condition}' 데이터를 찾을 수 없습니다")
            return None

        # 목표값 추출
        targets = {
            'left_delta': target_row['D(0-4)'],
            'left_theta': target_row['T(4-8)'],
            'left_alpha': target_row['A(8-12)'],
            'left_low_beta': target_row['LB(12-18)'],
            'left_high_beta': target_row['HB(18-30)'],
            'left_gamma': target_row['G(30-50)'],
            'right_delta': target_row['R_D(0-4)'],
            'right_theta': target_row['R_T(4-8)'],
            'right_alpha': target_row['R_A(8-12)'],
            'right_low_beta': target_row['R_LB(12-18)'],
            'right_high_beta': target_row['R_HB(18-30)'],
            'right_gamma': target_row['R_G(30-50)'],
            'bpm': target_row['bpm:'],
            'sdnn': target_row['sdnn:'],
            'rmssd': target_row['rmssd:'],
            'pnn50': target_row['pnn50:']
        }

        return targets

    def preprocess_signal(self, signal, use_notch=True, lowcut=0.5, highcut=50):
        """신호 전처리 - 파라미터 조정 가능"""
        processed = signal.copy()

        if use_notch:
            # 60Hz 노치 필터
            b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
            processed = scipy.signal.filtfilt(b_notch, a_notch, processed)

        # 대역통과 필터
        nyquist = self.sampling_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = scipy.signal.butter(4, [low, high], btype='band')
        processed = scipy.signal.filtfilt(b, a, processed)

        return processed

    def calculate_power_spectrum_variants(self, signal):
        """다양한 파라미터로 파워 스펙트럼 계산"""
        results = {}

        # 다양한 윈도우 크기 시도
        window_factors = [2, 4, 8, 16]  # 초 단위

        for factor in window_factors:
            nperseg = int(self.sampling_rate * factor)
            if nperseg < len(signal):
                freqs, psd = scipy.signal.welch(signal, self.sampling_rate,
                                              nperseg=nperseg,
                                              noverlap=nperseg//2)
                results[f'window_{factor}s'] = (freqs, psd)

        return results

    def extract_band_powers_all_methods(self, freqs, psd):
        """다양한 방법으로 대역별 파워 추출"""
        band_powers = {}

        for band_name, freq_range in self.frequency_bands.items():
            band_mask = (freqs >= freq_range[0]) & (freqs <= freq_range[1])

            # 방법 1: 면적 (trapz)
            power_trapz = np.trapz(psd[band_mask], freqs[band_mask])

            # 방법 2: 평균 파워
            power_mean = np.mean(psd[band_mask]) * (freq_range[1] - freq_range[0])

            # 방법 3: 최대값
            power_max = np.max(psd[band_mask])

            # 방법 4: 합계
            power_sum = np.sum(psd[band_mask])

            band_powers[band_name] = {
                'trapz': power_trapz,
                'mean': power_mean,
                'max': power_max,
                'sum': power_sum
            }

        return band_powers

    def calculate_hrv_variants(self, ppg_signal):
        """다양한 파라미터로 HRV 계산"""
        results = {}

        # 다양한 피크 검출 파라미터
        height_factors = [0.2, 0.3, 0.5, 0.8]  # 표준편차의 배수
        distance_factors = [3, 4, 5, 6]  # sampling_rate를 나누는 값

        for h_factor in height_factors:
            for d_factor in distance_factors:
                height_threshold = np.mean(ppg_signal) + h_factor * np.std(ppg_signal)
                distance = self.sampling_rate // d_factor

                peaks, _ = scipy.signal.find_peaks(ppg_signal,
                                                 height=height_threshold,
                                                 distance=distance)

                if len(peaks) < 5:
                    continue

                # R-R 간격 계산
                rr_intervals = np.diff(peaks) / self.sampling_rate * 1000

                # 이상치 제거
                rr_clean = rr_intervals[(rr_intervals > 300) & (rr_intervals < 2000)]

                if len(rr_clean) < 3:
                    continue

                bpm = 60000 / np.mean(rr_clean)
                sdnn = np.std(rr_clean)
                rmssd = np.sqrt(np.mean(np.diff(rr_clean)**2))
                nn50 = np.sum(np.abs(np.diff(rr_clean)) > 50)
                pnn50 = nn50 / len(rr_clean) * 100

                param_key = f'h{h_factor}_d{d_factor}'
                results[param_key] = {
                    'bpm': bpm,
                    'sdnn': sdnn,
                    'rmssd': rmssd,
                    'pnn50': pnn50,
                    'num_peaks': len(peaks)
                }

        return results

    def find_best_match(self, raw_data, targets):
        """최적의 파라미터 조합 찾기"""
        print("\n=== 최적 파라미터 탐색 ===")

        best_score = float('inf')
        best_params = None
        best_results = None

        # 전처리 옵션들
        notch_options = [True, False]
        filter_options = [(0.5, 50), (1, 45), (0.1, 60)]

        for use_notch in notch_options:
            for lowcut, highcut in filter_options:

                # EEG 신호 전처리
                eeg1_clean = self.preprocess_signal(raw_data['EEG1'], use_notch, lowcut, highcut)
                eeg2_clean = self.preprocess_signal(raw_data['EEG2'], use_notch, lowcut, highcut)

                # 다양한 파워 스펙트럼 방법 시도
                psd_variants1 = self.calculate_power_spectrum_variants(eeg1_clean)
                psd_variants2 = self.calculate_power_spectrum_variants(eeg2_clean)

                for window_key in psd_variants1.keys():
                    freqs1, psd1 = psd_variants1[window_key]
                    freqs2, psd2 = psd_variants2[window_key]

                    # 대역별 파워 계산
                    powers1 = self.extract_band_powers_all_methods(freqs1, psd1)
                    powers2 = self.extract_band_powers_all_methods(freqs2, psd2)

                    # 다양한 파워 추출 방법 시도
                    for power_method in ['trapz', 'mean', 'max', 'sum']:

                        # 현재 조합으로 계산된 값들
                        current_results = {}

                        # EEG 결과
                        for band in self.frequency_bands.keys():
                            current_results[f'left_{band}'] = powers1[band][power_method]
                            current_results[f'right_{band}'] = powers2[band][power_method]

                        # HRV 계산
                        hrv_variants = self.calculate_hrv_variants(raw_data['PPG'])

                        # 각 HRV 파라미터 조합 시도
                        for hrv_key, hrv_values in hrv_variants.items():
                            current_results.update({
                                'bpm': hrv_values['bpm'],
                                'sdnn': hrv_values['sdnn'],
                                'rmssd': hrv_values['rmssd'],
                                'pnn50': hrv_values['pnn50']
                            })

                            # 목표값과의 오차 계산
                            total_error = 0
                            for key, target_value in targets.items():
                                if key in current_results and target_value != 0:
                                    current_value = current_results[key]
                                    error = abs(current_value - target_value) / abs(target_value)
                                    total_error += error

                            # 최적 조합 업데이트
                            if total_error < best_score:
                                best_score = total_error
                                best_params = {
                                    'notch': use_notch,
                                    'lowcut': lowcut,
                                    'highcut': highcut,
                                    'window': window_key,
                                    'power_method': power_method,
                                    'hrv_params': hrv_key
                                }
                                best_results = current_results.copy()

        return best_params, best_results, best_score

    def compare_results(self, results, targets, params):
        """결과 비교 출력"""
        print(f"\n=== 최적 결과 (오차: {params['score']:.4f}) ===")
        print(f"파라미터: {params['params']}")

        print("\nEEG 주파수 대역별 비교:")
        for side in ['left', 'right']:
            print(f"\n{side.upper()}:")
            for band in self.frequency_bands.keys():
                key = f'{side}_{band}'
                our_val = results.get(key, 0)
                target_val = targets.get(key, 0)
                ratio = our_val / target_val if target_val != 0 else 0
                print(f"  {band:10s}: {our_val:8.2f} -> 목표: {target_val:8.2f} (비율: {ratio:.3f})")

        print("\nHRV 지표 비교:")
        for metric in ['bpm', 'sdnn', 'rmssd', 'pnn50']:
            our_val = results.get(metric, 0)
            target_val = targets.get(metric, 0)
            ratio = our_val / target_val if target_val != 0 else 0
            print(f"  {metric:6s}: {our_val:8.2f} -> 목표: {target_val:8.2f} (비율: {ratio:.3f})")

# 테스트 실행
if __name__ == "__main__":
    analyzer = ExcelReverseEngineer()

    # 테스트 파일들
    raw_file = "01.이선미 숫자.xlsx"
    results_file = "01.Results_0128.xlsx"
    subject_name = "이선미"
    condition = "숫자"

    print("=== Excel 기반 EEG 역공학 분석 ===")

    # 데이터 로드
    raw_data = analyzer.load_excel_data(raw_file)

    if raw_data:
        targets = analyzer.load_target_results(results_file, subject_name, condition)

        if targets:
            # 최적 파라미터 찾기
            best_params, best_results, best_score = analyzer.find_best_match(raw_data, targets)

            # 결과 출력
            analyzer.compare_results(best_results, targets, {
                'params': best_params,
                'score': best_score
            })
        else:
            print("목표값을 찾을 수 없습니다.")
    else:
        print("로우 데이터 로드 실패")