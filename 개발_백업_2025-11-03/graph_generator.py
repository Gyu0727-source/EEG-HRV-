"""
EEG 실시간 분석 프로젝트 - 그래프 생성 모듈

각 주파수 대역별로 개별 PNG 생성:
- 부드러운 추세선
- 의미있는 변화점 표시 (화살표 + 타임스탬프)
- 평균선 표시
- 가변 시간축
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 그래프 생성
import config


def format_time(seconds):
    """
    초를 "분:초" 형식으로 변환

    예: 185초 → "3:05"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def plot_band_timeseries(time_array, smoothed_data, change_points, change_types,
                          band_name, save_path):
    """
    단일 주파수 대역의 시계열 그래프 생성

    Parameters:
    -----------
    time_array : ndarray
        시간 배열 (초)
    smoothed_data : ndarray
        스무딩된 파워 데이터
    change_points : list of int
        변화점 인덱스
    change_types : list of str
        변화 방향 ('increase', 'decrease', 'stable')
    band_name : str
        주파수 대역 이름 ('delta', 'theta', ...)
    save_path : str
        저장 경로

    Returns:
    --------
    save_path : str
        저장된 파일 경로
    """
    # 그래프 설정
    fig, ax = plt.subplots(figsize=(config.GRAPH_WIDTH, config.GRAPH_HEIGHT), dpi=config.GRAPH_DPI)

    # 배경 색상
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # 주파수 대역 정보
    band_info = config.BAND_INFO[band_name]
    color = config.COLORS[band_name]

    # 부드러운 추세선 그리기
    ax.plot(time_array, smoothed_data, color=color, linewidth=2, label=f"{band_info['name_kr']} 파워")

    # 평균선 그리기
    mean_power = np.mean(smoothed_data)
    ax.axhline(y=mean_power, color='gray', linestyle='--', linewidth=1, alpha=0.7, label='평균')

    # 변화점 표시
    for cp_idx, cp_type in zip(change_points, change_types):
        cp_time = time_array[cp_idx]
        cp_power = smoothed_data[cp_idx]

        # 화살표 방향 및 색상
        if cp_type == 'increase':
            arrow_symbol = '↑'
            arrow_color = 'green'
        elif cp_type == 'decrease':
            arrow_symbol = '↓'
            arrow_color = 'red'
        else:  # stable
            arrow_symbol = '→'
            arrow_color = 'blue'

        # 변화점 마커
        ax.plot(cp_time, cp_power, marker='o', markersize=10, color=arrow_color,
                markeredgecolor='black', markeredgewidth=1.5, zorder=5)

        # 타임스탬프 표시
        time_label = format_time(cp_time)
        ax.annotate(f"{arrow_symbol} {time_label}",
                    xy=(cp_time, cp_power),
                    xytext=(0, 20),
                    textcoords='offset points',
                    ha='center',
                    fontsize=10,
                    fontweight='bold',
                    color=arrow_color,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=arrow_color, alpha=0.8))

    # 축 레이블
    ax.set_xlabel('측정 시간', fontsize=12, fontweight='bold')
    ax.set_ylabel('파워 (μV²)', fontsize=12, fontweight='bold')

    # 제목
    title = f"{band_info['name_kr']} ({band_info['range']}) - {band_info['description']}"
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    # X축 시간 레이블을 "분:초" 형식으로 변경
    max_time = time_array[-1]
    if max_time < 120:  # 2분 이하
        # 10초 간격
        tick_interval = 10
    elif max_time < 600:  # 10분 이하
        # 30초 간격
        tick_interval = 30
    else:
        # 1분 간격
        tick_interval = 60

    tick_positions = np.arange(0, max_time + tick_interval, tick_interval)
    tick_labels = [format_time(t) for t in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=0)

    # 범례
    ax.legend(loc='upper right', fontsize=10)

    # 그리드
    ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.5)

    # 여백 조정
    plt.tight_layout()

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"그래프 저장: {save_path}")

    return save_path


def generate_graphs(analysis_result, info):
    """
    5개 주파수 대역별 그래프 생성

    Parameters:
    -----------
    analysis_result : dict
        분석 결과 (analyzer.py의 analyze_eeg 결과)
    info : dict
        파일 정보

    Returns:
    --------
    graph_paths : dict
        {'delta': path, 'theta': path, ...}
    """
    from utils import get_output_paths

    paths = get_output_paths(info)
    graph_paths = {}

    # 각 주파수 대역별로 그래프 생성
    for band in config.FREQUENCY_BANDS.keys():
        graph_path = plot_band_timeseries(
            time_array=analysis_result['time'],
            smoothed_data=analysis_result['smooth'][band],
            change_points=analysis_result['change_points'][band],
            change_types=analysis_result['change_types'][band],
            band_name=band,
            save_path=paths['graphs'][band]
        )
        graph_paths[band] = graph_path

    return graph_paths
