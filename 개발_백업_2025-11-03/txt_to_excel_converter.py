"""
BrainBay TXT 파일을 Excel로 변환하는 간단한 스크립트

BrainBay에서 ARC → TXT 변환 후,
이 스크립트로 TXT → Excel (Fp1, Fp2 추출) 자동화
"""

import pandas as pd
import os
import glob


def convert_brainbay_txt_to_excel(txt_path, output_excel_path=None):
    """
    BrainBay TXT 파일을 Excel로 변환

    Parameters:
    -----------
    txt_path : str
        BrainBay에서 생성한 TXT 파일 경로
    output_excel_path : str, optional
        출력 Excel 파일 경로 (기본값: 같은 이름.xlsx)

    Returns:
    --------
    output_excel_path : str
        생성된 Excel 파일 경로
    """
    # TXT 파일 읽기 (CSV 형식, comma separated)
    df = pd.read_csv(txt_path)

    print(f"파일 로드: {txt_path}")
    print(f"행 개수: {len(df)}")
    print(f"컬럼 개수: {len(df.columns)}")

    # 출력 경로 설정
    if output_excel_path is None:
        output_excel_path = txt_path.replace('.txt', '.xlsx')

    # Excel로 저장
    df.to_excel(output_excel_path, index=False)

    print(f"Excel 저장 완료: {output_excel_path}")

    return output_excel_path


def extract_fp1_fp2_ppg(txt_path, output_excel_path=None):
    """
    BrainBay TXT에서 Fp1, Fp2, PPG 추출하여 Excel로 저장

    분석 시스템에 필요한 컬럼:
    - Fp1 (컬럼 1): 좌뇌 EEG
    - Fp2 (컬럼 2): 우뇌 EEG
    - PPG (컬럼 3): 심박 측정 (HRV 분석용)

    Parameters:
    -----------
    txt_path : str
        BrainBay TXT 파일
    output_excel_path : str, optional
        출력 Excel 파일 경로

    Returns:
    --------
    output_excel_path : str
        생성된 Excel 파일 경로
    """
    # TXT 파일 읽기
    df = pd.read_csv(txt_path)

    # 첫 3개 컬럼 추출 (Fp1, Fp2, PPG)
    analysis_df = df.iloc[:, :3].copy()
    analysis_df.columns = ['Fp1', 'Fp2', 'PPG']

    # Sample Index 추가
    analysis_df.insert(0, 'Sample Index', range(len(analysis_df)))

    # 출력 경로 설정
    if output_excel_path is None:
        output_excel_path = txt_path.replace('.txt', '_analysis_ready.xlsx')

    # Excel로 저장
    analysis_df.to_excel(output_excel_path, index=False)

    print(f"Fp1/Fp2/PPG 추출 완료: {output_excel_path}")
    print(f"행 개수: {len(analysis_df)}")
    print(f"컬럼: {analysis_df.columns.tolist()}")

    return output_excel_path


def batch_convert_txt_folder(txt_folder, output_folder=None, mode='analysis'):
    """
    폴더 내 모든 TXT 파일을 Excel로 일괄 변환

    Parameters:
    -----------
    txt_folder : str
        TXT 파일이 있는 폴더
    output_folder : str, optional
        출력 폴더 (기본값: txt_folder/excel_output)
    mode : str
        'analysis': Fp1/Fp2/PPG 추출 (분석용, 기본값)
        'full': 전체 컬럼 변환

    Returns:
    --------
    converted_files : list
        변환된 파일 경로 리스트
    """
    if output_folder is None:
        output_folder = os.path.join(txt_folder, 'excel_output')

    os.makedirs(output_folder, exist_ok=True)

    txt_files = glob.glob(os.path.join(txt_folder, '*.txt'))
    converted_files = []

    print(f"총 {len(txt_files)}개의 TXT 파일 발견")
    print(f"출력 폴더: {output_folder}")
    print(f"모드: {'Fp1/Fp2/PPG 추출 (분석용)' if mode == 'analysis' else '전체 컬럼'}")
    print("=" * 60)

    for idx, txt_file in enumerate(txt_files, 1):
        filename = os.path.basename(txt_file)

        if mode == 'analysis':
            excel_file = filename.replace('.txt', '_analysis_ready.xlsx')
        else:
            excel_file = filename.replace('.txt', '.xlsx')

        excel_path = os.path.join(output_folder, excel_file)

        print(f"\n[{idx}/{len(txt_files)}] {filename}")

        try:
            if mode == 'analysis':
                extract_fp1_fp2_ppg(txt_file, excel_path)
            else:
                convert_brainbay_txt_to_excel(txt_file, excel_path)

            converted_files.append(excel_path)
        except Exception as e:
            print(f"오류 발생: {e}")

    print("\n" + "=" * 60)
    print(f"변환 완료: {len(converted_files)}/{len(txt_files)} 파일")

    return converted_files


def parse_filename(filename):
    """
    파일명에서 이름, 성별, 나이 추출
    예: "07.이찬희 호흡.txt" → ("이찬희", "남", 28)

    Note: 성별과 나이는 별도 매핑 필요
    """
    # 번호 제거
    name_part = filename.split('.', 1)[1] if '.' in filename else filename
    # .txt 제거
    name_part = name_part.replace('.txt', '')
    # 활동 제거 (호흡, 숫자, 잔상 등)
    name = name_part.split()[0] if ' ' in name_part else name_part

    return name


if __name__ == "__main__":
    import sys

    # 사용 예시
    if len(sys.argv) > 1:
        # 명령행 인자로 폴더 경로 받기
        folder_path = sys.argv[1]
        mode = 'full' if '--full' in sys.argv else 'analysis'

        batch_convert_txt_folder(folder_path, mode=mode)
    else:
        # 기본 테스트
        txt_folder = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일"

        print("=" * 60)
        print("BrainBay TXT → Excel 변환 도구")
        print("=" * 60)
        print("\n옵션:")
        print("1. 분석용 변환 (Fp1/Fp2/PPG만 추출) - 권장")
        print("2. 전체 컬럼 변환")
        print()

        choice = input("선택 (1 또는 2, 기본값=1): ").strip()

        mode = 'full' if choice == '2' else 'analysis'

        batch_convert_txt_folder(txt_folder, mode=mode)

        print("\n변환 완료!")
        print("\n사용법:")
        print("  python txt_to_excel_converter.py <폴더경로>              # 분석용 (기본)")
        print("  python txt_to_excel_converter.py <폴더경로> --full      # 전체 컬럼")
