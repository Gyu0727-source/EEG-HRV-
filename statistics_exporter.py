"""
통계 분석 결과 Excel 출력 모듈

참고 파일(01.Results_0128.xlsx) 수준의 상세 통계 생성
"""

import pandas as pd
import numpy as np
import os
import config


def export_detailed_statistics(analysis_result, info):
    """
    상세 통계 분석 결과를 Excel로 출력

    Parameters:
    -----------
    analysis_result : dict
        분석 결과 (analyzer.py의 analyze_eeg 결과)
    info : dict
        파일 정보

    Returns:
    --------
    excel_path : str
        저장된 Excel 파일 경로
    """
    from utils import get_output_paths

    paths = get_output_paths(info)
    excel_path = paths['report_html'].replace('_report.html', '_statistics.xlsx')

    # Excel Writer 생성
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # 1. 기본 정보 시트
        create_basic_info_sheet(writer, analysis_result, info)

        # 2. 절대 파워 시트 (Absolute Power)
        create_absolute_power_sheet(writer, analysis_result, info)

        # 3. 상대 파워 시트 (Relative Power)
        create_relative_power_sheet(writer, analysis_result, info)

        # 4. 좌우 비대칭 시트 (Asymmetry)
        create_asymmetry_sheet(writer, analysis_result, info)

        # 5. HRV 상세 시트
        if 'hrv_metrics' in analysis_result and analysis_result['hrv_metrics']:
            create_hrv_detail_sheet(writer, analysis_result['hrv_metrics'])

        # 6. 시계열 원데이터 시트
        create_timeseries_data_sheet(writer, analysis_result)

    print(f"통계 분석 Excel 저장: {excel_path}")
    return excel_path


def create_basic_info_sheet(writer, analysis_result, info):
    """기본 정보 시트"""
    data = {
        '항목': ['이름', '성별', '나이', '측정 시간(초)', '측정 시간(분)', '샘플링 레이트'],
        '값': [
            info['name'],
            info['gender'],
            info['age'],
            analysis_result['duration'],
            round(analysis_result['duration'] / 60, 1),
            analysis_result['sampling_rate']
        ]
    }
    df = pd.DataFrame(data)
    df.to_excel(writer, sheet_name='기본정보', index=False)


def create_absolute_power_sheet(writer, analysis_result, info):
    """절대 파워 시트 - 시간에 따른 변화 포함"""
    smooth = analysis_result['smooth']
    fp1_powers = analysis_result['fp1_powers']
    fp2_powers = analysis_result['fp2_powers']
    time = analysis_result['time']

    bands = list(config.FREQUENCY_BANDS.keys())

    # 통계 요약
    stats_data = []
    for band in bands:
        band_kr = config.BAND_INFO[band]['name_kr']
        freq_range = config.FREQUENCY_BANDS[band]

        # 전체 평균 (Fp1 + Fp2 평균)
        mean_power = np.mean(smooth[band])
        std_power = np.std(smooth[band])
        min_power = np.min(smooth[band])
        max_power = np.max(smooth[band])

        # 좌뇌/우뇌 개별
        fp1_mean = np.mean(fp1_powers[band])
        fp2_mean = np.mean(fp2_powers[band])

        stats_data.append({
            '주파수대역': f'{band_kr} ({band})',
            '주파수범위(Hz)': f'{freq_range[0]}-{freq_range[1]}',
            '평균(μV²)': round(mean_power, 2),
            '표준편차': round(std_power, 2),
            '최소값': round(min_power, 2),
            '최대값': round(max_power, 2),
            '좌뇌평균(Fp1)': round(fp1_mean, 2),
            '우뇌평균(Fp2)': round(fp2_mean, 2)
        })

    df_stats = pd.DataFrame(stats_data)
    df_stats.to_excel(writer, sheet_name='절대파워_통계', index=False)

    # 시계열 데이터 (샘플링)
    # 전체 데이터가 너무 길면 1초 간격으로 샘플링
    sample_interval = max(1, len(time) // 500)  # 최대 500개 포인트

    timeseries_data = {'시간(초)': time[::sample_interval]}
    for band in bands:
        band_kr = config.BAND_INFO[band]['name_kr']
        timeseries_data[f'{band_kr}_전체'] = smooth[band][::sample_interval]
        timeseries_data[f'{band_kr}_Fp1'] = fp1_powers[band][::sample_interval]
        timeseries_data[f'{band_kr}_Fp2'] = fp2_powers[band][::sample_interval]

    df_timeseries = pd.DataFrame(timeseries_data)
    df_timeseries.to_excel(writer, sheet_name='절대파워_시계열', index=False)


def create_relative_power_sheet(writer, analysis_result, info):
    """상대 파워 시트 - 전체 파워 대비 비율"""
    smooth = analysis_result['smooth']
    fp1_powers = analysis_result['fp1_powers']
    fp2_powers = analysis_result['fp2_powers']

    bands = list(config.FREQUENCY_BANDS.keys())

    # 전체 파워 계산
    total_power = sum(np.mean(smooth[band]) for band in bands)
    fp1_total = sum(np.mean(fp1_powers[band]) for band in bands)
    fp2_total = sum(np.mean(fp2_powers[band]) for band in bands)

    relative_data = []
    for band in bands:
        band_kr = config.BAND_INFO[band]['name_kr']

        # 상대 파워 (%)
        rel_power = (np.mean(smooth[band]) / total_power) * 100 if total_power > 0 else 0
        fp1_rel = (np.mean(fp1_powers[band]) / fp1_total) * 100 if fp1_total > 0 else 0
        fp2_rel = (np.mean(fp2_powers[band]) / fp2_total) * 100 if fp2_total > 0 else 0

        relative_data.append({
            '주파수대역': f'{band_kr} ({band})',
            '상대파워(%)': round(rel_power, 2),
            '좌뇌상대파워(%)': round(fp1_rel, 2),
            '우뇌상대파워(%)': round(fp2_rel, 2)
        })

    df = pd.DataFrame(relative_data)
    df.to_excel(writer, sheet_name='상대파워', index=False)


def create_asymmetry_sheet(writer, analysis_result, info):
    """좌우 비대칭 시트"""
    fp1_powers = analysis_result['fp1_powers']
    fp2_powers = analysis_result['fp2_powers']

    bands = list(config.FREQUENCY_BANDS.keys())

    asymmetry_data = []
    for band in bands:
        band_kr = config.BAND_INFO[band]['name_kr']

        fp1_mean = np.mean(fp1_powers[band])
        fp2_mean = np.mean(fp2_powers[band])

        # 비대칭 지수 계산 방법들
        # 1. 단순 차이
        diff = fp2_mean - fp1_mean

        # 2. 비율
        ratio = fp2_mean / fp1_mean if fp1_mean > 0 else 0

        # 3. 정규화된 비대칭 지수 [-100, +100]
        # 양수: 우뇌 우세, 음수: 좌뇌 우세
        total = fp1_mean + fp2_mean
        asymmetry_index = ((fp2_mean - fp1_mean) / total) * 100 if total > 0 else 0

        asymmetry_data.append({
            '주파수대역': f'{band_kr} ({band})',
            '좌뇌평균(Fp1)': round(fp1_mean, 2),
            '우뇌평균(Fp2)': round(fp2_mean, 2),
            '차이(Fp2-Fp1)': round(diff, 2),
            '비율(Fp2/Fp1)': round(ratio, 2),
            '비대칭지수': round(asymmetry_index, 1),
            '우세반구': '우뇌' if asymmetry_index > 5 else ('좌뇌' if asymmetry_index < -5 else '균형')
        })

    df = pd.DataFrame(asymmetry_data)
    df.to_excel(writer, sheet_name='좌우비대칭', index=False)


def create_hrv_detail_sheet(writer, hrv_metrics):
    """HRV 상세 시트"""
    time_domain = hrv_metrics['time_domain']
    freq_domain = hrv_metrics['frequency_domain']
    interp = hrv_metrics['interpretation']
    quality = hrv_metrics.get('quality', 'unknown')

    hrv_data = {
        '지표': [
            'Mean HR (bpm)',
            'SDNN (ms)',
            'RMSSD (ms)',
            'pNN50 (%)',
            'VLF Power',
            'LF Power',
            'HF Power',
            'Total Power',
            'LF/HF Ratio',
            'LF Norm (%)',
            'HF Norm (%)',
            '데이터품질',
            '스트레스수준',
            '자율신경균형',
            '부교감신경상태',
            '교감신경상태'
        ],
        '값': [
            time_domain['mean_hr'],
            time_domain['sdnn'],
            time_domain['rmssd'],
            time_domain['pnn50'],
            freq_domain['vlf'],
            freq_domain['lf'],
            freq_domain['hf'],
            freq_domain['total_power'],
            freq_domain['lf_hf_ratio'],
            freq_domain['lf_norm'],
            freq_domain['hf_norm'],
            quality,
            interp['stress_level'],
            interp['autonomic_balance'],
            interp['parasympathetic_status'],
            interp['sympathetic_status']
        ]
    }

    df = pd.DataFrame(hrv_data)
    df.to_excel(writer, sheet_name='HRV상세', index=False)


def create_timeseries_data_sheet(writer, analysis_result):
    """시계열 원데이터 시트 (전체 데이터)"""
    smooth = analysis_result['smooth']
    time = analysis_result['time']

    bands = list(config.FREQUENCY_BANDS.keys())

    # 데이터가 너무 크면 Excel 한계(1,048,576행)를 고려하여 샘플링
    max_rows = 100000
    if len(time) > max_rows:
        sample_interval = len(time) // max_rows + 1
    else:
        sample_interval = 1

    data = {'시간(초)': time[::sample_interval]}
    for band in bands:
        band_kr = config.BAND_INFO[band]['name_kr']
        data[band_kr] = smooth[band][::sample_interval]

    df = pd.DataFrame(data)
    df.to_excel(writer, sheet_name='시계열원데이터', index=False)
