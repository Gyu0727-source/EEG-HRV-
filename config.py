"""
EEG 실시간 분석 프로젝트 - 설정 파일
"""

# 분석 파라미터
SAMPLING_RATE = 250  # Hz
WINDOW_SIZE = 2.0  # 초 (2초 윈도우)
OVERLAP = 0.5  # 50% 오버랩 (1초씩 이동)
SMOOTHING_WINDOW = 51  # Savitzky-Golay 필터 윈도우 크기
SMOOTHING_POLY = 3  # Savitzky-Golay 다항식 차수

# 전처리 파라미터 (기존 역공학 알고리즘 기반)
NOTCH_FREQUENCY = 60  # Hz (전원선 노이즈)
NOTCH_QUALITY = 30
LOWCUT_FREQUENCY = 0.5  # Hz
HIGHCUT_FREQUENCY = 50  # Hz
FILTER_ORDER = 4

# 주파수 대역 (비웨이브 표준 + Low/High Beta 분리)
FREQUENCY_BANDS = {
    'delta': (1, 4),      # 비웨이브: 1-4Hz (깊은 이완)
    'theta': (4, 8),      # 비웨이브: 4-8Hz (명상, 창의성)
    'alpha': (8, 12),     # 비웨이브: 8-12Hz (편안한 각성)
    'low_beta': (13, 18), # 비웨이브: 13-18Hz (집중)
    'high_beta': (18, 30),# 비웨이브: 18-30Hz (긴장, 스트레스)
    'gamma': (30, 50)     # 비웨이브: 30-50Hz (고차원 인지)
}

# 변화점 감지 파라미터
N_CHANGE_POINTS = 3  # 최대 변화점 개수
MIN_DISTANCE_RATIO = 0.2  # 변화점 간 최소 거리 (전체 길이의 20%)
CURVATURE_THRESHOLD = 0.1  # 곡률 임계값 (통계적 유의성)

# 그래프 설정
GRAPH_WIDTH = 14  # 인치
GRAPH_HEIGHT = 5  # 인치
GRAPH_DPI = 300

# 색상 (각 주파수 대역별)
COLORS = {
    'delta': '#000080',      # Navy
    'theta': '#8B008B',      # Dark Magenta
    'alpha': '#228B22',      # Forest Green
    'low_beta': '#FFA500',   # Orange
    'high_beta': '#FF6B35',  # Dark Orange
    'gamma': '#FF4500'       # Orange Red
}

# 주파수 대역 정보 (한글명, 설명) - 비웨이브 표준
BAND_INFO = {
    'delta': {
        'name_kr': '델타파',
        'name_en': 'Delta',
        'description': '깊은 수면 및 이완 상태',
        'range': '1-4Hz',
        'icon': 'D'
    },
    'theta': {
        'name_kr': '세타파',
        'name_en': 'Theta',
        'description': '명상 및 창의적 사고',
        'range': '4-8Hz',
        'icon': 'Θ'
    },
    'alpha': {
        'name_kr': '알파파',
        'name_en': 'Alpha',
        'description': '편안한 각성 상태',
        'range': '8-12Hz',
        'icon': 'α'
    },
    'low_beta': {
        'name_kr': 'Low Beta파',
        'name_en': 'Low Beta',
        'description': '집중 및 인지 활동',
        'range': '13-18Hz',
        'icon': 'β1'
    },
    'high_beta': {
        'name_kr': 'High Beta파',
        'name_en': 'High Beta',
        'description': '긴장 및 스트레스',
        'range': '18-30Hz',
        'icon': 'β2'
    },
    'gamma': {
        'name_kr': '감마파',
        'name_en': 'Gamma',
        'description': '고도의 인지 활동',
        'range': '30-50Hz',
        'icon': 'γ'
    }
}

# 비율 지표 (비웨이브 명상/집중 알고리즘)
RATIO_METRICS = {
    'theta_alpha_ratio': {
        'name_kr': 'Theta/Alpha 비율',
        'name_en': 'T/A ratio',
        'description': '안정화 지표 (명상 깊이)',
        'interpretation': {
            'high': 'Theta > Alpha: 깊은 안정(명상) 상태',
            'low': 'Alpha > Theta: 편안한 각성 상태'
        }
    },
    'gamma_theta_slope': {
        'name_kr': 'Gamma/Theta 기울기',
        'name_en': 'G/T slope',
        'description': '집중 vs 명상 지표',
        'interpretation': {
            'positive': '명상 기반 안정화 (기울기 큼)',
            'negative': '주의집중 활성화 (Gamma 증가)'
        }
    }
}

# HRV 파라미터 (HeartPy 라이브러리 기준)
HRV_ENABLED = True  # HRV 분석 활성화 여부
HRV_SAMPLE_RATE = 250  # Hz

# HRV Time Domain 지표
HRV_TIME_DOMAIN = [
    'bpm',      # Beats Per Minute
    'ibi',      # Interbeat Interval
    'sdnn',     # Standard Deviation of NN intervals
    'sdsd',     # Standard Deviation of Successive Differences
    'rmssd',    # Root Mean Square of Successive Differences
    'pnn20',    # Proportion of NN20 (>20ms)
    'pnn50',    # Proportion of NN50 (>50ms)
    'mad'       # Median Absolute Deviation
]

# HRV Frequency Domain 지표
HRV_FREQUENCY_DOMAIN = [
    'lf',       # Low Frequency (0.05-0.15 Hz)
    'hf',       # High Frequency (0.15-0.5 Hz)
    'lf_hf_ratio'  # LF/HF ratio (자율신경 균형)
]

# 디렉토리 경로
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'raw_data')
ANALYSIS_DATA_DIR = os.path.join(BASE_DIR, 'analysis_data')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
GRAPHS_DIR = os.path.join(BASE_DIR, 'graphs')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
