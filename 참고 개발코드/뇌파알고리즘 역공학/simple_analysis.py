import numpy as np
import pandas as pd
import scipy.signal
import warnings
warnings.filterwarnings('ignore')

class SimpleEEGAnalysis:
    def __init__(self, sampling_rate=250):
        self.sampling_rate = sampling_rate
        # 과학자가 사용한 주파수 대역
        self.frequency_bands = {
            'delta': (0, 4),
            'theta': (4, 8),
            'alpha': (8, 12),
            'low_beta': (12, 18),
            'high_beta': (18, 30),
            'gamma': (30, 50)
        }

    def load_raw_data(self, txt_file):
        """로우 데이터 로드"""
        print(f"데이터 로딩: {txt_file}")

        data = pd.read_csv(txt_file, sep='\t', header=None)
        print(f"데이터 형태: {data.shape}")

        # 데이터 정리
        def clean_column(col):
            if col.dtype == object:
                cleaned = col.astype(str).str.replace('"', '').str.replace(',', '').str.strip()
                return pd.to_numeric(cleaned, errors='coerce').fillna(0).values
            return col.values

        eeg1 = clean_column(data.iloc[:, 0])
        eeg2 = clean_column(data.iloc[:, 1])
        ppg = clean_column(data.iloc[:, 2])

        print(f"EEG1 범위: {np.min(eeg1):.2f} ~ {np.max(eeg1):.2f}, 평균: {np.mean(eeg1):.2f}")
        print(f"EEG2 범위: {np.min(eeg2):.2f} ~ {np.max(eeg2):.2f}, 평균: {np.mean(eeg2):.2f}")
        print(f"PPG 범위: {np.min(ppg):.2f} ~ {np.max(ppg):.2f}, 평균: {np.mean(ppg):.2f}")

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
        """파워 스펙트럼 계산 - 다양한 윈도우 크기 시도"""
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
        # 다양한 피크 검출 파라미터 시도
        height_threshold = np.mean(ppg_signal) + 0.3 * np.std(ppg_signal)
        peaks, _ = scipy.signal.find_peaks(ppg_signal,
                                         height=height_threshold,
                                         distance=self.sampling_rate//5)

        if len(peaks) < 5:
            return {'bpm': 0, 'sdnn': 0, 'rmssd': 0, 'pnn50': 0}

        # R-R 간격 (밀리초)
        rr_intervals = np.diff(peaks) / self.sampling_rate * 1000

        # 이상치 제거 (너무 짧거나 긴 간격)
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

        raw_data = self.load_raw_data(filename)
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

            print(f"{side} EEG 주파수 대역별 파워:")
            for band, power in band_powers.items():
                print(f"  {band:10s}: {power:10.2f}")

        # HRV 분석
        hrv_results = self.calculate_hrv(raw_data['PPG'])
        results['HRV'] = hrv_results

        print(f"HRV 지표:")
        for metric, value in hrv_results.items():
            print(f"  {metric:6s}: {value:8.2f}")

        return results

# 테스트 실행
if __name__ == "__main__":
    analyzer = SimpleEEGAnalysis()

    # 첫 번째 파일 분석
    result1 = analyzer.analyze_file("01.이선미 숫자.txt")

    # 두 번째 파일도 분석해서 비교
    result2 = analyzer.analyze_file("02.방지수 숫자.txt")