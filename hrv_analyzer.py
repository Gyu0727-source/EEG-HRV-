"""
EEG 실시간 분석 프로젝트 - HRV 분석 모듈

HeartPy 기반 심박변이도 분석
- Time Domain: SDNN, RMSSD, pNN50 등
- Frequency Domain: LF, HF, LF/HF ratio

참고:
- 마음력 알고리즘 템플릿
- HRV 연구 논문들
"""

import numpy as np
import config

try:
    import heartpy as hp
    HEARTPY_AVAILABLE = True
except ImportError:
    HEARTPY_AVAILABLE = False
    print("Warning: heartpy 라이브러리가 설치되어 있지 않습니다.")
    print("HRV 분석을 사용하려면 다음 명령어로 설치하세요:")
    print("pip install heartpy")


def assess_ppg_quality(ppg_signal, sample_rate=250):
    """
    PPG 신호 품질 평가

    품질이 낮으면 BPM 200+ 같은 이상한 값이 나올 수 있음
    품질 등급에 따라 HRV 분석 진행 여부 결정

    Parameters:
    -----------
    ppg_signal : ndarray
        PPG 신호
    sample_rate : int
        샘플링 레이트

    Returns:
    --------
    quality_report : dict
        {
            'grade': str,  # 'excellent', 'good', 'poor'
            'score': float,  # 0-100 점수
            'issues': list,  # 발견된 문제들
            'can_analyze': bool,  # HRV 분석 가능 여부
            'message': str  # 품질 평가 메시지
        }
    """
    issues = []
    score = 100
    min_duration = 30  # 최소 30초 필요

    # 1. 기본 체크: 신호 길이
    duration = len(ppg_signal) / sample_rate
    if duration < min_duration:
        issues.append(f"신호 길이 부족 ({duration:.1f}초 < {min_duration}초)")
        score -= 50

    # 2. 결측치 및 이상값 체크
    nan_ratio = np.isnan(ppg_signal).sum() / len(ppg_signal)
    if nan_ratio > 0.01:  # 1% 이상 NaN
        issues.append(f"결측치 과다 ({nan_ratio*100:.1f}%)")
        score -= 30

    inf_count = np.isinf(ppg_signal).sum()
    if inf_count > 0:
        issues.append(f"무한대 값 감지 ({inf_count}개)")
        score -= 30

    # 유효한 데이터만 추출
    valid_signal = ppg_signal[~np.isnan(ppg_signal) & ~np.isinf(ppg_signal)]

    if len(valid_signal) < sample_rate * 10:  # 최소 10초 유효 데이터
        return {
            'grade': 'poor',
            'score': 0,
            'issues': issues + ["유효 데이터 부족 (<10초)"],
            'can_analyze': False,
            'message': "PPG 데이터 품질이 매우 낮습니다. 센서 접촉 불량 또는 측정 오류가 의심됩니다."
        }

    # 3. 신호 범위 체크
    signal_std = np.std(valid_signal)
    signal_mean = np.mean(valid_signal)

    if signal_std < 0.1:  # 표준편차가 너무 작음
        issues.append(f"신호 변동 없음 (STD={signal_std:.3f})")
        score -= 40

    # 4. 변동 계수 (Coefficient of Variation)
    if abs(signal_mean) > 0.01:
        cv = signal_std / abs(signal_mean)
        if cv < 0.01:  # 변동이 거의 없음
            issues.append(f"신호가 너무 일정함 (CV={cv:.3f})")
            score -= 30
    else:
        issues.append("신호 평균이 0에 가까움 (센서 오류 의심)")
        score -= 40

    # 5. 이상치 비율 체크 (3 표준편차 벗어난 값)
    if signal_std > 0:
        z_scores = np.abs((valid_signal - signal_mean) / signal_std)
        outlier_ratio = (z_scores > 3).sum() / len(valid_signal)

        if outlier_ratio > 0.05:  # 5% 이상 이상치
            issues.append(f"이상치 과다 ({outlier_ratio*100:.1f}%)")
            score -= 20

    # 6. 신호 범위 체크
    signal_range = np.max(valid_signal) - np.min(valid_signal)
    if signal_range < 1.0:  # 범위가 너무 작음
        issues.append(f"신호 범위 부족 (range={signal_range:.2f})")
        score -= 20

    # 점수 범위 제한
    score = max(0, min(100, score))

    # 등급 결정
    if score >= 70:
        grade = 'excellent'
        can_analyze = True
        message = "PPG 데이터 품질이 우수합니다. HRV 분석을 진행합니다."
    elif score >= 40:
        grade = 'good'
        can_analyze = True
        message = "PPG 데이터 품질이 양호합니다. HRV 분석을 진행하나 일부 부정확할 수 있습니다."
    else:
        grade = 'poor'
        can_analyze = False
        message = "PPG 데이터 품질이 낮아 HRV 분석을 수행하지 않습니다. 센서 재부착 후 재측정을 권장합니다."

    return {
        'grade': grade,
        'score': score,
        'issues': issues,
        'can_analyze': can_analyze,
        'message': message,
        'stats': {
            'duration': duration,
            'mean': signal_mean,
            'std': signal_std,
            'valid_ratio': len(valid_signal) / len(ppg_signal)
        }
    }


def analyze_hrv(ppg_signal, sample_rate=250):
    """
    HRV (Heart Rate Variability) 분석

    품질 검사 후 분석 진행 여부 결정

    Parameters:
    -----------
    ppg_signal : ndarray
        PPG (Photoplethysmography) 신호 또는 ECG R-peak 간격
    sample_rate : int
        샘플링 레이트 (Hz)

    Returns:
    --------
    hrv_metrics : dict
        {
            'time_domain': {...},  # Time domain 지표
            'frequency_domain': {...},  # Frequency domain 지표
            'quality': {...},  # 품질 평가 결과
            'status': str  # 'success', 'failed', 'poor_quality'
        }
    """
    # 1. PPG 품질 검사 먼저 수행
    quality_report = assess_ppg_quality(ppg_signal, sample_rate)

    if not quality_report['can_analyze']:
        # 품질이 낮아서 분석 불가
        return {
            'status': 'poor_quality',
            'quality': quality_report,
            'time_domain': {},
            'frequency_domain': {},
            'message': quality_report['message']
        }

    if not HEARTPY_AVAILABLE:
        return {
            'status': 'failed',
            'error': 'heartpy not installed',
            'quality': quality_report,
            'time_domain': {},
            'frequency_domain': {}
        }

    if not config.HRV_ENABLED:
        return {
            'status': 'disabled',
            'quality': quality_report,
            'time_domain': {},
            'frequency_domain': {}
        }

    try:
        # 피크 강조 (노이즈 제거)
        enhanced = hp.enhance_peaks(ppg_signal, iterations=1)

        # HRV 분석 실행
        wd, m = hp.process(
            enhanced,
            sample_rate=sample_rate,
            calc_freq=True
        )

        # Time Domain 지표 추출
        time_domain = extract_time_domain(m)

        # Frequency Domain 지표 추출
        frequency_domain = extract_frequency_domain(m)

        return {
            'status': 'success',
            'quality': quality_report,  # 품질 정보 포함
            'time_domain': time_domain,
            'frequency_domain': frequency_domain,
            'working_data': wd,  # 원시 작업 데이터
            'measures': m        # 전체 측정값
        }

    except Exception as e:
        print(f"HRV 분석 중 오류 발생: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'quality': quality_report,  # 품질 정보 포함
            'time_domain': {},
            'frequency_domain': {}
        }


def extract_time_domain(measures):
    """
    Time Domain 지표 추출

    지표 설명:
    - BPM: 분당 심박수 (Beats Per Minute)
    - IBI: 심박 간격 (Interbeat Interval)
    - SDNN: RR 간격의 표준편차 (자율신경 전체 활성)
    - RMSSD: 연속 RR 간격 차이의 제곱근 평균 (부교감신경 활성)
    - pNN20/pNN50: 20ms/50ms 이상 차이나는 비율 (부교감신경)
    - MAD: 중위 절대 편차

    Parameters:
    -----------
    measures : dict
        HeartPy가 계산한 측정값

    Returns:
    --------
    time_metrics : dict
        Time domain HRV 지표
    """
    time_metrics = {}

    for metric in config.HRV_TIME_DOMAIN:
        if metric in measures:
            time_metrics[metric] = measures[metric]
        else:
            time_metrics[metric] = None

    # 추가 통계 계산
    if 'ibi' in measures and measures['ibi'] is not None:
        time_metrics['ibi_mean'] = measures['ibi']
        time_metrics['ibi_std'] = measures.get('sdnn', None)

    return time_metrics


def extract_frequency_domain(measures):
    """
    Frequency Domain 지표 추출

    지표 설명:
    - LF (Low Frequency, 0.05-0.15 Hz): 교감신경 + 부교감신경
    - HF (High Frequency, 0.15-0.5 Hz): 부교감신경 (호흡 동조성)
    - LF/HF ratio: 자율신경 균형 지표
      - 높음: 교감신경 우세 (스트레스, 긴장)
      - 낮음: 부교감신경 우세 (이완, 안정)

    Parameters:
    -----------
    measures : dict
        HeartPy가 계산한 측정값

    Returns:
    --------
    freq_metrics : dict
        Frequency domain HRV 지표
    """
    freq_metrics = {}

    for metric in config.HRV_FREQUENCY_DOMAIN:
        if metric in measures:
            freq_metrics[metric] = measures[metric]
        else:
            freq_metrics[metric] = None

    # LF/HF ratio 해석
    if 'lf_hf_ratio' in freq_metrics and freq_metrics['lf_hf_ratio'] is not None:
        ratio = freq_metrics['lf_hf_ratio']
        if ratio > 2.0:
            interpretation = 'high_stress'  # 교감신경 우세
        elif ratio > 1.0:
            interpretation = 'moderate_stress'
        elif ratio > 0.5:
            interpretation = 'balanced'  # 균형
        else:
            interpretation = 'relaxed'  # 부교감신경 우세

        freq_metrics['lf_hf_interpretation'] = interpretation

    return freq_metrics


def calculate_hrv_timeseries(ppg_signal, sample_rate=250, window_size=60, overlap=0.5):
    """
    시계열 HRV 분석 (2초 윈도우 EEG와 유사한 방식)

    Parameters:
    -----------
    ppg_signal : ndarray
        PPG 신호
    sample_rate : int
        샘플링 레이트 (Hz)
    window_size : int
        윈도우 크기 (초) - HRV는 최소 60초 권장
    overlap : float
        오버랩 비율

    Returns:
    --------
    timeseries_hrv : dict
        {
            'time': ndarray,
            'bpm': ndarray,
            'sdnn': ndarray,
            'rmssd': ndarray,
            'lf_hf_ratio': ndarray
        }
    """
    if not HEARTPY_AVAILABLE:
        return None

    window_samples = int(sample_rate * window_size)
    step_samples = int(window_samples * (1 - overlap))
    signal_length = len(ppg_signal)
    n_windows = (signal_length - window_samples) // step_samples + 1

    # 결과 저장
    time_array = []
    bpm_array = []
    sdnn_array = []
    rmssd_array = []
    lf_hf_array = []

    for i in range(n_windows):
        start_idx = i * step_samples
        end_idx = start_idx + window_samples

        window_signal = ppg_signal[start_idx:end_idx]
        center_time = (start_idx + window_samples / 2) / sample_rate

        try:
            # HRV 분석
            enhanced = hp.enhance_peaks(window_signal, iterations=1)
            wd, m = hp.process(enhanced, sample_rate=sample_rate, calc_freq=True)

            time_array.append(center_time)
            bpm_array.append(m.get('bpm', np.nan))
            sdnn_array.append(m.get('sdnn', np.nan))
            rmssd_array.append(m.get('rmssd', np.nan))
            lf_hf_array.append(m.get('lf_hf_ratio', np.nan))

        except Exception as e:
            # 분석 실패 시 NaN 추가
            time_array.append(center_time)
            bpm_array.append(np.nan)
            sdnn_array.append(np.nan)
            rmssd_array.append(np.nan)
            lf_hf_array.append(np.nan)

    return {
        'time': np.array(time_array),
        'bpm': np.array(bpm_array),
        'sdnn': np.array(sdnn_array),
        'rmssd': np.array(rmssd_array),
        'lf_hf_ratio': np.array(lf_hf_array)
    }


def calculate_rsa(ibi_array, respiration_rate=None):
    """
    RSA (Respiratory Sinus Arrhythmia) 계산

    호흡성 동성 부정맥 - 호흡에 따른 심박 변화
    부교감신경 활성도의 지표

    Parameters:
    -----------
    ibi_array : ndarray
        IBI (Interbeat Interval) 배열
    respiration_rate : float, optional
        호흡 속도 (회/분)

    Returns:
    --------
    rsa_metrics : dict
        {
            'rsa_amplitude': float,  # RSA 진폭
            'rsa_frequency': float   # RSA 주파수
        }
    """
    if len(ibi_array) < 10:
        return {'rsa_amplitude': None, 'rsa_frequency': None}

    # FFT로 주기적 패턴 찾기
    fft = np.fft.fft(ibi_array - np.mean(ibi_array))
    power = np.abs(fft) ** 2
    freqs = np.fft.fftfreq(len(ibi_array))

    # 호흡 주파수 대역 (0.15-0.5 Hz = HF 대역)
    hf_mask = (freqs >= 0.15) & (freqs <= 0.5)
    if np.any(hf_mask):
        hf_power = power[hf_mask]
        hf_freqs = freqs[hf_mask]

        # 최대 파워의 주파수
        max_idx = np.argmax(hf_power)
        rsa_frequency = hf_freqs[max_idx]
        rsa_amplitude = np.sqrt(hf_power[max_idx])

        return {
            'rsa_amplitude': float(rsa_amplitude),
            'rsa_frequency': float(rsa_frequency),
            'rsa_power': float(hf_power[max_idx])
        }
    else:
        return {
            'rsa_amplitude': None,
            'rsa_frequency': None,
            'rsa_power': None
        }
