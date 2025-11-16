"""
EEG 실시간 분석 프로젝트 - 뇌파 분석 모듈

핵심 기능:
1. 전처리 (60Hz notch, 0.5-50Hz bandpass)
2. 2초 윈도우 기반 시계열 분석
3. Savitzky-Golay 스무딩
4. 변화점 자동 감지
"""

import numpy as np
import scipy.signal
from scipy.signal import savgol_filter
import config


def preprocess_signal(signal):
    """
    신호 전처리: 노이즈 제거 및 필터링
    (기존 역공학 알고리즘과 동일한 방법 사용)

    Parameters:
    -----------
    signal : ndarray
        원시 EEG 신호

    Returns:
    --------
    processed : ndarray
        전처리된 신호
    """
    processed = signal.copy()

    # 1. 60Hz 노치 필터 (전원선 노이즈 제거)
    b_notch, a_notch = scipy.signal.iirnotch(
        config.NOTCH_FREQUENCY,
        config.NOTCH_QUALITY,
        config.SAMPLING_RATE
    )
    processed = scipy.signal.filtfilt(b_notch, a_notch, processed)

    # 2. 0.5-50Hz 대역통과 필터
    nyquist = config.SAMPLING_RATE / 2
    low = config.LOWCUT_FREQUENCY / nyquist
    high = config.HIGHCUT_FREQUENCY / nyquist
    b, a = scipy.signal.butter(
        config.FILTER_ORDER,
        [low, high],
        btype='band'
    )
    processed = scipy.signal.filtfilt(b, a, processed)

    return processed


def compute_band_power_timeseries(fp1, fp2):
    """
    2초 윈도우 기반 시계열 분석

    핵심 개념:
    - 윈도우 크기: 2초 (500 샘플 @ 250Hz)
    - 오버랩: 50% (1초, 250 샘플)
    - 결과: 1초마다 새로운 파워 값 생성

    예: 15분(900초) 측정 → 약 900개 데이터 포인트

    Parameters:
    -----------
    fp1, fp2 : ndarray
        전처리된 Fp1, Fp2 신호

    Returns:
    --------
    result : dict
        {
            'time': 시간 배열 (초),
            'band_powers': {
                'delta': 시계열 파워 배열,
                'theta': ...,
                ...
            }
        }
    """
    # 파라미터 계산
    window_samples = int(config.SAMPLING_RATE * config.WINDOW_SIZE)  # 2초 = 500 샘플
    step_samples = int(window_samples * (1 - config.OVERLAP))  # 50% 오버랩 = 250 샘플

    # 신호 길이
    signal_length = len(fp1)

    # 윈도우 개수 계산
    n_windows = (signal_length - window_samples) // step_samples + 1

    # 시간 배열 생성 (각 윈도우의 중심 시간)
    time_array = np.array([
        (i * step_samples + window_samples / 2) / config.SAMPLING_RATE
        for i in range(n_windows)
    ])

    # 주파수 대역별 파워 저장
    band_powers = {band: [] for band in config.FREQUENCY_BANDS.keys()}
    fp1_powers = {band: [] for band in config.FREQUENCY_BANDS.keys()}
    fp2_powers = {band: [] for band in config.FREQUENCY_BANDS.keys()}

    # 각 윈도우에서 파워 계산
    for i in range(n_windows):
        start_idx = i * step_samples
        end_idx = start_idx + window_samples

        # 윈도우 추출
        fp1_window = fp1[start_idx:end_idx]
        fp2_window = fp2[start_idx:end_idx]

        # 파워 스펙트럼 계산 (Welch 방법)
        freqs1, psd1 = scipy.signal.welch(
            fp1_window,
            config.SAMPLING_RATE,
            nperseg=len(fp1_window),
            window='hann'
        )

        freqs2, psd2 = scipy.signal.welch(
            fp2_window,
            config.SAMPLING_RATE,
            nperseg=len(fp2_window),
            window='hann'
        )

        # 주파수 대역별 파워 추출 (양쪽 평균)
        for band_name, (fmin, fmax) in config.FREQUENCY_BANDS.items():
            # Fp1 파워
            mask1 = (freqs1 >= fmin) & (freqs1 <= fmax)
            power1 = np.trapz(psd1[mask1], freqs1[mask1]) if np.any(mask1) else 0

            # Fp2 파워
            mask2 = (freqs2 >= fmin) & (freqs2 <= fmax)
            power2 = np.trapz(psd2[mask2], freqs2[mask2]) if np.any(mask2) else 0

            # 개별 파워 저장 (좌뇌/우뇌 균형 분석용)
            fp1_powers[band_name].append(power1)
            fp2_powers[band_name].append(power2)

            # 평균 파워 (양쪽 전극의 평균)
            avg_power = (power1 + power2) / 2
            band_powers[band_name].append(avg_power)

    # 리스트를 numpy 배열로 변환
    for band in band_powers:
        band_powers[band] = np.array(band_powers[band])
        fp1_powers[band] = np.array(fp1_powers[band])
        fp2_powers[band] = np.array(fp2_powers[band])

    return {
        'time': time_array,
        'band_powers': band_powers,
        'fp1_powers': fp1_powers,
        'fp2_powers': fp2_powers
    }


def smooth_signal(signal):
    """
    Savitzky-Golay 필터를 사용한 신호 스무딩

    목적: 자글자글한 원본 데이터를 부드러운 추세선으로 변환

    Parameters:
    -----------
    signal : ndarray
        원본 시계열 데이터

    Returns:
    --------
    smoothed : ndarray
        스무딩된 시계열 데이터
    """
    # 윈도우 길이가 신호보다 길면 조정
    window_length = min(config.SMOOTHING_WINDOW, len(signal))

    # 윈도우 길이는 홀수여야 함
    if window_length % 2 == 0:
        window_length -= 1

    # 윈도우 길이가 polyorder보다 커야 함
    if window_length <= config.SMOOTHING_POLY:
        return signal  # 스무딩 불가능하면 원본 반환

    smoothed = savgol_filter(
        signal,
        window_length=window_length,
        polyorder=config.SMOOTHING_POLY
    )

    return smoothed


def detect_significant_changes(smoothed_signal, n_changes=3):
    """
    통계적으로 유의미한 변화점 감지

    방법:
    1. 2차 미분으로 곡률 계산
    2. 곡률의 절댓값이 큰 지점을 변화점 후보로 선택
    3. 너무 가까운 변화점 제거 (최소 거리 유지)
    4. 상위 n_changes개만 선택

    Parameters:
    -----------
    smoothed_signal : ndarray
        스무딩된 시계열 데이터
    n_changes : int
        최대 변화점 개수

    Returns:
    --------
    change_points : list of int
        변화점 인덱스
    change_types : list of str
        변화 방향 ('increase', 'decrease', 'stable')
    """
    # 2차 미분 (곡률)
    first_derivative = np.gradient(smoothed_signal)
    second_derivative = np.gradient(first_derivative)

    # 곡률의 절댓값
    curvature = np.abs(second_derivative)

    # 최소 거리 계산 (전체 길이의 일정 비율)
    min_distance = int(len(smoothed_signal) * config.MIN_DISTANCE_RATIO)

    # 변화점 후보 찾기
    candidate_indices = []
    candidate_curvatures = []

    for i in range(min_distance, len(curvature) - min_distance):
        # 지역 최대값 찾기
        if curvature[i] > config.CURVATURE_THRESHOLD:
            # 너무 가까운 후보가 있는지 확인
            too_close = False
            for existing_idx in candidate_indices:
                if abs(i - existing_idx) < min_distance:
                    # 기존 후보와 비교하여 더 큰 것만 유지
                    existing_pos = candidate_indices.index(existing_idx)
                    if curvature[i] > candidate_curvatures[existing_pos]:
                        candidate_indices[existing_pos] = i
                        candidate_curvatures[existing_pos] = curvature[i]
                    too_close = True
                    break

            if not too_close:
                candidate_indices.append(i)
                candidate_curvatures.append(curvature[i])

    # 곡률이 큰 순서로 정렬하여 상위 n개 선택
    if len(candidate_indices) > n_changes:
        sorted_pairs = sorted(zip(candidate_curvatures, candidate_indices), reverse=True)
        candidate_indices = [idx for _, idx in sorted_pairs[:n_changes]]

    # 시간 순서로 정렬
    change_points = sorted(candidate_indices)

    # 변화 방향 판단
    change_types = []
    for cp in change_points:
        # 변화점 전후의 평균 비교
        window = min_distance // 2
        before_avg = np.mean(smoothed_signal[max(0, cp-window):cp])
        after_avg = np.mean(smoothed_signal[cp:min(len(smoothed_signal), cp+window)])

        diff = after_avg - before_avg
        rel_diff = diff / before_avg if before_avg != 0 else 0

        if rel_diff > 0.05:  # 5% 이상 증가
            change_types.append('increase')
        elif rel_diff < -0.05:  # 5% 이상 감소
            change_types.append('decrease')
        else:
            change_types.append('stable')

    return change_points, change_types


def analyze_eeg(raw_file, info):
    """
    EEG 원시 데이터 전체 분석 파이프라인

    Parameters:
    -----------
    raw_file : str
        원시 데이터 파일 경로
    info : dict
        파일 정보

    Returns:
    --------
    result : dict
        {
            'time': 시간 배열,
            'raw': {band: raw_data, ...},
            'smooth': {band: smoothed_data, ...},
            'change_points': {band: [cp1, cp2, ...], ...},
            'change_types': {band: [type1, type2, ...], ...},
            'duration': 측정 시간(초),
            'sampling_rate': 샘플링 레이트
        }
    """
    # 1. 데이터 로드
    from utils import load_raw_data
    data = load_raw_data(raw_file)

    # 2. 전처리
    fp1_clean = preprocess_signal(data['Fp1'])
    fp2_clean = preprocess_signal(data['Fp2'])

    # 3. 2초 윈도우 시계열 분석
    timeseries = compute_band_power_timeseries(fp1_clean, fp2_clean)

    # 4. 스무딩
    band_powers_smooth = {}
    fp1_powers_smooth = {}
    fp2_powers_smooth = {}
    for band, values in timeseries['band_powers'].items():
        band_powers_smooth[band] = smooth_signal(values)
        fp1_powers_smooth[band] = smooth_signal(timeseries['fp1_powers'][band])
        fp2_powers_smooth[band] = smooth_signal(timeseries['fp2_powers'][band])

    # 5. 변화점 감지
    change_points = {}
    change_types = {}
    for band, values in band_powers_smooth.items():
        cp, ct = detect_significant_changes(values, n_changes=config.N_CHANGE_POINTS)
        change_points[band] = cp
        change_types[band] = ct

    # 6. 비율 지표 계산 (비웨이브 명상/집중 알고리즘)
    ratio_metrics = calculate_ratio_metrics(band_powers_smooth)

    # 7. HRV 지표 계산
    hrv_metrics = calculate_hrv_metrics(fp1_clean, fp2_clean)

    return {
        'time': timeseries['time'],
        'raw': timeseries['band_powers'],
        'smooth': band_powers_smooth,
        'fp1_powers': fp1_powers_smooth,
        'fp2_powers': fp2_powers_smooth,
        'change_points': change_points,
        'change_types': change_types,
        'ratio_metrics': ratio_metrics,
        'hrv_metrics': hrv_metrics,
        'duration': data['duration'],
        'sampling_rate': data['sampling_rate'],
        'info': info
    }


def calculate_ratio_metrics(band_powers_smooth):
    """
    비웨이브 명상/집중 알고리즘에 따른 비율 지표 계산

    핵심 지표:
    1. Theta/Alpha ratio: 안정화 지표 (명상 깊이)
       - Theta > Alpha: 깊은 안정(명상) 상태
       - Alpha > Theta: 편안한 각성 상태

    2. Gamma/Theta slope: 집중 vs 명상 지표
       - 명상 기반 안정화: 기울기 커짐
       - 주의집중 활성화: Gamma 증가하며 기울기 작아짐

    Parameters:
    -----------
    band_powers_smooth : dict
        스무딩된 주파수 대역별 파워 딕셔너리

    Returns:
    --------
    metrics : dict
        {
            'theta_alpha_ratio': {
                'timeseries': ndarray,  # 시계열 비율
                'mean': float,          # 평균 비율
                'trend': str            # 추세 ('increasing', 'decreasing', 'stable')
            },
            'gamma_theta_slope': {
                'timeseries': ndarray,  # 시계열 기울기
                'mean': float,          # 평균 기울기
                'interpretation': str   # 해석 ('meditation', 'concentration')
            }
        }
    """
    metrics = {}

    # 1. Theta/Alpha ratio 계산
    theta = band_powers_smooth['theta']
    alpha = band_powers_smooth['alpha']

    # 0으로 나누는 것 방지
    alpha_safe = np.where(alpha == 0, 1e-10, alpha)
    theta_alpha_ratio = theta / alpha_safe

    # 추세 분석
    trend_slope = np.polyfit(range(len(theta_alpha_ratio)), theta_alpha_ratio, 1)[0]
    if trend_slope > 0.01:
        trend = 'increasing'  # 명상 상태로 진입
    elif trend_slope < -0.01:
        trend = 'decreasing'  # 각성 상태로 진입
    else:
        trend = 'stable'

    metrics['theta_alpha_ratio'] = {
        'timeseries': theta_alpha_ratio,
        'mean': np.mean(theta_alpha_ratio),
        'median': np.median(theta_alpha_ratio),
        'std': np.std(theta_alpha_ratio),
        'trend': trend,
        'trend_slope': trend_slope
    }

    # 2. Gamma/Theta slope 계산
    gamma = band_powers_smooth['gamma']

    # 0으로 나누는 것 방지
    theta_safe = np.where(theta == 0, 1e-10, theta)
    gamma_theta_ratio = gamma / theta_safe

    # 기울기 계산 (시간에 따른 변화율)
    slope = np.gradient(gamma_theta_ratio)
    mean_slope = np.mean(slope)

    # 해석
    if mean_slope > 0:
        interpretation = 'concentration'  # 주의집중 활성화 (Gamma 증가)
    else:
        interpretation = 'meditation'     # 명상 기반 안정화

    metrics['gamma_theta_slope'] = {
        'timeseries': gamma_theta_ratio,
        'slope': slope,
        'mean_ratio': np.mean(gamma_theta_ratio),
        'mean_slope': mean_slope,
        'interpretation': interpretation
    }

    # 3. Beta-Gamma 패턴 분석 (비웨이브 알고리즘)
    low_beta = band_powers_smooth['low_beta']
    high_beta = band_powers_smooth['high_beta']

    # 베이스라인 패턴: High beta > Low beta > Gamma
    baseline_pattern = {
        'low_beta_mean': np.mean(low_beta),
        'high_beta_mean': np.mean(high_beta),
        'gamma_mean': np.mean(gamma)
    }

    # 집중 수행 패턴 감지: Gamma > Low beta
    concentration_periods = gamma > low_beta
    concentration_ratio = np.sum(concentration_periods) / len(gamma)

    # 명상 수행 패턴 감지: Gamma > High beta > Low beta
    meditation_periods = (gamma > high_beta) & (high_beta > low_beta)
    meditation_ratio = np.sum(meditation_periods) / len(gamma)

    metrics['beta_gamma_pattern'] = {
        'baseline': baseline_pattern,
        'concentration_ratio': concentration_ratio,
        'meditation_ratio': meditation_ratio,
        'pattern_type': 'meditation' if meditation_ratio > 0.3 else ('concentration' if concentration_ratio > 0.3 else 'baseline')
    }

    return metrics


def calculate_hrv_metrics(fp1_clean, fp2_clean):
    """
    심박변이도 (HRV) 지표 계산

    EEG 신호에서 추출한 맥박 정보를 기반으로 HRV 분석

    Parameters:
    -----------
    fp1_clean : ndarray
        전처리된 Fp1 신호
    fp2_clean : ndarray
        전처리된 Fp2 신호

    Returns:
    --------
    hrv_metrics : dict
        {
            'time_domain': {
                'mean_hr': float,      # 평균 심박수 (bpm)
                'sdnn': float,         # NN간격 표준편차 (ms)
                'rmssd': float,        # 연속 NN간격 변이의 제곱평균 루트 (ms)
                'pnn50': float         # 50ms 이상 차이나는 NN간격 비율 (%)
            },
            'frequency_domain': {
                'vlf': float,          # 초저주파 파워 (0.003-0.04 Hz)
                'lf': float,           # 저주파 파워 (0.04-0.15 Hz)
                'hf': float,           # 고주파 파워 (0.15-0.4 Hz)
                'total_power': float,  # 전체 파워
                'lf_hf_ratio': float,  # LF/HF 비율
                'lf_norm': float,      # 정규화된 LF (%)
                'hf_norm': float       # 정규화된 HF (%)
            },
            'interpretation': {
                'stress_level': str,           # 스트레스 수준
                'autonomic_balance': str,      # 자율신경 균형
                'parasympathetic_status': str, # 부교감신경 상태
                'sympathetic_status': str      # 교감신경 상태
            }
        }
    """
    # EEG 신호에서 심박 성분 추출 (매우 낮은 주파수 대역)
    # 실제로는 PPG나 ECG 데이터가 필요하지만, EEG에서 근사적으로 추출

    # 1. 심박 주파수 대역 필터링 (0.5-4 Hz, Delta 대역 활용)
    from scipy.signal import welch

    # Fp1, Fp2 평균 (더 안정적인 신호)
    combined_signal = (fp1_clean + fp2_clean) / 2

    # Delta 대역 (0.5-4 Hz) 추출 - 심박 성분 포함
    nyquist = config.SAMPLING_RATE / 2
    low = 0.5 / nyquist
    high = 4.0 / nyquist
    b_hr, a_hr = scipy.signal.butter(4, [low, high], btype='band')
    hr_signal = scipy.signal.filtfilt(b_hr, a_hr, combined_signal)

    # 2. 피크 검출 (R-R 간격 추정)
    from scipy.signal import find_peaks

    # 피크 검출
    peaks, _ = find_peaks(hr_signal, distance=int(config.SAMPLING_RATE * 0.5))  # 최소 0.5초 간격

    # NN 간격 계산 (ms 단위)
    if len(peaks) < 2:
        # 피크가 충분하지 않으면 기본값 반환
        return _get_default_hrv_metrics(quality='insufficient_peaks')

    nn_intervals = np.diff(peaks) / config.SAMPLING_RATE * 1000  # ms로 변환

    # 데이터 품질 검증 1: 피크 수 검증
    if len(nn_intervals) < 30:
        return _get_default_hrv_metrics(quality='insufficient_data')

    # 이상치 제거 (300-2000 ms 범위 = 30~200 bpm)
    valid_mask = (nn_intervals >= 300) & (nn_intervals <= 2000)
    nn_intervals_filtered = nn_intervals[valid_mask]

    # 데이터 품질 검증 2: 유효 데이터 비율 검증
    valid_ratio = len(nn_intervals_filtered) / len(nn_intervals)
    if valid_ratio < 0.5:  # 50% 미만이 유효하면 품질 저하
        return _get_default_hrv_metrics(quality='low_quality_ratio')

    if len(nn_intervals_filtered) < 10:
        return _get_default_hrv_metrics(quality='insufficient_valid_data')

    # 3. 시간 영역 지표 계산
    mean_nn = np.mean(nn_intervals_filtered)
    mean_hr = 60000 / mean_nn  # bpm
    sdnn = np.std(nn_intervals_filtered, ddof=1)

    # 데이터 품질 검증 3: 생리학적 타당성 검증
    if mean_hr < 40 or mean_hr > 180:
        return _get_default_hrv_metrics(quality='abnormal_heart_rate')

    # RMSSD 계산
    diff_nn = np.diff(nn_intervals_filtered)
    rmssd = np.sqrt(np.mean(diff_nn ** 2))

    # pNN50 계산
    nn50_count = np.sum(np.abs(diff_nn) > 50)
    pnn50 = (nn50_count / len(diff_nn)) * 100

    # 데이터 품질 검증 4: 변동성 타당성 검증
    cv_nn = (np.std(nn_intervals_filtered) / np.mean(nn_intervals_filtered)) * 100
    if cv_nn > 50:  # 변동 계수가 50% 초과하면 비정상
        return _get_default_hrv_metrics(quality='excessive_variability')

    # 4. 주파수 영역 지표 계산
    # NN 간격을 등간격 시계열로 보간
    from scipy.interpolate import interp1d

    # valid_mask에 해당하는 peaks 인덱스 찾기 (nn_intervals는 diff이므로 1개 적음)
    valid_peak_indices = np.where(valid_mask)[0]  # 시작 피크 인덱스
    valid_peaks = peaks[valid_peak_indices]

    if len(valid_peaks) < 2:
        return _get_default_hrv_metrics()

    time_peaks = valid_peaks / config.SAMPLING_RATE

    # 4 Hz로 리샘플링
    fs_resample = 4.0
    time_interp = np.arange(time_peaks[0], time_peaks[-1], 1/fs_resample)

    if len(time_interp) < 10:
        return _get_default_hrv_metrics()

    interp_func = interp1d(time_peaks, nn_intervals_filtered, kind='linear', fill_value='extrapolate')
    nn_interp = interp_func(time_interp)

    # Welch 파워 스펙트럼 분석
    nperseg = min(256, len(nn_interp))
    freqs, psd = welch(nn_interp, fs=fs_resample, nperseg=nperseg, scaling='density')

    # 주파수 대역별 파워 계산
    vlf_band = (freqs >= 0.003) & (freqs < 0.04)
    lf_band = (freqs >= 0.04) & (freqs < 0.15)
    hf_band = (freqs >= 0.15) & (freqs < 0.4)

    vlf_power = np.trapz(psd[vlf_band], freqs[vlf_band]) if np.any(vlf_band) else 0
    lf_power = np.trapz(psd[lf_band], freqs[lf_band]) if np.any(lf_band) else 0
    hf_power = np.trapz(psd[hf_band], freqs[hf_band]) if np.any(hf_band) else 0
    total_power = vlf_power + lf_power + hf_power

    # LF/HF 비율
    lf_hf_ratio = lf_power / hf_power if hf_power > 0 else 0

    # 정규화된 LF, HF (VLF 제외)
    lf_hf_sum = lf_power + hf_power
    lf_norm = (lf_power / lf_hf_sum * 100) if lf_hf_sum > 0 else 0
    hf_norm = (hf_power / lf_hf_sum * 100) if lf_hf_sum > 0 else 0

    # 5. 해석 생성
    interpretation = _interpret_hrv(
        sdnn=sdnn,
        rmssd=rmssd,
        lf_hf_ratio=lf_hf_ratio,
        hf_power=hf_power
    )

    return {
        'quality': 'good',
        'quality_message': '데이터 품질 양호',
        'valid_ratio': round(valid_ratio * 100, 1),
        'time_domain': {
            'mean_hr': round(mean_hr, 1),
            'sdnn': round(sdnn, 1),
            'rmssd': round(rmssd, 1),
            'pnn50': round(pnn50, 1)
        },
        'frequency_domain': {
            'vlf': round(vlf_power, 2),
            'lf': round(lf_power, 2),
            'hf': round(hf_power, 2),
            'total_power': round(total_power, 2),
            'lf_hf_ratio': round(lf_hf_ratio, 2),
            'lf_norm': round(lf_norm, 1),
            'hf_norm': round(hf_norm, 1)
        },
        'interpretation': interpretation
    }


def _get_default_hrv_metrics(quality='unknown'):
    """HRV 계산 실패 시 기본값 반환

    Parameters:
    -----------
    quality : str
        데이터 품질 상태
        - 'insufficient_peaks': 피크 수 부족
        - 'insufficient_data': 전체 데이터 부족
        - 'low_quality_ratio': 유효 데이터 비율 낮음
        - 'insufficient_valid_data': 유효 데이터 수 부족
        - 'abnormal_heart_rate': 비정상 심박수
        - 'excessive_variability': 과도한 변동성
    """
    quality_messages = {
        'insufficient_peaks': '데이터 품질 저하: 피크 수 부족',
        'insufficient_data': '데이터 품질 저하: 전체 데이터 부족 (최소 30개 필요)',
        'low_quality_ratio': '데이터 품질 저하: 유효 데이터 50% 미만',
        'insufficient_valid_data': '데이터 품질 저하: 유효 데이터 수 부족',
        'abnormal_heart_rate': '데이터 품질 저하: 비정상 심박수 (40~180 bpm 범위 벗어남)',
        'excessive_variability': '데이터 품질 저하: 과도한 변동성 (CV > 50%)',
        'unknown': '데이터 품질 저하: 원인 미상'
    }

    return {
        'quality': quality,
        'quality_message': quality_messages.get(quality, '데이터 품질 저하'),
        'time_domain': {
            'mean_hr': 0,
            'sdnn': 0,
            'rmssd': 0,
            'pnn50': 0
        },
        'frequency_domain': {
            'vlf': 0,
            'lf': 0,
            'hf': 0,
            'total_power': 0,
            'lf_hf_ratio': 0,
            'lf_norm': 0,
            'hf_norm': 0
        },
        'interpretation': {
            'stress_level': '측정 불가',
            'autonomic_balance': '측정 불가',
            'parasympathetic_status': '측정 불가',
            'sympathetic_status': '측정 불가'
        }
    }


def _interpret_hrv(sdnn, rmssd, lf_hf_ratio, hf_power):
    """
    HRV 지표 해석

    참고: 논문 "정신과에서 심박 변이도(Heart Rate Variability)의 이용"
    """
    interpretation = {}

    # 1. 스트레스 수준 (SDNN, LF/HF ratio 기반)
    if sdnn < 50:
        if lf_hf_ratio > 2.0:
            stress_level = '높음'
        else:
            stress_level = '중간'
    elif sdnn < 100:
        stress_level = '정상'
    else:
        stress_level = '낮음'

    interpretation['stress_level'] = stress_level

    # 2. 자율신경 균형 (LF/HF ratio)
    if lf_hf_ratio > 2.5:
        balance = '교감신경 우세'
    elif lf_hf_ratio < 0.5:
        balance = '부교감신경 우세'
    else:
        balance = '균형'

    interpretation['autonomic_balance'] = balance

    # 3. 부교감신경 상태 (HF power, RMSSD)
    if hf_power > 1000 and rmssd > 40:
        para_status = '높음 (이완 상태)'
    elif hf_power > 500 and rmssd > 25:
        para_status = '정상'
    else:
        para_status = '낮음 (긴장 상태)'

    interpretation['parasympathetic_status'] = para_status

    # 4. 교감신경 상태 (LF/HF ratio)
    if lf_hf_ratio > 2.5:
        symp_status = '높음 (스트레스/각성)'
    elif lf_hf_ratio > 1.0:
        symp_status = '정상'
    else:
        symp_status = '낮음'

    interpretation['sympathetic_status'] = symp_status

    return interpretation
