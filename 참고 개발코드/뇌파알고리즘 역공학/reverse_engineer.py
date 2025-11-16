import numpy as np
import pandas as pd
import scipy.signal
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class ReverseEngineerEEG:
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

    def load_raw_data(self, txt_file):
        """로우 데이터 로드 (txt 파일)"""
        print(f"로우 데이터 로딩: {txt_file}")

        # 탭 구분자로 로드
        data = pd.read_csv(txt_file, sep='\t', header=None)
        print(f"데이터 형태: {data.shape}")

        # 데이터 정리 (따옴표 제거, 숫자 변환)
        def clean_column(col):
            if col.dtype == object:
                cleaned = col.astype(str).str.replace('"', '').str.replace(',', '').str.strip()
                return pd.to_numeric(cleaned, errors='coerce').fillna(0).values
            return col.values

        # EEG1, EEG2, PPG 채널 추출 (처음 3개 컬럼)
        eeg1 = clean_column(data.iloc[:, 0])
        eeg2 = clean_column(data.iloc[:, 1])
        ppg = clean_column(data.iloc[:, 2])

        print(f"EEG1 범위: {np.min(eeg1):.2f} ~ {np.max(eeg1):.2f}")
        print(f"EEG2 범위: {np.min(eeg2):.2f} ~ {np.max(eeg2):.2f}")
        print(f"PPG 범위: {np.min(ppg):.2f} ~ {np.max(ppg):.2f}")

        return {'EEG1': eeg1, 'EEG2': eeg2, 'PPG': ppg}

    def load_target_results(self, excel_file, subject_name):
        """목표 결과값 로드"""
        df = pd.read_excel(excel_file)

        # 해당 피험자 찾기
        target_row = None
        for idx, row in df.iterrows():
            if subject_name in str(row['Name']):
                target_row = row
                break

        if target_row is None:
            print(f"피험자 {subject_name}을 찾을 수 없습니다")
            return None

        print(f"목표 결과 발견: {target_row['Name']}")

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

    def preprocess_signal(self, signal, notch_freq=60, lowcut=0.5, highcut=50):
        """신호 전처리"""
        # 60Hz 노치 필터
        quality_factor = 30
        b_notch, a_notch = scipy.signal.iirnotch(notch_freq, quality_factor, self.sampling_rate)
        signal_filtered = scipy.signal.filtfilt(b_notch, a_notch, signal)

        # 대역통과 필터
        nyquist = self.sampling_rate / 2
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = scipy.signal.butter(4, [low, high], btype='band')
        signal_clean = scipy.signal.filtfilt(b, a, signal_filtered)

        return signal_clean

    def calculate_power_spectrum_welch(self, signal, nperseg_seconds=4):
        """Welch 방법으로 파워 스펙트럼 계산"""
        nperseg = int(self.sampling_rate * nperseg_seconds)
        freqs, psd = scipy.signal.welch(signal, self.sampling_rate, nperseg=nperseg, overlap=nperseg//2)
        return freqs, psd

    def extract_band_power(self, freqs, psd, freq_band):
        """주파수 대역별 파워 추출"""
        band_mask = (freqs >= freq_band[0]) & (freqs <= freq_band[1])
        band_power = np.trapz(psd[band_mask], freqs[band_mask])
        return band_power

    def calculate_hrv_metrics(self, ppg_signal):
        """HRV 지표 계산"""
        # PPG 신호에서 피크 검출
        peaks, _ = scipy.signal.find_peaks(ppg_signal,
                                         height=np.mean(ppg_signal) + 0.5*np.std(ppg_signal),
                                         distance=self.sampling_rate//4)

        # R-R 간격 계산 (밀리초)
        rr_intervals = np.diff(peaks) / self.sampling_rate * 1000

        if len(rr_intervals) < 5:
            return {'bpm': 0, 'sdnn': 0, 'rmssd': 0, 'pnn50': 0}

        # BPM 계산
        bpm = 60000 / np.mean(rr_intervals)

        # SDNN: R-R 간격의 표준편차
        sdnn = np.std(rr_intervals)

        # RMSSD: 연속 R-R 간격 차이의 제곱근 평균
        rmssd = np.sqrt(np.mean(np.diff(rr_intervals)**2))

        # pNN50: 연속 R-R 간격 차이가 50ms 이상인 비율
        nn50 = np.sum(np.abs(np.diff(rr_intervals)) > 50)
        pnn50 = nn50 / len(rr_intervals) * 100 if len(rr_intervals) > 0 else 0

        return {'bpm': bpm, 'sdnn': sdnn, 'rmssd': rmssd, 'pnn50': pnn50}

    def analyze_and_compare(self, raw_data, targets):
        """분석 후 목표값과 비교"""
        results = {}

        # EEG 채널별 분석
        for i, channel in enumerate(['EEG1', 'EEG2']):
            signal = raw_data[channel]

            # 전처리
            clean_signal = self.preprocess_signal(signal)

            # 파워 스펙트럼 계산
            freqs, psd = self.calculate_power_spectrum_welch(clean_signal)

            # 주파수 대역별 파워 계산
            band_powers = {}
            for band_name, freq_range in self.frequency_bands.items():
                power = self.extract_band_power(freqs, psd, freq_range)
                band_powers[band_name] = power

            side = 'left' if i == 0 else 'right'
            results[f'{side}_powers'] = band_powers

        # HRV 분석
        hrv_results = self.calculate_hrv_metrics(raw_data['PPG'])
        results['hrv'] = hrv_results

        # 목표값과 비교
        print("\n=== 분석 결과 vs 목표값 비교 ===")

        # EEG 파워 비교
        for side in ['left', 'right']:
            print(f"\n{side.upper()} EEG:")
            target_prefix = side
            our_powers = results[f'{side}_powers']

            bands_map = {
                'delta': f'{target_prefix}_delta',
                'theta': f'{target_prefix}_theta',
                'alpha': f'{target_prefix}_alpha',
                'low_beta': f'{target_prefix}_low_beta',
                'high_beta': f'{target_prefix}_high_beta',
                'gamma': f'{target_prefix}_gamma'
            }

            for band, target_key in bands_map.items():
                our_value = our_powers[band]
                target_value = targets[target_key]
                ratio = our_value / target_value if target_value != 0 else 0
                print(f"  {band:10s}: {our_value:8.2f} -> 목표: {target_value:8.2f} (비율: {ratio:.3f})")

        # HRV 비교
        print(f"\nHRV:")
        hrv_metrics = ['bpm', 'sdnn', 'rmssd', 'pnn50']
        for metric in hrv_metrics:
            our_value = hrv_results[metric]
            target_value = targets[metric]
            ratio = our_value / target_value if target_value != 0 else 0
            print(f"  {metric:6s}: {our_value:8.2f} -> 목표: {target_value:8.2f} (비율: {ratio:.3f})")

        return results

# 테스트 실행
if __name__ == "__main__":
    analyzer = ReverseEngineerEEG()

    # 첫 번째 파일로 테스트
    raw_file = "01.이선미 숫자.txt"
    results_file = "01.Results_0128.xlsx"
    subject_name = "이선미"

    print("=== EEG 역공학 분석 시작 ===")

    # 로우 데이터 로드
    raw_data = analyzer.load_raw_data(raw_file)

    if raw_data:
        # 목표 결과 로드
        targets = analyzer.load_target_results(results_file, subject_name)

        if targets:
            # 분석 및 비교
            results = analyzer.analyze_and_compare(raw_data, targets)
        else:
            print("목표값을 찾을 수 없습니다.")
    else:
        print("로우 데이터 로드 실패")