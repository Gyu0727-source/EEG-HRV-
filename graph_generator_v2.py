"""
EEG 실시간 분석 프로젝트 - 그래프 생성 모듈 V2 (한글 폰트 문제 해결)

개선사항:
1. 한글 폰트 자동 설정 (Windows Malgun Gothic)
2. 폰트 경고 제거
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # GUI 없이 그래프 생성

# 한글 폰트 설정
import platform

def setup_korean_font():
    """한글 폰트 자동 설정"""
    system = platform.system()

    if system == 'Windows':
        # Windows: Malgun Gothic
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        plt.rcParams['font.family'] = 'AppleGothic'
    else:  # Linux
        plt.rcParams['font.family'] = 'NanumGothic'

    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False

    # 이모지 경고 억제
    import warnings
    warnings.filterwarnings('ignore', message='Glyph.*missing from font')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# 폰트 설정 실행
setup_korean_font()

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
    ax.plot(time_array, smoothed_data, color=color, linewidth=2.5, label=f"{band_info['name_kr']} 파워", zorder=3)

    # 평균선 그리기
    mean_power = np.mean(smoothed_data)
    ax.axhline(y=mean_power, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label='평균', zorder=2)

    # 변화점 표시
    for cp_idx, cp_type in zip(change_points, change_types):
        cp_time = time_array[cp_idx]
        cp_power = smoothed_data[cp_idx]

        # 화살표 방향 및 색상
        if cp_type == 'increase':
            arrow_symbol = '↑'
            arrow_color = '#2ecc71'  # 초록
        elif cp_type == 'decrease':
            arrow_symbol = '↓'
            arrow_color = '#e74c3c'  # 빨강
        else:  # stable
            arrow_symbol = '→'
            arrow_color = '#3498db'  # 파랑

        # 변화점 마커
        ax.plot(cp_time, cp_power, marker='o', markersize=12, color=arrow_color,
                markeredgecolor='white', markeredgewidth=2, zorder=5)

        # 타임스탬프 표시
        time_label = format_time(cp_time)
        ax.annotate(f"{arrow_symbol} {time_label}",
                    xy=(cp_time, cp_power),
                    xytext=(0, 25),
                    textcoords='offset points',
                    ha='center',
                    fontsize=11,
                    fontweight='bold',
                    color=arrow_color,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=arrow_color, alpha=0.9, linewidth=2),
                    zorder=6)

    # 축 레이블
    ax.set_xlabel('측정 시간', fontsize=13, fontweight='bold')
    ax.set_ylabel('파워 (μV²)', fontsize=13, fontweight='bold')

    # 제목
    title = f"{band_info['name_kr']} ({band_info['range']}) - {band_info['description']}"
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # X축 시간 레이블을 "분:초" 형식으로 변경
    max_time = time_array[-1]
    if max_time < 120:  # 2분 이하
        tick_interval = 10
    elif max_time < 600:  # 10분 이하
        tick_interval = 30
    else:
        tick_interval = 60

    tick_positions = np.arange(0, max_time + tick_interval, tick_interval)
    tick_labels = [format_time(t) for t in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=0, fontsize=10)

    # Y축 레이블
    ax.tick_params(axis='y', labelsize=10)

    # 범례
    ax.legend(loc='upper right', fontsize=11, framealpha=0.9)

    # 그리드
    ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.8, zorder=1)

    # 여백 조정
    plt.tight_layout()

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"그래프 저장: {save_path}")

    return save_path


def plot_ratio_timeseries(time_array, ratio_data, ratio_name, save_path, info):
    """
    비율 지표 시계열 그래프 생성 (Theta/Alpha, Gamma/Theta)

    Parameters:
    -----------
    time_array : ndarray
        시간 배열 (초)
    ratio_data : dict
        비율 데이터 (calculate_ratio_metrics 결과)
    ratio_name : str
        비율 이름 ('theta_alpha_ratio' or 'gamma_theta_slope')
    save_path : str
        저장 경로
    info : dict
        파일 정보

    Returns:
    --------
    save_path : str
        저장된 파일 경로
    """
    fig, ax = plt.subplots(figsize=(config.GRAPH_WIDTH, config.GRAPH_HEIGHT), dpi=config.GRAPH_DPI)

    # 배경 색상
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # 비율 정보
    ratio_info = config.RATIO_METRICS[ratio_name]

    if ratio_name == 'theta_alpha_ratio':
        # Theta/Alpha 비율 그래프
        ratio_timeseries = ratio_data['timeseries']
        mean_ratio = ratio_data['mean']

        # 비율선 그리기
        ax.plot(time_array, ratio_timeseries, color='#9C27B0', linewidth=2.5, label='T/A Ratio', zorder=3)

        # 평균선
        ax.axhline(y=mean_ratio, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label=f'평균: {mean_ratio:.2f}', zorder=2)

        # 기준선 (1.0)
        ax.axhline(y=1.0, color='red', linestyle=':', linewidth=1.5, alpha=0.5, label='기준 (Theta=Alpha)', zorder=2)

        # 추세 표시
        if ratio_data['trend'] == 'increasing':
            trend_text = '↑ 명상 상태 진입'
            trend_color = '#4CAF50'
        elif ratio_data['trend'] == 'decreasing':
            trend_text = '↓ 각성 상태 진입'
            trend_color = '#FF9800'
        else:
            trend_text = '→ 안정적 유지'
            trend_color = '#2196F3'

        ax.text(0.98, 0.95, trend_text, transform=ax.transAxes, fontsize=14,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor=trend_color, alpha=0.3))

        ylabel = 'Theta/Alpha 비율'

    else:  # gamma_theta_slope
        # Gamma/Theta 비율 그래프
        ratio_timeseries = ratio_data['timeseries']
        mean_ratio = ratio_data['mean_ratio']

        # 비율선 그리기
        ax.plot(time_array, ratio_timeseries, color='#FF5722', linewidth=2.5, label='G/T Ratio', zorder=3)

        # 평균선
        ax.axhline(y=mean_ratio, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label=f'평균: {mean_ratio:.2f}', zorder=2)

        # 해석 표시
        if ratio_data['interpretation'] == 'concentration':
            interp_text = '주의집중 활성화 (Gamma↑)'
            interp_color = '#FF6B6B'
        else:
            interp_text = '명상 기반 안정화'
            interp_color = '#4ECDC4'

        ax.text(0.98, 0.95, interp_text, transform=ax.transAxes, fontsize=14,
                verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor=interp_color, alpha=0.3))

        ylabel = 'Gamma/Theta 비율'

    # 축 설정
    ax.set_xlabel('시간 (초)', fontsize=14, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
    ax.set_title(f"{ratio_info['name_kr']} 시계열 변화 - {info['name']}", fontsize=16, fontweight='bold', pad=20)

    # 그리드
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

    # 범례
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

    # 레이아웃 조정
    plt.tight_layout()

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"비율 그래프 저장: {save_path}")

    return save_path


def generate_graphs(analysis_result, info):
    """
    주파수 대역별 + 비율 지표 그래프 생성

    Parameters:
    -----------
    analysis_result : dict
        분석 결과 (analyzer.py의 analyze_eeg 결과)
    info : dict
        파일 정보

    Returns:
    --------
    graph_paths : dict
        {'delta': path, 'theta': path, ..., 'theta_alpha_ratio': path, ...}
    """
    from utils import get_output_paths

    paths = get_output_paths(info)
    graph_paths = {}

    # 1. 각 주파수 대역별 그래프 생성 (6개)
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

    # 2. 비율 지표 그래프 생성
    if 'ratio_metrics' in analysis_result:
        ratio_metrics = analysis_result['ratio_metrics']

        # Theta/Alpha ratio 그래프
        ta_ratio_path = os.path.join(
            config.GRAPHS_DIR,
            f"{info['name']}_{info['gender']}_{info['age']}_theta_alpha_ratio.png"
        )
        graph_paths['theta_alpha_ratio'] = plot_ratio_timeseries(
            time_array=analysis_result['time'],
            ratio_data=ratio_metrics['theta_alpha_ratio'],
            ratio_name='theta_alpha_ratio',
            save_path=ta_ratio_path,
            info=info
        )

        # Gamma/Theta slope 그래프
        gt_slope_path = os.path.join(
            config.GRAPHS_DIR,
            f"{info['name']}_{info['gender']}_{info['age']}_gamma_theta_slope.png"
        )
        graph_paths['gamma_theta_slope'] = plot_ratio_timeseries(
            time_array=analysis_result['time'],
            ratio_data=ratio_metrics['gamma_theta_slope'],
            ratio_name='gamma_theta_slope',
            save_path=gt_slope_path,
            info=info
        )

    # 3. 주파수 대역 비율 막대그래프 생성
    band_ratio_path = os.path.join(
        config.GRAPHS_DIR,
        f"{info['name']}_{info['gender']}_{info['age']}_band_ratio.png"
    )
    graph_paths['band_ratio'] = plot_band_ratio_bar(
        band_powers_smooth=analysis_result['smooth'],
        save_path=band_ratio_path,
        info=info
    )

    # 4. HRV 시각화 그래프 생성
    if 'hrv_metrics' in analysis_result and analysis_result['hrv_metrics'] is not None:
        hrv_graph_path = os.path.join(
            config.GRAPHS_DIR,
            f"{info['name']}_{info['gender']}_{info['age']}_hrv_visualization.png"
        )
        graph_paths['hrv_visualization'] = plot_hrv_visualization(
            hrv_metrics=analysis_result['hrv_metrics'],
            save_path=hrv_graph_path,
            info=info
        )

    # 5. 좌뇌/우뇌 균형 그래프 생성
    if 'fp1_powers' in analysis_result and 'fp2_powers' in analysis_result:
        brain_balance_path = os.path.join(
            config.GRAPHS_DIR,
            f"{info['name']}_{info['gender']}_{info['age']}_brain_balance.png"
        )
        graph_paths['brain_balance'] = plot_brain_balance(
            fp1_power=analysis_result['fp1_powers'],
            fp2_power=analysis_result['fp2_powers'],
            save_path=brain_balance_path,
            info=info
        )

    return graph_paths


def plot_band_ratio_bar(band_powers_smooth, save_path, info):
    """
    주파수 대역별 평균 파워 비율 막대 그래프 생성

    Parameters:
    -----------
    band_powers_smooth : dict
        스무딩된 주파수 대역별 파워 딕셔너리
    save_path : str
        저장 경로
    info : dict
        파일 정보

    Returns:
    --------
    save_path : str
        저장된 파일 경로
    """
    fig, ax = plt.subplots(figsize=(10, 6), dpi=config.GRAPH_DPI)

    # 배경 색상
    ax.set_facecolor('white')
    fig.patch.set_facecolor('white')

    # 각 대역의 평균 파워 계산
    band_means = {}
    for band in config.FREQUENCY_BANDS.keys():
        band_means[band] = np.mean(band_powers_smooth[band])

    # 전체 합계 계산
    total_power = sum(band_means.values())

    # 비율 계산 (%)
    band_ratios = {}
    for band in config.FREQUENCY_BANDS.keys():
        band_ratios[band] = (band_means[band] / total_power) * 100

    # 막대 그래프 데이터 준비
    bands = list(config.FREQUENCY_BANDS.keys())
    ratios = [band_ratios[band] for band in bands]
    colors = [config.COLORS[band] for band in bands]
    labels = [config.BAND_INFO[band]['name_kr'] for band in bands]

    # 막대 그래프 그리기
    bars = ax.bar(range(len(bands)), ratios, color=colors, alpha=0.8, edgecolor='white', linewidth=2)

    # 막대 위에 비율 표시
    for i, (bar, ratio, band) in enumerate(zip(bars, ratios, bands)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{ratio:.1f}%',
                ha='center', va='bottom', fontsize=12, fontweight='bold')

        # 막대 중앙에 파워 값 표시
        mean_val = band_means[band]
        ax.text(bar.get_x() + bar.get_width()/2., height/2,
                f'{mean_val:.1f}μV²',
                ha='center', va='center', fontsize=10, color='white', fontweight='bold')

    # X축 설정
    ax.set_xticks(range(len(bands)))
    ax.set_xticklabels(labels, fontsize=12, fontweight='bold')

    # Y축 설정
    ax.set_ylabel('비율 (%)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(ratios) * 1.2)  # 여유 공간

    # 제목
    ax.set_title(f'주파수 대역별 평균 파워 비율 - {info["name"]}', fontsize=16, fontweight='bold', pad=20)

    # 그리드 (Y축만)
    ax.yaxis.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # 최대 비율 대역 강조
    max_band_idx = ratios.index(max(ratios))
    bars[max_band_idx].set_edgecolor('gold')
    bars[max_band_idx].set_linewidth(4)

    # 레이아웃 조정
    plt.tight_layout()

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"주파수 대역 비율 그래프 저장: {save_path}")

    return save_path


def plot_hrv_visualization(hrv_metrics, save_path, info):
    """
    HRV 지표 시각화 - 4개 서브플롯으로 구성

    1. 시간 영역 지표 게이지 차트 (SDNN, RMSSD, pNN50)
    2. 주파수 영역 파이 차트 (VLF, LF, HF)
    3. 스트레스 수준 가로 막대 게이지
    4. 자율신경 균형 좌우 대칭 막대

    Parameters:
    -----------
    hrv_metrics : dict
        HRV 분석 결과
    save_path : str
        저장 경로
    info : dict
        개인 정보

    Returns:
    --------
    save_path : str
        저장된 파일 경로
    """
    fig = plt.figure(figsize=(16, 10), dpi=config.GRAPH_DPI)
    fig.patch.set_facecolor('white')

    # 그리드 레이아웃: 2행 2열
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3,
                          left=0.08, right=0.95, top=0.92, bottom=0.08)

    time_domain = hrv_metrics['time_domain']
    freq_domain = hrv_metrics['frequency_domain']
    interp = hrv_metrics['interpretation']

    # 1. 시간 영역 지표 게이지 차트 (좌상단)
    ax1 = fig.add_subplot(gs[0, 0])
    plot_time_domain_gauges(ax1, time_domain)

    # 2. 주파수 영역 파이 차트 (우상단)
    ax2 = fig.add_subplot(gs[0, 1])
    plot_frequency_domain_pie(ax2, freq_domain)

    # 3. 스트레스 수준 가로 막대 (좌하단)
    ax3 = fig.add_subplot(gs[1, 0])
    plot_stress_gauge(ax3, interp['stress_level'], freq_domain['lf_hf_ratio'], time_domain['sdnn'])

    # 4. 자율신경 균형 좌우 막대 (우하단)
    ax4 = fig.add_subplot(gs[1, 1])
    plot_autonomic_balance(ax4, freq_domain['lf_norm'], freq_domain['hf_norm'], interp['autonomic_balance'])

    # 전체 제목
    fig.suptitle(f'💓 심박변이도 (HRV) 종합 분석 - {info["name"]}',
                 fontsize=20, fontweight='bold', y=0.98)

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"HRV 시각화 그래프 저장: {save_path}")

    return save_path


def plot_time_domain_gauges(ax, time_domain):
    """시간 영역 지표 게이지 차트 (ubio 스타일)"""
    ax.set_facecolor('white')
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 4)
    ax.axis('off')

    # 제목
    ax.text(80, 3.7, '⏱️ 시간 영역 지표', ha='center', fontsize=16, fontweight='bold')

    # Mean BPM (40~140, 정상: 60~100)
    mean_hr = time_domain['mean_hr']
    y_pos = 3.0
    ax.text(5, y_pos + 0.15, '평균 맥박', fontsize=11, fontweight='bold', va='center')
    ax.text(5, y_pos - 0.1, f'{mean_hr:.1f}', fontsize=10, va='center', color='#333')

    # 전체 바 (0~160)
    for x in range(40, 141):
        if 60 <= x <= 100:
            color = '#4caf50'  # 정상 범위
        else:
            color = '#e0e0e0'  # 비정상 범위
        ax.add_patch(plt.Rectangle((x, y_pos - 0.15), 0.95, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    # 현재 값 마커
    marker_x = max(40, min(140, mean_hr))
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    # 범위 레이블
    ax.text(40, y_pos - 0.35, '40', fontsize=8, ha='center', color='gray')
    ax.text(70, y_pos - 0.35, '70', fontsize=8, ha='center', color='gray')
    ax.text(100, y_pos - 0.35, '100', fontsize=8, ha='center', color='gray')
    ax.text(140, y_pos - 0.35, '140', fontsize=8, ha='center', color='gray')

    # SDNN (0~150, 정상: 30~120)
    sdnn_val = time_domain['sdnn']
    y_pos = 2.0
    ax.text(5, y_pos + 0.15, '맥박표준편차', fontsize=11, fontweight='bold', va='center')
    ax.text(5, y_pos - 0.1, f'{sdnn_val:.1f}', fontsize=10, va='center', color='#333')

    for x in range(0, 151):
        if 30 <= x <= 120:
            color = '#4caf50'
        else:
            color = '#e0e0e0'
        ax.add_patch(plt.Rectangle((x + 10, y_pos - 0.15), 0.95, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    marker_x = max(0, min(150, sdnn_val)) + 10
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    ax.text(10, y_pos - 0.35, '0', fontsize=8, ha='center', color='gray')
    ax.text(55, y_pos - 0.35, '45', fontsize=8, ha='center', color='gray')
    ax.text(100, y_pos - 0.35, '90', fontsize=8, ha='center', color='gray')
    ax.text(160, y_pos - 0.35, '150', fontsize=8, ha='center', color='gray')

    # RMSSD (0~150, 정상: 20~100)
    rmssd_val = time_domain['rmssd']
    y_pos = 1.0
    ax.text(5, y_pos + 0.15, '평균편차', fontsize=11, fontweight='bold', va='center')
    ax.text(5, y_pos - 0.1, f'{rmssd_val:.1f}', fontsize=10, va='center', color='#333')

    for x in range(0, 151):
        if 20 <= x <= 100:
            color = '#4caf50'
        else:
            color = '#e0e0e0'
        ax.add_patch(plt.Rectangle((x + 10, y_pos - 0.15), 0.95, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    marker_x = max(0, min(150, rmssd_val)) + 10
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    ax.text(10, y_pos - 0.35, '0', fontsize=8, ha='center', color='gray')
    ax.text(55, y_pos - 0.35, '45', fontsize=8, ha='center', color='gray')
    ax.text(100, y_pos - 0.35, '90', fontsize=8, ha='center', color='gray')
    ax.text(160, y_pos - 0.35, '150', fontsize=8, ha='center', color='gray')

    # 설명
    ax.text(80, 0.1, '녹색 구간: 정상 범위 | 빨간 화살표: 현재 값',
            ha='center', fontsize=9, color='gray', style='italic')


def plot_frequency_domain_pie(ax, freq_domain):
    """주파수 영역 막대 차트 (ubio 스타일)"""
    ax.set_facecolor('white')
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.5)
    ax.axis('off')

    # 제목
    ax.text(6, 4.2, '📊 주파수 영역 지표', ha='center', fontsize=16, fontweight='bold')

    # 데이터
    lf = freq_domain['lf']
    hf = freq_domain['hf']
    lf_hf_ratio = freq_domain['lf_hf_ratio']

    # LF (교감+부교감): 0~10, 정상: 4~6
    y_pos = 3.0
    ax.text(0.5, y_pos + 0.15, '교감활성', fontsize=11, fontweight='bold', va='center')
    ax.text(0.5, y_pos - 0.1, f'{lf:.1f}', fontsize=10, va='center', color='#333')

    for x in np.arange(0, 10.1, 0.1):
        if 4 <= x <= 6:
            color = '#4caf50'
        else:
            color = '#e0e0e0'
        ax.add_patch(plt.Rectangle((x + 1.5, y_pos - 0.15), 0.095, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    marker_x = max(0, min(10, lf)) + 1.5
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    ax.text(1.5, y_pos - 0.35, '0', fontsize=8, ha='center', color='gray')
    ax.text(4, y_pos - 0.35, '2.5', fontsize=8, ha='center', color='gray')
    ax.text(6.5, y_pos - 0.35, '5', fontsize=8, ha='center', color='gray')
    ax.text(9, y_pos - 0.35, '7.5', fontsize=8, ha='center', color='gray')
    ax.text(11.5, y_pos - 0.35, '10', fontsize=8, ha='center', color='gray')

    # HF (부교감): 0~10, 정상: 4~6
    y_pos = 2.0
    ax.text(0.5, y_pos + 0.15, '부교감활성', fontsize=11, fontweight='bold', va='center')
    ax.text(0.5, y_pos - 0.1, f'{hf:.1f}', fontsize=10, va='center', color='#333')

    for x in np.arange(0, 10.1, 0.1):
        if 4 <= x <= 6:
            color = '#4caf50'
        else:
            color = '#e0e0e0'
        ax.add_patch(plt.Rectangle((x + 1.5, y_pos - 0.15), 0.095, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    marker_x = max(0, min(10, hf)) + 1.5
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    ax.text(1.5, y_pos - 0.35, '0', fontsize=8, ha='center', color='gray')
    ax.text(4, y_pos - 0.35, '2.5', fontsize=8, ha='center', color='gray')
    ax.text(6.5, y_pos - 0.35, '5', fontsize=8, ha='center', color='gray')
    ax.text(9, y_pos - 0.35, '7.5', fontsize=8, ha='center', color='gray')
    ax.text(11.5, y_pos - 0.35, '10', fontsize=8, ha='center', color='gray')

    # LF/HF Ratio: 0~5, 정상: 1~2
    y_pos = 1.0
    ax.text(0.5, y_pos + 0.15, '자율신경균형', fontsize=11, fontweight='bold', va='center')
    ax.text(0.5, y_pos - 0.1, f'{lf_hf_ratio:.2f}', fontsize=10, va='center', color='#333')

    for x in np.arange(0, 5.1, 0.05):
        if 1 <= x <= 2:
            color = '#4caf50'
        else:
            color = '#e0e0e0'
        ax.add_patch(plt.Rectangle((x * 2 + 1.5, y_pos - 0.15), 0.095, 0.3,
                                    facecolor=color, edgecolor='none', alpha=0.6))

    marker_x = max(0, min(5, lf_hf_ratio)) * 2 + 1.5
    ax.plot([marker_x, marker_x], [y_pos - 0.2, y_pos + 0.2], 'r-', linewidth=3)
    ax.plot(marker_x, y_pos + 0.25, 'rv', markersize=8)

    ax.text(1.5, y_pos - 0.35, '0', fontsize=8, ha='center', color='gray')
    ax.text(4, y_pos - 0.35, '1.25', fontsize=8, ha='center', color='gray')
    ax.text(6.5, y_pos - 0.35, '2.5', fontsize=8, ha='center', color='gray')
    ax.text(9, y_pos - 0.35, '3.75', fontsize=8, ha='center', color='gray')
    ax.text(11.5, y_pos - 0.35, '5', fontsize=8, ha='center', color='gray')

    # 설명
    ax.text(6, 0.1, '녹색 구간: 정상 범위 | 빨간 화살표: 현재 값',
            ha='center', fontsize=9, color='gray', style='italic')


def plot_stress_gauge(ax, stress_level, lf_hf_ratio, sdnn):
    """스트레스 수준 가로 막대 게이지"""
    ax.set_facecolor('white')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2)
    ax.axis('off')

    # 제목
    ax.text(5, 1.7, '😰 스트레스 수준', ha='center', fontsize=16, fontweight='bold')

    # 스트레스 레벨 계산 (0-100 스케일)
    # LF/HF ratio와 SDNN 조합으로 계산
    stress_score = 0

    if lf_hf_ratio > 2.5:
        stress_score += 40
    elif lf_hf_ratio > 1.5:
        stress_score += 25
    elif lf_hf_ratio > 1.0:
        stress_score += 10

    if sdnn < 30:
        stress_score += 40
    elif sdnn < 50:
        stress_score += 25
    elif sdnn < 70:
        stress_score += 10

    stress_score = min(100, max(0, stress_score))

    # 배경 그라데이션
    for i in range(100):
        x = 1 + (i / 100) * 8
        if i < 33:
            color = '#4caf50'  # 녹색
        elif i < 66:
            color = '#ff9800'  # 주황
        else:
            color = '#f44336'  # 빨강
        ax.add_patch(plt.Rectangle((x, 0.8), 0.08, 0.5,
                                    facecolor=color, edgecolor='none', alpha=0.3))

    # 테두리
    ax.add_patch(plt.Rectangle((1, 0.8), 8, 0.5,
                                facecolor='none', edgecolor='black', linewidth=2))

    # 현재 위치 마커
    marker_x = 1 + (stress_score / 100) * 8
    ax.plot([marker_x, marker_x], [0.7, 1.4], color='black', linewidth=3)
    ax.plot(marker_x, 1.5, 'v', color='black', markersize=15)

    # 수치 표시
    ax.text(marker_x, 0.5, f'{stress_score:.0f}점', ha='center',
            fontsize=14, fontweight='bold')

    # 범주 레이블
    ax.text(1, 0.2, '낮음\n(정상)', ha='left', fontsize=10, color='#4caf50', fontweight='bold')
    ax.text(5, 0.2, '보통\n(주의)', ha='center', fontsize=10, color='#ff9800', fontweight='bold')
    ax.text(9, 0.2, '높음\n(관리필요)', ha='right', fontsize=10, color='#f44336', fontweight='bold')

    # 상태 표시
    ax.text(5, 1.5, f'현재: {stress_level}', ha='center', fontsize=13,
            fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray'))


def plot_autonomic_balance(ax, lf_norm, hf_norm, balance_status):
    """자율신경 균형 좌우 대칭 막대"""
    ax.set_facecolor('white')
    ax.set_xlim(-100, 100)
    ax.set_ylim(0, 3)
    ax.axis('off')

    # 제목
    ax.text(0, 2.7, '⚖️ 자율신경 균형', ha='center', fontsize=16, fontweight='bold')

    # 교감신경 (왼쪽, 빨강)
    left_width = -lf_norm
    ax.add_patch(plt.Rectangle((left_width, 1.2), abs(left_width), 0.6,
                                facecolor='#ff5722', edgecolor='none', alpha=0.8))
    ax.text(left_width/2, 1.5, f'{lf_norm:.1f}%', ha='center', va='center',
            fontsize=14, fontweight='bold', color='white')
    ax.text(-100, 2.2, '교감신경 (LF)', ha='left', fontsize=12,
            fontweight='bold', color='#ff5722')
    ax.text(-100, 0.9, '긴장·스트레스', ha='left', fontsize=9, color='gray')

    # 부교감신경 (오른쪽, 파랑)
    right_width = hf_norm
    ax.add_patch(plt.Rectangle((0, 1.2), right_width, 0.6,
                                facecolor='#2196f3', edgecolor='none', alpha=0.8))
    ax.text(right_width/2, 1.5, f'{hf_norm:.1f}%', ha='center', va='center',
            fontsize=14, fontweight='bold', color='white')
    ax.text(100, 2.2, '부교감신경 (HF)', ha='right', fontsize=12,
            fontweight='bold', color='#2196f3')
    ax.text(100, 0.9, '이완·회복', ha='right', fontsize=9, color='gray')

    # 중앙선
    ax.axvline(0, color='black', linewidth=2, linestyle='--', alpha=0.5)

    # 균형 상태 표시
    status_color = '#4caf50' if balance_status == '균형' else '#ff9800'
    ax.text(0, 0.4, f'상태: {balance_status}', ha='center', fontsize=13,
            fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=status_color,
                     edgecolor='white', alpha=0.3, linewidth=2))

    # 스케일 표시
    for x in [-100, -50, 0, 50, 100]:
        ax.text(x, 0, f'{abs(x)}', ha='center', fontsize=8, color='gray')


def plot_brain_balance(fp1_power, fp2_power, save_path, info):
    """
    좌뇌/우뇌 균형도 그래프 (Fp1 vs Fp2)

    실시간 타임시리즈 + 전체 평균 게이지

    Parameters:
    -----------
    fp1_power : dict
        Fp1(좌뇌) 주파수 대역별 파워 데이터
    fp2_power : dict
        Fp2(우뇌) 주파수 대역별 파워 데이터
    save_path : str
        저장 경로
    info : dict
        개인 정보

    Returns:
    --------
    save_path : str
        저장된 파일 경로
    """
    fig = plt.figure(figsize=(14, 10), dpi=config.GRAPH_DPI)
    fig.patch.set_facecolor('white')

    # 2x3 그리드 레이아웃 (6개 주파수 대역)
    gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3,
                          left=0.08, right=0.95, top=0.88, bottom=0.12)

    # 전체 제목
    fig.suptitle(f'🧠 좌뇌/우뇌 균형도 분석 - {info["name"]}',
                 fontsize=20, fontweight='bold', y=0.96)

    bands = list(config.FREQUENCY_BANDS.keys())

    for idx, band in enumerate(bands):
        row = idx // 2
        col = idx % 2
        ax = fig.add_subplot(gs[row, col])

        plot_brain_balance_timeseries(ax, fp1_power[band], fp2_power[band], band)

    # 하단에 전체 평균 게이지 추가
    gs_bottom = fig.add_gridspec(1, 1, hspace=0, wspace=0,
                                  left=0.15, right=0.85, top=0.10, bottom=0.02)
    ax_gauge = fig.add_subplot(gs_bottom[0, 0])

    # 전체 평균 계산
    fp1_total = sum(np.mean(fp1_power[band]) for band in bands)
    fp2_total = sum(np.mean(fp2_power[band]) for band in bands)

    plot_brain_balance_gauge(ax_gauge, fp1_total, fp2_total)

    # 저장
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=config.GRAPH_DPI, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    print(f"좌뇌/우뇌 균형 그래프 저장: {save_path}")

    return save_path


def plot_brain_balance_timeseries(ax, fp1_data, fp2_data, band_name):
    """좌뇌/우뇌 파워 타임시리즈 (중앙선 기준 위/아래)"""
    ax.set_facecolor('white')

    time_points = np.arange(len(fp1_data))

    # 중앙선
    ax.axhline(0, color='black', linewidth=1.5, linestyle='-', alpha=0.5)

    # 차이 계산 (양수: 우뇌 우세, 음수: 좌뇌 우세)
    diff = fp2_data - fp1_data

    # 영역 채우기
    ax.fill_between(time_points, 0, diff, where=(diff >= 0),
                     color='#2196f3', alpha=0.6, label='우뇌 우세 (Fp2)')
    ax.fill_between(time_points, 0, diff, where=(diff < 0),
                     color='#ff5722', alpha=0.6, label='좌뇌 우세 (Fp1)')

    # 차이 라인
    ax.plot(time_points, diff, color='black', linewidth=1, alpha=0.7)

    # 축 설정
    band_kr = config.BAND_INFO[band_name]['name_kr']
    ax.set_title(f'{band_kr} ({band_name.upper()})', fontsize=13, fontweight='bold', pad=10)
    ax.set_xlabel('시간 (2초 윈도우)', fontsize=10)
    ax.set_ylabel('파워 차이 (μV²)', fontsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right', fontsize=8)

    # 평균 계산 및 표시
    mean_fp1 = np.mean(fp1_data)
    mean_fp2 = np.mean(fp2_data)
    mean_diff = mean_fp2 - mean_fp1

    balance_pct = (mean_fp2 / (mean_fp1 + mean_fp2)) * 100 if (mean_fp1 + mean_fp2) > 0 else 50

    text_str = f'평균: 좌뇌 {mean_fp1:.1f} | 우뇌 {mean_fp2:.1f} ({balance_pct:.1f}%)'
    ax.text(0.02, 0.98, text_str, transform=ax.transAxes,
            fontsize=9, va='top', ha='left',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'))


def plot_brain_balance_gauge(ax, fp1_total, fp2_total):
    """전체 평균 좌뇌/우뇌 균형 게이지"""
    ax.set_facecolor('white')
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.4, 1.3)
    ax.axis('off')

    # 전체 평균 비율 계산
    total = fp1_total + fp2_total
    if total > 0:
        left_pct = (fp1_total / total) * 100
        right_pct = (fp2_total / total) * 100
        balance_index = (right_pct - left_pct)  # -100 ~ +100
    else:
        left_pct = right_pct = 50
        balance_index = 0

    # 제목
    ax.text(0, 1.2, '전체 평균 좌뇌/우뇌 균형', ha='center', fontsize=14, fontweight='bold')

    # 반원 게이지 배경 그리기 (wedge 사용)
    from matplotlib.patches import Wedge

    # 좌뇌 영역 (빨강) - 180~135도
    wedge_left = Wedge((0, 0), 1.0, 135, 180, width=0.1,
                       facecolor='#ff5722', edgecolor='none', alpha=0.5)
    ax.add_patch(wedge_left)

    # 균형 영역 (녹색) - 135~45도
    wedge_center = Wedge((0, 0), 1.0, 45, 135, width=0.1,
                         facecolor='#4caf50', edgecolor='none', alpha=0.5)
    ax.add_patch(wedge_center)

    # 우뇌 영역 (파랑) - 45~0도
    wedge_right = Wedge((0, 0), 1.0, 0, 45, width=0.1,
                        facecolor='#2196f3', edgecolor='none', alpha=0.5)
    ax.add_patch(wedge_right)

    # 테두리 원호
    arc_theta = np.linspace(0, np.pi, 100)
    arc_x_inner = 0.9 * np.cos(arc_theta)
    arc_y_inner = 0.9 * np.sin(arc_theta)
    arc_x_outer = 1.0 * np.cos(arc_theta)
    arc_y_outer = 1.0 * np.sin(arc_theta)
    ax.plot(arc_x_inner, arc_y_inner, 'k-', linewidth=2, alpha=0.3)
    ax.plot(arc_x_outer, arc_y_outer, 'k-', linewidth=2, alpha=0.3)

    # 바늘 위치 계산 (-100 좌뇌 ~ +100 우뇌)
    # balance_index: -100(좌뇌) ~ 0(균형) ~ +100(우뇌)
    # 각도: 180도(좌뇌) ~ 90도(균형) ~ 0도(우뇌)
    needle_angle = np.radians(90 - balance_index * 0.9)  # -100->180도, 0->90도, +100->0도
    needle_length = 0.8
    needle_x = needle_length * np.cos(needle_angle)
    needle_y = needle_length * np.sin(needle_angle)

    # 바늘 그리기
    ax.plot([0, needle_x], [0, needle_y], color='black', linewidth=5, zorder=10)
    ax.plot(needle_x, needle_y, 'o', color='red', markersize=10, zorder=11)
    ax.plot(0, 0, 'o', color='black', markersize=18, zorder=12)

    # 라벨
    ax.text(-1.15, 0.0, '좌뇌우세\n(Fp1)', ha='center', va='center', fontsize=11,
            fontweight='bold', color='#ff5722')
    ax.text(0, 1.05, '균형', ha='center', va='bottom', fontsize=11,
            fontweight='bold', color='#4caf50')
    ax.text(1.15, 0.0, '우뇌우세\n(Fp2)', ha='center', va='center', fontsize=11,
            fontweight='bold', color='#2196f3')

    # 수치 표시
    ax.text(0, -0.35, f'좌뇌: {left_pct:.1f}%  |  우뇌: {right_pct:.1f}%',
            ha='center', fontsize=12, fontweight='bold')

    # 상태 표시
    if abs(balance_index) < 10:
        status = '균형'
        status_color = '#4caf50'
    elif balance_index > 0:
        status = '우뇌 우세'
        status_color = '#2196f3'
    else:
        status = '좌뇌 우세'
        status_color = '#ff5722'

    ax.text(0, 0.35, status, ha='center', fontsize=13, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=status_color,
                     edgecolor='white', alpha=0.6, linewidth=2))
