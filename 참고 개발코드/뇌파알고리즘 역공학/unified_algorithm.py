import numpy as np
import pandas as pd
import scipy.signal
import warnings
warnings.filterwarnings('ignore')

class UnifiedEEGAlgorithm:
    def __init__(self, sampling_rate=250):
        self.sampling_rate = sampling_rate
        self.frequency_bands = {
            'delta': (0, 4),
            'theta': (4, 8),
            'alpha': (8, 12),
            'low_beta': (12, 18),
            'high_beta': (18, 30),
            'gamma': (30, 50)
        }

        # 목표값 정의
        self.targets = {
            '숫자': {
                'left_delta': 476.24, 'left_theta': 13.39, 'left_alpha': 6.26,
                'right_delta': 786.90, 'right_theta': 19.68, 'right_alpha': 7.90
            },
            '잔상': {
                'left_delta': 963.15, 'left_theta': 10.01, 'left_alpha': 5.90,
                'right_delta': 1010.26, 'right_theta': 10.35, 'right_alpha': 5.83
            },
            '호흡': {
                'left_delta': 174.89, 'left_theta': 4.22, 'left_alpha': 7.54,
                'right_delta': 160.54, 'right_theta': 4.02, 'right_alpha': 6.51
            }
        }

    def load_excel_data(self, excel_file):
        """Excel 로우 데이터 로드"""
        data = pd.read_excel(excel_file, header=None)

        # 데이터 타입에 따라 처리
        if data.iloc[0, 0].__class__.__name__ == 'str':
            # 문자열 형태 (쉼표 포함)
            def clean_string_data(col):
                return pd.to_numeric(col.astype(str).str.replace(',', '').str.replace('"', ''), errors='coerce').fillna(0).values
            eeg1 = clean_string_data(data.iloc[:, 0])
            eeg2 = clean_string_data(data.iloc[:, 1])
        else:
            # 숫자 형태
            eeg1 = pd.to_numeric(data.iloc[:, 0], errors='coerce').fillna(0).values
            eeg2 = pd.to_numeric(data.iloc[:, 1], errors='coerce').fillna(0).values

        return {'EEG1': eeg1, 'EEG2': eeg2}

    def test_single_algorithm(self, params):
        """단일 알고리즘으로 모든 조건 테스트"""
        test_files = [
            ("01.이선미 숫자.xlsx", "숫자"),
            ("01.이선미 잔상.xlsx", "잔상"),
            ("01.이선미 호흡.xlsx", "호흡")
        ]

        total_errors = []
        detailed_results = {}

        print(f"\n=== 파라미터 테스트: {params} ===")

        for filename, condition in test_files:
            try:
                raw_data = self.load_excel_data(filename)
                targets = self.targets[condition]

                # 신호 전처리
                results = {}
                for channel_idx, channel in enumerate(['EEG1', 'EEG2']):
                    signal = raw_data[channel]
                    side = 'LEFT' if channel_idx == 0 else 'RIGHT'

                    # 전처리 적용
                    processed = self.apply_preprocessing(signal, params)

                    # PSD 계산
                    freqs, psd = self.calculate_psd(processed, params)

                    # 파워 추출
                    band_powers = self.extract_band_powers(freqs, psd, params)

                    results[side] = band_powers

                # 오차 계산
                error = self.calculate_error(results, targets)
                total_errors.append(error)
                detailed_results[condition] = {'error': error, 'results': results}

                print(f"{condition:4s}: 오차={error:.4f}")

            except Exception as e:
                print(f"{filename} 실패: {e}")
                total_errors.append(float('inf'))

        avg_error = np.mean(total_errors) if total_errors else float('inf')
        print(f"평균 오차: {avg_error:.4f}")

        return avg_error, detailed_results

    def apply_preprocessing(self, signal, params):
        """파라미터에 따른 전처리 적용"""
        processed = signal.copy()

        if params.get('use_notch', True):
            # 60Hz 노치 필터
            b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
            processed = scipy.signal.filtfilt(b_notch, a_notch, processed)

        if params.get('use_bandpass', True):
            # 대역통과 필터
            lowcut = params.get('lowcut', 0.5)
            highcut = params.get('highcut', 50)
            nyquist = self.sampling_rate / 2
            b, a = scipy.signal.butter(4, [lowcut/nyquist, highcut/nyquist], btype='band')
            processed = scipy.signal.filtfilt(b, a, processed)

        return processed

    def calculate_psd(self, signal, params):
        """PSD 계산"""
        method = params.get('psd_method', 'welch')

        if method == 'welch':
            window_sec = params.get('window_sec', 4)
            overlap_ratio = params.get('overlap_ratio', 0.5)

            nperseg = int(self.sampling_rate * window_sec)
            noverlap = int(nperseg * overlap_ratio)

            freqs, psd = scipy.signal.welch(
                signal, self.sampling_rate,
                nperseg=nperseg,
                noverlap=noverlap,
                window='hann'
            )
        elif method == 'fft':
            # FFT 방법
            freqs = np.fft.fftfreq(len(signal), 1/self.sampling_rate)[:len(signal)//2]
            psd = np.abs(np.fft.fft(signal * np.hanning(len(signal)))[:len(signal)//2])**2
        else:
            # 기본 welch
            freqs, psd = scipy.signal.welch(signal, self.sampling_rate)

        return freqs, psd

    def extract_band_powers(self, freqs, psd, params):
        """주파수 대역별 파워 추출"""
        power_method = params.get('power_method', 'trapz')
        band_powers = {}

        for band_name, (fmin, fmax) in self.frequency_bands.items():
            band_mask = (freqs >= fmin) & (freqs <= fmax)
            if not np.any(band_mask):
                band_powers[band_name] = 0
                continue

            band_freqs = freqs[band_mask]
            band_psd = psd[band_mask]

            if power_method == 'trapz':
                power = np.trapz(band_psd, band_freqs)
            elif power_method == 'mean':
                power = np.mean(band_psd) * (fmax - fmin)
            elif power_method == 'sum':
                power = np.sum(band_psd)
            elif power_method == 'log':
                power = np.log10(np.mean(band_psd) + 1e-12)
            elif power_method == 'sqrt':
                power = np.sqrt(np.mean(band_psd))
            else:
                power = np.trapz(band_psd, band_freqs)

            band_powers[band_name] = power

        return band_powers

    def calculate_error(self, results, targets):
        """목표값과의 오차 계산"""
        total_error = 0
        count = 0

        key_mapping = {
            'left_delta': 'delta',
            'left_theta': 'theta',
            'left_alpha': 'alpha',
            'right_delta': 'delta',
            'right_theta': 'theta',
            'right_alpha': 'alpha'
        }

        for target_key, target_value in targets.items():
            if target_value == 0:
                continue

            side = 'LEFT' if 'left_' in target_key else 'RIGHT'
            band = key_mapping[target_key]

            if side in results and band in results[side]:
                our_value = results[side][band]
                if our_value > 0:
                    error = abs(our_value - target_value) / target_value
                    total_error += error
                    count += 1

        return total_error / count if count > 0 else float('inf')

    def find_unified_best_params(self):
        """모든 조건에서 균형잡힌 최적 파라미터 찾기"""
        print("=== 통합 알고리즘 최적화 시작 ===")

        best_avg_error = float('inf')
        best_params = None
        best_details = None

        # 파라미터 조합들
        param_combinations = [
            # 기본 조합들
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': False, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 윈도우 크기 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 2, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 8, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 1, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 파워 계산 방법 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'mean'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'sum'},

            # 오버랩 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.25, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.75, 'power_method': 'trapz'},

            # FFT 방법
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'fft', 'power_method': 'trapz'},

            {'use_notch': False, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'fft', 'power_method': 'mean'},

            # 필터 범위 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 1, 'highcut': 45,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.1, 'highcut': 60,
             'psd_method': 'welch', 'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 복합 최적화 (이전 결과 기반)
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 2, 'overlap_ratio': 0.25, 'power_method': 'mean'},

            {'use_notch': False, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'psd_method': 'welch', 'window_sec': 6, 'overlap_ratio': 0.5, 'power_method': 'trapz'},
        ]

        print(f"총 {len(param_combinations)}개 조합 테스트...")

        for i, params in enumerate(param_combinations):
            print(f"\n[{i+1}/{len(param_combinations)}]", end=" ")
            avg_error, details = self.test_single_algorithm(params)

            if avg_error < best_avg_error:
                best_avg_error = avg_error
                best_params = params
                best_details = details
                print(f"*** 새로운 최적값! 평균 오차: {avg_error:.4f} ***")

        return best_params, best_details, best_avg_error

    def detailed_comparison(self, params, details):
        """상세 비교 결과 출력"""
        print(f"\n{'='*60}")
        print(f"최종 통합 알고리즘 결과")
        print(f"{'='*60}")
        print(f"최적 파라미터: {params}")
        print(f"평균 오차: {details}")

        conditions = ['숫자', '잔상', '호흡']

        for condition in conditions:
            if condition in details:
                print(f"\n{condition} 조건:")
                results = details[condition]['results']
                targets = self.targets[condition]
                error = details[condition]['error']

                print(f"  오차: {error:.4f}")

                for side in ['LEFT', 'RIGHT']:
                    print(f"  {side}:")
                    for band in ['delta', 'theta', 'alpha']:
                        target_key = f"{side.lower()}_{band}"
                        if target_key in targets and band in results[side]:
                            our_val = results[side][band]
                            target_val = targets[target_key]
                            ratio = our_val / target_val if target_val > 0 else 0
                            print(f"    {band:6s}: {our_val:8.2f} -> 목표: {target_val:8.2f} (비율: {ratio:.3f})")

# 테스트 실행
if __name__ == "__main__":
    analyzer = UnifiedEEGAlgorithm()

    # 통합 알고리즘 찾기
    best_params, best_details, best_avg_error = analyzer.find_unified_best_params()

    # 상세 결과 출력
    if best_params:
        analyzer.detailed_comparison(best_params, best_details)