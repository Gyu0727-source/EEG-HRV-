"""
ARC 파일 완전 자동화 분석 시스템

ARC 파일 → Excel → 분석 결과 (한 번에!)
"""

import os
import sys
import pandas as pd
from arc_reader_v5_sync import ARCReaderV5


def arc_to_excel(arc_path, output_excel_path=None):
    """
    ARC 파일을 분석용 Excel로 변환

    Parameters:
    -----------
    arc_path : str
        입력 ARC 파일 경로
    output_excel_path : str, optional
        출력 Excel 파일 경로 (기본값: ARC 파일과 같은 이름.xlsx)

    Returns:
    --------
    output_excel_path : str
        생성된 Excel 파일 경로
    """
    if output_excel_path is None:
        output_excel_path = arc_path.replace('.arc', '_analysis_ready.xlsx')

    print(f"[1단계] ARC 파일 파싱: {os.path.basename(arc_path)}")

    # ARC 파일 읽기
    reader = ARCReaderV5(arc_path)
    data = reader.read()

    if data is None:
        print("  [FAIL] ARC 파일 파싱 실패!")
        return None

    # Fp1, Fp2, PPG 추출
    analysis_df = reader.get_fp1_fp2_ppg()

    # Excel로 저장
    analysis_df.to_excel(output_excel_path, index=False)

    print(f"  [OK] Excel 생성 완료: {os.path.basename(output_excel_path)}")
    print(f"  [OK] 행 개수: {len(analysis_df):,}")

    return output_excel_path


def batch_convert_arc_folder(arc_folder, output_folder=None):
    """
    폴더 내 모든 ARC 파일을 Excel로 일괄 변환

    Parameters:
    -----------
    arc_folder : str
        ARC 파일이 있는 폴더
    output_folder : str, optional
        출력 폴더 (기본값: arc_folder/excel_output)

    Returns:
    --------
    converted_files : list
        변환된 Excel 파일 경로 리스트
    """
    import glob

    if output_folder is None:
        output_folder = os.path.join(arc_folder, 'excel_output_from_arc')

    os.makedirs(output_folder, exist_ok=True)

    arc_files = glob.glob(os.path.join(arc_folder, '*.arc'))
    converted_files = []

    print("=" * 80)
    print("ARC → Excel 일괄 변환")
    print("=" * 80)
    print(f"총 {len(arc_files)}개의 ARC 파일 발견")
    print(f"출력 폴더: {output_folder}")
    print("=" * 80)

    for idx, arc_file in enumerate(arc_files, 1):
        filename = os.path.basename(arc_file)
        excel_file = filename.replace('.arc', '_analysis_ready.xlsx')
        excel_path = os.path.join(output_folder, excel_file)

        print(f"\n[{idx}/{len(arc_files)}] {filename}")

        try:
            result = arc_to_excel(arc_file, excel_path)
            if result:
                converted_files.append(excel_path)
        except Exception as e:
            print(f"  [FAIL] 오류 발생: {e}")

    print("\n" + "=" * 80)
    print(f"변환 완료: {len(converted_files)}/{len(arc_files)} 파일")
    print("=" * 80)

    return converted_files


def arc_to_full_analysis(arc_path, name=None, gender=None, age=None):
    """
    ARC 파일을 분석까지 완전 자동 실행

    Parameters:
    -----------
    arc_path : str
        입력 ARC 파일 경로
    name : str, optional
        피험자 이름
    gender : str, optional
        성별 (남/여)
    age : int, optional
        나이

    Returns:
    --------
    result_paths : dict
        생성된 파일들의 경로
    """
    import subprocess

    print("=" * 80)
    print("ARC 파일 완전 자동 분석")
    print("=" * 80)

    # 1. ARC → Excel
    excel_path = arc_to_excel(arc_path)

    if not excel_path:
        print("[FAIL] Excel 변환 실패!")
        return None

    # 2. 분석 실행
    print(f"\n[2단계] EEG 분석 실행...")

    # main.py 실행 명령어 구성
    cmd = [
        sys.executable,
        'main.py',
        '--file', excel_path
    ]

    if name:
        cmd.extend(['--name', name])
    if gender:
        cmd.extend(['--gender', gender])
    if age:
        cmd.extend(['--age', str(age)])

    # 분석 실행
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("  [OK] 분석 완료!")
        print("\n결과 파일:")
        print(f"  - Excel: {excel_path}")
        print(f"  - 그래프: graphs/ 폴더")
        print(f"  - 리포트: reports/ 폴더")

        return {
            'excel': excel_path,
            'status': 'success'
        }
    else:
        print(f"  [FAIL] 분석 실패!")
        print(f"  오류: {result.stderr}")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='ARC 파일 자동 분석 시스템')
    parser.add_argument('--file', help='단일 ARC 파일 경로')
    parser.add_argument('--folder', help='ARC 파일이 있는 폴더')
    parser.add_argument('--name', help='피험자 이름')
    parser.add_argument('--gender', help='성별 (남/여)')
    parser.add_argument('--age', type=int, help='나이')
    parser.add_argument('--convert-only', action='store_true', help='Excel 변환만 (분석 안 함)')

    args = parser.parse_args()

    if args.file:
        # 단일 파일 처리
        if args.convert_only:
            arc_to_excel(args.file)
        else:
            arc_to_full_analysis(args.file, args.name, args.gender, args.age)

    elif args.folder:
        # 폴더 배치 처리
        converted_files = batch_convert_arc_folder(args.folder)

        if not args.convert_only and converted_files:
            print(f"\n[3단계] 모든 Excel 파일 분석...")

            import subprocess
            result = subprocess.run([
                sys.executable,
                'main.py',
                '--folder', os.path.join(args.folder, 'excel_output_from_arc')
            ])

            if result.returncode == 0:
                print("\n[OK] 전체 분석 완료!")

    else:
        # 기본 테스트
        test_arc = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 호흡.arc"

        print("=" * 80)
        print("기본 테스트 실행")
        print("=" * 80)

        # 변환만 테스트
        excel_path = arc_to_excel(test_arc)

        if excel_path:
            print(f"\n[OK] 성공! Excel 파일: {excel_path}")

        print("\n사용법:")
        print("  # 단일 파일 변환")
        print("  python arc_to_analysis_auto.py --file <ARC파일> --convert-only")
        print()
        print("  # 단일 파일 분석")
        print("  python arc_to_analysis_auto.py --file <ARC파일> --name 이름 --gender 남 --age 28")
        print()
        print("  # 폴더 전체 변환")
        print("  python arc_to_analysis_auto.py --folder <ARC폴더> --convert-only")
        print()
        print("  # 폴더 전체 분석")
        print("  python arc_to_analysis_auto.py --folder <ARC폴더>")
