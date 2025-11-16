import numpy as np
import pandas as pd
import scipy.signal
import warnings
warnings.filterwarnings('ignore')

class QuickUnifiedTest:
    def __init__(self, sampling_rate=250):
        self.sampling_rate = sampling_rate
        self.frequency_bands = {
            'delta': (0, 4),
            'theta': (4, 8),
            'alpha': (8, 12)
        }

        # 목표값 (Alpha만 비교)
        self.targets = {
            '숫자': {'left_alpha': 6.26, 'right_alpha': 7.90},
            '잔상': {'left_alpha': 5.90, 'right_alpha': 5.83},
            '호흡': {'left_alpha': 7.54, 'right_alpha': 6.51}
        }

    def load_excel_data(self, excel_file):
        """Excel 로우 데이터 로드"""
        data = pd.read_excel(excel_file, header=None)

        if data.iloc[0, 0].__class__.__name__ == 'str':
            def clean_string_data(col):
                return pd.to_numeric(col.astype(str).str.replace(',', '').str.replace('"', ''), errors='coerce').fillna(0).values
            eeg1 = clean_string_data(data.iloc[:, 0])
            eeg2 = clean_string_data(data.iloc[:, 1])
        else:
            eeg1 = pd.to_numeric(data.iloc[:, 0], errors='coerce').fillna(0).values
            eeg2 = pd.to_numeric(data.iloc[:, 1], errors='coerce').fillna(0).values

        return {'EEG1': eeg1, 'EEG2': eeg2}

    def test_params(self, params):
        """파라미터 조합 테스트"""
        test_files = [
            ("01.이선미 숫자.xlsx", "숫자"),
            ("01.이선미 잔상.xlsx", "잔상"),
            ("01.이선미 호흡.xlsx", "호흡")
        ]

        errors = []

        for filename, condition in test_files:
            try:
                raw_data = self.load_excel_data(filename)
                targets = self.targets[condition]

                results = {}
                for channel_idx, channel in enumerate(['EEG1', 'EEG2']):
                    signal = raw_data[channel]
                    side = 'LEFT' if channel_idx == 0 else 'RIGHT'

                    # 전처리
                    if params['use_notch']:
                        b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
                        signal = scipy.signal.filtfilt(b_notch, a_notch, signal)

                    if params['use_bandpass']:
                        nyquist = self.sampling_rate / 2
                        low = params['lowcut'] / nyquist
                        high = params['highcut'] / nyquist
                        b, a = scipy.signal.butter(4, [low, high], btype='band')
                        signal = scipy.signal.filtfilt(b, a, signal)

                    # PSD 계산
                    nperseg = int(self.sampling_rate * params['window_sec'])
                    noverlap = int(nperseg * params['overlap_ratio'])

                    freqs, psd = scipy.signal.welch(signal, self.sampling_rate,
                                                  nperseg=nperseg, noverlap=noverlap)

                    # Alpha 파워만 계산
                    alpha_mask = (freqs >= 8) & (freqs <= 12)

                    if params['power_method'] == 'trapz':
                        alpha_power = np.trapz(psd[alpha_mask], freqs[alpha_mask])
                    elif params['power_method'] == 'mean':
                        alpha_power = np.mean(psd[alpha_mask]) * 4  # 4Hz 대역폭
                    else:
                        alpha_power = np.sum(psd[alpha_mask])

                    results[side] = alpha_power

                # 오차 계산 (Alpha만)
                error = 0
                count = 0
                for side in ['LEFT', 'RIGHT']:
                    target_key = f"{side.lower()}_alpha"
                    if target_key in targets:
                        our_val = results[side]
                        target_val = targets[target_key]
                        if target_val > 0:
                            error += abs(our_val - target_val) / target_val
                            count += 1

                errors.append(error / count if count > 0 else float('inf'))

            except:
                errors.append(float('inf'))

        return np.mean(errors)

    def find_best(self):
        """최적 파라미터 찾기"""
        print("=== 빠른 통합 알고리즘 테스트 ===")

        # 주요 파라미터 조합들
        param_sets = [
            # 기본
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 윈도우 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 2, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 8, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 1, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 파워 방법 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'mean'},

            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'sum'},

            # 오버랩 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 4, 'overlap_ratio': 0.25, 'power_method': 'trapz'},

            # 노치 필터 없음
            {'use_notch': False, 'use_bandpass': True, 'lowcut': 0.5, 'highcut': 50,
             'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},

            # 필터 범위 변형
            {'use_notch': True, 'use_bandpass': True, 'lowcut': 1, 'highcut': 45,
             'window_sec': 4, 'overlap_ratio': 0.5, 'power_method': 'trapz'},
        ]

        best_error = float('inf')
        best_params = None

        for i, params in enumerate(param_sets):
            error = self.test_params(params)
            print(f"[{i+1}] 오차: {error:.4f} - {params}")

            if error < best_error:
                best_error = error
                best_params = params
                print(f"*** 새로운 최적값! ***")

        print(f"\n최종 결과:")
        print(f"최적 오차: {best_error:.4f}")
        print(f"최적 파라미터: {best_params}")

        return best_params, best_error

    def detailed_test(self, params):
        """상세 테스트"""
        print(f"\n=== 상세 테스트: {params} ===")

        test_files = [
            ("01.이선미 숫자.xlsx", "숫자"),
            ("01.이선미 잔상.xlsx", "잔상"),
            ("01.이선미 호흡.xlsx", "호흡")
        ]

        for filename, condition in test_files:
            raw_data = self.load_excel_data(filename)
            targets = self.targets[condition]

            print(f"\n{condition} 조건:")

            for channel_idx, channel in enumerate(['EEG1', 'EEG2']):
                signal = raw_data[channel]
                side = 'LEFT' if channel_idx == 0 else 'RIGHT'

                # 동일한 처리 과정
                if params['use_notch']:
                    b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
                    signal = scipy.signal.filtfilt(b_notch, a_notch, signal)

                if params['use_bandpass']:
                    nyquist = self.sampling_rate / 2
                    low = params['lowcut'] / nyquist
                    high = params['highcut'] / nyquist
                    b, a = scipy.signal.butter(4, [low, high], btype='band')
                    signal = scipy.signal.filtfilt(b, a, signal)

                nperseg = int(self.sampling_rate * params['window_sec'])
                noverlap = int(nperseg * params['overlap_ratio'])

                freqs, psd = scipy.signal.welch(signal, self.sampling_rate,
                                              nperseg=nperseg, noverlap=noverlap)

                alpha_mask = (freqs >= 8) & (freqs <= 12)

                if params['power_method'] == 'trapz':
                    alpha_power = np.trapz(psd[alpha_mask], freqs[alpha_mask])
                elif params['power_method'] == 'mean':
                    alpha_power = np.mean(psd[alpha_mask]) * 4
                else:
                    alpha_power = np.sum(psd[alpha_mask])

                target_key = f"{side.lower()}_alpha"
                target_val = targets[target_key]
                ratio = alpha_power / target_val if target_val > 0 else 0

                print(f"  {side} Alpha: {alpha_power:8.2f} -> 목표: {target_val:8.2f} (비율: {ratio:.3f})")

# 실행
if __name__ == "__main__":
    tester = QuickUnifiedTest()
    best_params, best_error = tester.find_best()

    if best_params:
        tester.detailed_test(best_params)