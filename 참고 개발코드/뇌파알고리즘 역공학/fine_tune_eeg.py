import numpy as np
import pandas as pd
import scipy.signal
import warnings
warnings.filterwarnings('ignore')

class FineTuneEEG:
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

    def preprocess_signal_variants(self, signal):
        """다양한 전처리 방법 시도"""
        variants = {}

        # 기본 신호
        variants['original'] = signal

        # 1. 노치 필터만
        b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
        variants['notch_only'] = scipy.signal.filtfilt(b_notch, a_notch, signal)

        # 2. 대역통과 필터만 (다양한 범위)
        filter_ranges = [(0.5, 50), (1, 45), (0.1, 60), (2, 40)]
        for i, (low, high) in enumerate(filter_ranges):
            nyquist = self.sampling_rate / 2
            b, a = scipy.signal.butter(4, [low/nyquist, high/nyquist], btype='band')
            variants[f'bandpass_{i}'] = scipy.signal.filtfilt(b, a, signal)

        # 3. 노치 + 대역통과 조합
        for i, (low, high) in enumerate(filter_ranges):
            notched = scipy.signal.filtfilt(b_notch, a_notch, signal)
            nyquist = self.sampling_rate / 2
            b, a = scipy.signal.butter(4, [low/nyquist, high/nyquist], btype='band')
            variants[f'notch_band_{i}'] = scipy.signal.filtfilt(b, a, notched)

        return variants

    def calculate_psd_variants(self, signal):
        """다양한 PSD 계산 방법"""
        psd_results = {}

        # 윈도우 크기 변형 (초 단위)
        window_sizes = [1, 2, 4, 8, 16]

        # 오버랩 비율
        overlap_ratios = [0.25, 0.5, 0.75]

        for window_sec in window_sizes:
            nperseg = int(self.sampling_rate * window_sec)
            if nperseg > len(signal):
                continue

            for overlap_ratio in overlap_ratios:
                noverlap = int(nperseg * overlap_ratio)

                try:
                    freqs, psd = scipy.signal.welch(
                        signal, self.sampling_rate,
                        nperseg=nperseg,
                        noverlap=noverlap,
                        window='hann'
                    )
                    key = f'w{window_sec}s_o{overlap_ratio}'
                    psd_results[key] = (freqs, psd)
                except:
                    continue

        # 다른 방법들도 시도
        # FFT + 윈도잉
        try:
            freqs_fft = np.fft.fftfreq(len(signal), 1/self.sampling_rate)[:len(signal)//2]
            psd_fft = np.abs(np.fft.fft(signal * np.hanning(len(signal)))[:len(signal)//2])**2
            psd_results['fft_hann'] = (freqs_fft, psd_fft)
        except:
            pass

        return psd_results

    def extract_band_power_variants(self, freqs, psd):
        """다양한 파워 추출 방법"""
        band_powers = {}

        for band_name, (fmin, fmax) in self.frequency_bands.items():
            band_mask = (freqs >= fmin) & (freqs <= fmax)
            if not np.any(band_mask):
                continue

            band_freqs = freqs[band_mask]
            band_psd = psd[band_mask]

            # 방법 1: Trapz (면적)
            power_trapz = np.trapz(band_psd, band_freqs)

            # 방법 2: 평균 * 대역폭
            power_mean = np.mean(band_psd) * (fmax - fmin)

            # 방법 3: 합
            power_sum = np.sum(band_psd)

            # 방법 4: 로그 파워
            power_log = np.log10(np.mean(band_psd) + 1e-12)

            # 방법 5: 제곱근
            power_sqrt = np.sqrt(np.mean(band_psd))

            band_powers[band_name] = {
                'trapz': power_trapz,
                'mean': power_mean,
                'sum': power_sum,
                'log': power_log,
                'sqrt': power_sqrt
            }

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

    def find_best_parameters(self, filename, condition):
        """최적 파라미터 조합 찾기"""
        print(f"\n=== {filename} ({condition}) 최적화 ===")

        raw_data = self.load_excel_data(filename)
        targets = self.targets[condition]

        best_error = float('inf')
        best_params = None
        best_results = None

        # 진행상황 카운터
        total_combinations = 0
        current_combination = 0

        # 모든 조합 수 계산
        for channel in ['EEG1', 'EEG2']:
            signal = raw_data[channel]
            preprocess_variants = self.preprocess_signal_variants(signal)
            for preprocess_key in preprocess_variants.keys():
                psd_variants = self.calculate_psd_variants(preprocess_variants[preprocess_key])
                for psd_key in psd_variants.keys():
                    for power_method in ['trapz', 'mean', 'sum', 'log', 'sqrt']:
                        total_combinations += 1

        print(f"총 {total_combinations}개 조합 테스트 중...")

        # 파라미터 조합 시도
        for channel_idx, channel in enumerate(['EEG1', 'EEG2']):
            signal = raw_data[channel]
            side = 'LEFT' if channel_idx == 0 else 'RIGHT'

            # 전처리 변형들
            preprocess_variants = self.preprocess_signal_variants(signal)

            for preprocess_key, processed_signal in preprocess_variants.items():
                # PSD 계산 변형들
                psd_variants = self.calculate_psd_variants(processed_signal)

                for psd_key, (freqs, psd) in psd_variants.items():
                    # 파워 추출 변형들
                    band_powers = self.extract_band_power_variants(freqs, psd)

                    for power_method in ['trapz', 'mean', 'sum', 'log', 'sqrt']:
                        current_combination += 1

                        # 현재 조합으로 결과 생성
                        current_results = {}
                        if channel_idx == 0:  # LEFT만 처리
                            current_results['LEFT'] = {}
                            for band in self.frequency_bands.keys():
                                if band in band_powers:
                                    current_results['LEFT'][band] = band_powers[band][power_method]

                            # RIGHT는 기본값으로 (임시)
                            current_results['RIGHT'] = current_results['LEFT'].copy()

                        # 양쪽 채널이 모두 처리되었을 때만 오차 계산
                        if channel_idx == 1:  # RIGHT 처리 중
                            # LEFT는 이전 최적값 사용 (단순화)
                            current_results = {'LEFT': {}, 'RIGHT': {}}
                            for band in self.frequency_bands.keys():
                                if band in band_powers:
                                    current_results['RIGHT'][band] = band_powers[band][power_method]

                            # LEFT는 기본 설정으로 (임시)
                            left_signal = raw_data['EEG1']
                            left_processed = scipy.signal.filtfilt(
                                *scipy.signal.butter(4, [0.5/125, 50/125], btype='band'),
                                left_signal
                            )
                            freqs_left, psd_left = scipy.signal.welch(left_processed, self.sampling_rate, nperseg=1000)
                            band_powers_left = self.extract_band_power_variants(freqs_left, psd_left)

                            for band in self.frequency_bands.keys():
                                if band in band_powers_left:
                                    current_results['LEFT'][band] = band_powers_left[band]['trapz']

                            # 오차 계산
                            error = self.calculate_error(current_results, targets)

                            if error < best_error:
                                best_error = error
                                best_params = {
                                    'preprocess': preprocess_key,
                                    'psd_method': psd_key,
                                    'power_method': power_method
                                }
                                best_results = current_results.copy()

                                print(f"새로운 최적값 발견! 오차: {error:.6f}")
                                print(f"  파라미터: {best_params}")

                # 진행상황 출력 (10%마다)
                if current_combination % max(1, total_combinations // 10) == 0:
                    progress = current_combination / total_combinations * 100
                    print(f"  진행률: {progress:.1f}% ({current_combination}/{total_combinations})")

        return best_params, best_results, best_error

    def test_specific_combination(self, filename, condition, params):
        """특정 파라미터 조합으로 테스트"""
        print(f"\n=== {filename} 특정 파라미터 테스트 ===")

        raw_data = self.load_excel_data(filename)
        targets = self.targets[condition]

        results = {}

        for channel_idx, channel in enumerate(['EEG1', 'EEG2']):
            signal = raw_data[channel]
            side = 'LEFT' if channel_idx == 0 else 'RIGHT'

            # 지정된 전처리 적용
            if params['preprocess'] == 'original':
                processed = signal
            elif params['preprocess'] == 'notch_only':
                b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
                processed = scipy.signal.filtfilt(b_notch, a_notch, signal)
            else:
                # 다른 전처리 방법들...
                processed = signal

            # PSD 계산
            if 'w' in params['psd_method'] and 'o' in params['psd_method']:
                parts = params['psd_method'].split('_')
                window_sec = float(parts[0][1:-1])  # w4s -> 4
                overlap_ratio = float(parts[1][1:])  # o0.5 -> 0.5

                nperseg = int(self.sampling_rate * window_sec)
                noverlap = int(nperseg * overlap_ratio)

                freqs, psd = scipy.signal.welch(
                    processed, self.sampling_rate,
                    nperseg=nperseg,
                    noverlap=noverlap
                )
            else:
                # 기본 설정
                freqs, psd = scipy.signal.welch(processed, self.sampling_rate)

            # 파워 계산
            band_powers = self.extract_band_power_variants(freqs, psd)

            results[side] = {}
            for band in self.frequency_bands.keys():
                if band in band_powers:
                    results[side][band] = band_powers[band][params['power_method']]

        # 결과 출력
        print(f"파라미터: {params}")
        print(f"오차: {self.calculate_error(results, targets):.6f}")

        for side in ['LEFT', 'RIGHT']:
            print(f"\n{side}:")
            for band in ['delta', 'theta', 'alpha']:
                target_key = f"{side.lower()}_{band}"
                if target_key in targets and band in results[side]:
                    our_val = results[side][band]
                    target_val = targets[target_key]
                    ratio = our_val / target_val if target_val > 0 else 0
                    print(f"  {band:6s}: {our_val:8.2f} -> 목표: {target_val:8.2f} (비율: {ratio:.3f})")

        return results

# 테스트 실행
if __name__ == "__main__":
    analyzer = FineTuneEEG()

    # 테스트할 파일들
    test_files = [
        ("01.이선미 숫자.xlsx", "숫자"),
        ("01.이선미 잔상.xlsx", "잔상"),
        ("01.이선미 호흡.xlsx", "호흡")
    ]

    # 각 파일에 대해 최적화
    for filename, condition in test_files:
        try:
            best_params, best_results, best_error = analyzer.find_best_parameters(filename, condition)

            print(f"\n{'='*50}")
            print(f"최종 결과 - {filename} ({condition})")
            print(f"최적 오차: {best_error:.6f}")
            print(f"최적 파라미터: {best_params}")

            # 특정 조합으로 재테스트
            if best_params:
                analyzer.test_specific_combination(filename, condition, best_params)

        except Exception as e:
            print(f"{filename} 처리 실패: {e}")