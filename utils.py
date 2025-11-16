"""
EEG 실시간 분석 프로젝트 - 유틸리티 함수
"""

import os
import re
import shutil
import pandas as pd
import numpy as np
from datetime import datetime
import config


def parse_filename(filepath):
    """
    파일명에서 정보 파싱

    형식: 이름_나이_성별.xlsx 또는 이름_성별_나이.xlsx
    예: 노인규_남_35.xlsx 또는 김영희_여_28.xlsx

    Returns:
    --------
    info : dict
        {'name': str, 'gender': str, 'age': int, 'base_filename': str}
    """
    filename = os.path.basename(filepath)
    base_filename = os.path.splitext(filename)[0]

    # 공백으로 구분된 경우도 처리 (예: "김선근 44 남.xlsx")
    parts = re.split(r'[_\s]+', base_filename)

    if len(parts) < 3:
        raise ValueError(f"파일명 형식이 올바르지 않습니다: {filename}\n형식: 이름_성별_나이 또는 이름_나이_성별")

    # 패턴 매칭
    name = None
    gender = None
    age = None

    for part in parts:
        if part in ['남', '여', 'M', 'F', 'male', 'female']:
            gender = '남' if part in ['남', 'M', 'male'] else '여'
        elif part.isdigit():
            age = int(part)
        else:
            if name is None:
                name = part

    if not all([name, gender, age]):
        raise ValueError(f"파일명에서 정보를 추출할 수 없습니다: {filename}")

    return {
        'name': name,
        'gender': gender,
        'age': age,
        'base_filename': base_filename,
        'original_path': filepath
    }


def load_raw_data(filepath):
    """
    원시 EEG 데이터 로드 (Excel 또는 CSV)

    Returns:
    --------
    data : dict
        {'Fp1': ndarray, 'Fp2': ndarray, 'sampling_rate': int, 'duration': float}
    """
    print(f"데이터 로딩: {filepath}")

    try:
        # Excel 파일 로드
        if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            df = pd.read_excel(filepath, header=None)
        else:
            # CSV 또는 TXT 파일
            df = pd.read_csv(filepath, header=None, sep=None, engine='python')

        print(f"데이터 형태: {df.shape}")

        # 첫 두 컬럼을 Fp1, Fp2로 간주
        if df.shape[1] < 2:
            raise ValueError("데이터에 최소 2개의 채널이 필요합니다 (Fp1, Fp2)")

        # 데이터 정리 (문자열 제거, 숫자 변환)
        def clean_column(col):
            if col.dtype == object:
                # 쉼표와 따옴표 제거
                cleaned = col.astype(str).str.replace(',', '').str.replace('"', '').str.strip()
                return pd.to_numeric(cleaned, errors='coerce').fillna(0).values
            else:
                return pd.to_numeric(col, errors='coerce').fillna(0).values

        fp1 = clean_column(df.iloc[:, 0])
        fp2 = clean_column(df.iloc[:, 1])

        # 샘플링 레이트와 지속 시간 계산
        sampling_rate = config.SAMPLING_RATE
        duration = len(fp1) / sampling_rate

        print(f"Fp1 범위: {np.min(fp1):.2f} ~ {np.max(fp1):.2f}")
        print(f"Fp2 범위: {np.min(fp2):.2f} ~ {np.max(fp2):.2f}")
        print(f"측정 시간: {duration:.1f}초 ({duration/60:.1f}분)")

        # 최소 측정 시간 확인 (60초 이상)
        if duration < 60:
            print(f"경고: 측정 시간이 너무 짧습니다 ({duration:.1f}초). 최소 60초 이상 권장.")

        return {
            'Fp1': fp1,
            'Fp2': fp2,
            'sampling_rate': sampling_rate,
            'duration': duration
        }

    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        raise


def copy_to_raw_data(source_path, info):
    """
    원시 데이터를 raw_data 폴더로 복사

    Parameters:
    -----------
    source_path : str
        원본 파일 경로
    info : dict
        파일 정보 (parse_filename 결과)

    Returns:
    --------
    dest_path : str
        복사된 파일 경로
    """
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)

    # 목적지 파일명: 이름_성별_나이.확장자
    ext = os.path.splitext(source_path)[1]
    dest_filename = f"{info['name']}_{info['gender']}_{info['age']}{ext}"
    dest_path = os.path.join(config.RAW_DATA_DIR, dest_filename)

    # 파일 복사
    if not os.path.exists(dest_path):
        shutil.copy2(source_path, dest_path)
        print(f"원시 데이터 복사: {dest_path}")
    else:
        print(f"원시 데이터 이미 존재: {dest_path}")

    return dest_path


def save_analysis_data(analysis_result, info):
    """
    분석 데이터를 CSV로 저장

    Parameters:
    -----------
    analysis_result : dict
        분석 결과 (analyzer.py의 analyze_eeg 결과)
    info : dict
        파일 정보
    """
    os.makedirs(config.ANALYSIS_DATA_DIR, exist_ok=True)

    # CSV 파일명
    csv_filename = f"{info['name']}_{info['gender']}_{info['age']}_analysis.csv"
    csv_path = os.path.join(config.ANALYSIS_DATA_DIR, csv_filename)

    # 데이터프레임 생성
    time_array = analysis_result['time']
    data_dict = {'time_sec': time_array}

    # 각 주파수 대역별 raw와 smooth 데이터 추가
    for band in config.FREQUENCY_BANDS.keys():
        data_dict[f'{band}_raw'] = analysis_result['raw'][band]
        data_dict[f'{band}_smooth'] = analysis_result['smooth'][band]

    df = pd.DataFrame(data_dict)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"분석 데이터 저장: {csv_path}")

    return csv_path


def save_metadata(analysis_result, info):
    """
    메타데이터를 JSON으로 저장

    Parameters:
    -----------
    analysis_result : dict
        분석 결과
    info : dict
        파일 정보
    """
    import json

    os.makedirs(config.ANALYSIS_DATA_DIR, exist_ok=True)

    # JSON 파일명
    json_filename = f"{info['name']}_{info['gender']}_{info['age']}_metadata.json"
    json_path = os.path.join(config.ANALYSIS_DATA_DIR, json_filename)

    # 메타데이터 구성
    metadata = {
        'name': info['name'],
        'gender': info['gender'],
        'age': info['age'],
        'measurement_date': datetime.now().strftime('%Y-%m-%d'),
        'duration_seconds': int(analysis_result['duration']),
        'sampling_rate': analysis_result['sampling_rate'],
        'window_size': config.WINDOW_SIZE,
        'overlap': config.OVERLAP,
        'change_points': {},
        'change_types': {}
    }

    # 변화점 정보 추가
    for band in config.FREQUENCY_BANDS.keys():
        if band in analysis_result['change_points']:
            metadata['change_points'][band] = [int(cp) for cp in analysis_result['change_points'][band]]
            metadata['change_types'][band] = analysis_result['change_types'][band]

    # JSON 저장
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"메타데이터 저장: {json_path}")

    return json_path


def get_output_paths(info):
    """
    출력 파일 경로들을 생성

    Returns:
    --------
    paths : dict
        {'graphs': dict, 'report_html': str, 'report_pdf': str}
    """
    base_name = f"{info['name']}_{info['gender']}_{info['age']}"

    paths = {
        'graphs': {},
        'report_html': os.path.join(config.REPORTS_DIR, f"{base_name}_report.html"),
        'report_pdf': os.path.join(config.REPORTS_DIR, f"{base_name}_report.pdf")
    }

    # 각 주파수 대역별 그래프 경로
    for band in config.FREQUENCY_BANDS.keys():
        paths['graphs'][band] = os.path.join(config.GRAPHS_DIR, f"{base_name}_{band}.png")

    return paths
