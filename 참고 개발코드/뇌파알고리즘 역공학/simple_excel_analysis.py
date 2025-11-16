import numpy as np
import pandas as pd
import scipy.signal
import warnings
warnings.filterwarnings('ignore')

class SimpleExcelAnalysis:
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

    def load_excel_data(self, excel_file):
        """Excel 로우 데이터 로드"""
        print(f"Excel 데이터 로딩: {excel_file}")

        data = pd.read_excel(excel_file, header=None)
        print(f"데이터 형태: {data.shape}")
        print(f"첫 5행 미리보기:")
        print(data.head())

        # 모든 컬럼 확인
        print(f"\n컬럼별 데이터 타입:")
        for i in range(min(data.shape[1], 5)):
            col_data = data.iloc[:, i]
            print(f"  컬럼 {i}: {col_data.dtype}, 첫 값: {col_data.iloc[0]}")

        # EEG와 PPG 데이터 추출
        eeg1 = pd.to_numeric(data.iloc[:, 0], errors='coerce').fillna(0).values
        eeg2 = pd.to_numeric(data.iloc[:, 1], errors='coerce').fillna(0).values

        # PPG는 3번째 컬럼 또는 다른 컬럼일 수 있음
        ppg_candidates = []
        for i in range(2, min(data.shape[1], 6)):
            ppg_candidate = pd.to_numeric(data.iloc[:, i], errors='coerce').fillna(0).values
            ppg_candidates.append((i, ppg_candidate))
            print(f"PPG 후보 컬럼 {i}: 범위 {np.min(ppg_candidate):.2f} ~ {np.max(ppg_candidate):.2f}, 평균 {np.mean(ppg_candidate):.2f}")

        # 가장 변동이 큰 컬럼을 PPG로 선택
        best_ppg_col = 2
        best_ppg_std = 0
        for col_idx, ppg_data in ppg_candidates:
            std_val = np.std(ppg_data)
            if std_val > best_ppg_std:
                best_ppg_std = std_val
                best_ppg_col = col_idx

        ppg = ppg_candidates[best_ppg_col - 2][1]
        print(f"\nPPG로 선택된 컬럼: {best_ppg_col} (표준편차: {best_ppg_std:.2f})")

        print(f"\n최종 데이터:")
        print(f"EEG1: {np.min(eeg1):.2f} ~ {np.max(eeg1):.2f}, mean={np.mean(eeg1):.2f}")
        print(f"EEG2: {np.min(eeg2):.2f} ~ {np.max(eeg2):.2f}, mean={np.mean(eeg2):.2f}")
        print(f"PPG: {np.min(ppg):.2f} ~ {np.max(ppg):.2f}, mean={np.mean(ppg):.2f}")

        return {'EEG1': eeg1, 'EEG2': eeg2, 'PPG': ppg}

    def preprocess_signal(self, signal):
        """신호 전처리"""
        # 60Hz 노치 필터
        b_notch, a_notch = scipy.signal.iirnotch(60, 30, self.sampling_rate)
        signal_filtered = scipy.signal.filtfilt(b_notch, a_notch, signal)

        # 0.5-50Hz 대역통과 필터
        nyquist = self.sampling_rate / 2
        b, a = scipy.signal.butter(4, [0.5/nyquist, 50/nyquist], btype='band')
        signal_clean = scipy.signal.filtfilt(b, a, signal_filtered)

        return signal_clean

    def calculate_power_spectrum(self, signal, nperseg_factor=4):
        """파워 스펙트럼 계산"""
        nperseg = int(self.sampling_rate * nperseg_factor)
        freqs, psd = scipy.signal.welch(signal, self.sampling_rate,
                                      nperseg=nperseg,
                                      noverlap=nperseg//2)
        return freqs, psd

    def extract_band_power(self, freqs, psd, freq_band):
        """주파수 대역별 파워"""
        band_mask = (freqs >= freq_band[0]) & (freqs <= freq_band[1])
        return np.trapz(psd[band_mask], freqs[band_mask])

    def calculate_hrv(self, ppg_signal):
        """HRV 계산"""
        if np.max(ppg_signal) - np.min(ppg_signal) < 0.1:
            print("PPG 신호가 평평함 - HRV 계산 불가")
            return {'bpm': 0, 'sdnn': 0, 'rmssd': 0, 'pnn50': 0}

        # 피크 검출
        height_threshold = np.mean(ppg_signal) + 0.3 * np.std(ppg_signal)
        peaks, _ = scipy.signal.find_peaks(ppg_signal,
                                         height=height_threshold,
                                         distance=self.sampling_rate//5)

        print(f"검출된 피크 수: {len(peaks)}")

        if len(peaks) < 5:
            return {'bpm': 0, 'sdnn': 0, 'rmssd': 0, 'pnn50': 0}

        # R-R 간격 (밀리초)
        rr_intervals = np.diff(peaks) / self.sampling_rate * 1000

        # 이상치 제거
        rr_clean = rr_intervals[(rr_intervals > 300) & (rr_intervals < 2000)]

        if len(rr_clean) < 3:
            return {'bpm': 0, 'sdnn': 0, 'rmssd': 0, 'pnn50': 0}

        bpm = 60000 / np.mean(rr_clean)
        sdnn = np.std(rr_clean)
        rmssd = np.sqrt(np.mean(np.diff(rr_clean)**2))
        nn50 = np.sum(np.abs(np.diff(rr_clean)) > 50)
        pnn50 = nn50 / len(rr_clean) * 100

        return {'bpm': bpm, 'sdnn': sdnn, 'rmssd': rmssd, 'pnn50': pnn50}

    def analyze_file(self, filename):
        """파일 분석"""
        print(f"\n=== {filename} 분석 ===")

        raw_data = self.load_excel_data(filename)
        if not raw_data:
            return None

        results = {}

        # EEG 분석
        for i, channel in enumerate(['EEG1', 'EEG2']):
            signal = raw_data[channel]
            clean_signal = self.preprocess_signal(signal)

            # 파워 스펙트럼 계산
            freqs, psd = self.calculate_power_spectrum(clean_signal)

            # 주파수 대역별 파워
            band_powers = {}
            for band_name, freq_range in self.frequency_bands.items():
                power = self.extract_band_power(freqs, psd, freq_range)
                band_powers[band_name] = power

            side = 'LEFT' if i == 0 else 'RIGHT'
            results[side] = band_powers

            print(f"\n{side} EEG 주파수 대역별 파워:")
            for band, power in band_powers.items():
                print(f"  {band:10s}: {power:10.2f}")

        # HRV 분석
        hrv_results = self.calculate_hrv(raw_data['PPG'])
        results['HRV'] = hrv_results

        print(f"\nHRV 지표:")
        for metric, value in hrv_results.items():
            print(f"  {metric:6s}: {value:8.2f}")

        return results

# 테스트 실행
if __name__ == "__main__":
    analyzer = SimpleExcelAnalysis()

    # 분석할 파일들
    files_to_analyze = [
        "01.이선미 숫자.xlsx",
        "01.이선미 잔상.xlsx",
        "01.이선미 호흡.xlsx"
    ]

    results = {}
    for filename in files_to_analyze:
        try:
            result = analyzer.analyze_file(filename)
            if result:
                results[filename] = result
        except Exception as e:
            print(f"{filename} 분석 실패: {e}")

    # 결과 요약
    print(f"\n=== 전체 결과 요약 ===")
    for filename, result in results.items():
        print(f"\n{filename}:")
        if 'LEFT' in result:
            print(f"  LEFT Alpha: {result['LEFT']['alpha']:.2f}")
            print(f"  RIGHT Alpha: {result['RIGHT']['alpha']:.2f}")
        if 'HRV' in result:
            print(f"  BPM: {result['HRV']['bpm']:.2f}")