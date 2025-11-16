"""
EEG 실시간 분석 프로젝트 - 메인 실행 파일

사용법:
1. 단일 파일: python main.py --file "경로/파일명.xlsx"
2. 폴더 배치: python main.py --folder "경로/폴더명/"
3. 대화형: python main.py
"""

import os
import sys
import argparse
from glob import glob
import traceback

# 로컬 모듈 임포트
import config
import utils
import analyzer
import graph_generator_v2 as graph_generator
import report_generator_v2 as report_generator


def initialize_project():
    """프로젝트 폴더 구조 초기화"""
    folders = [
        config.RAW_DATA_DIR,
        config.ANALYSIS_DATA_DIR,
        config.REPORTS_DIR,
        config.GRAPHS_DIR,
        config.TEMPLATES_DIR
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    print("프로젝트 폴더 구조 초기화 완료")


def process_single_file(raw_file):
    """
    단일 파일 처리 파이프라인

    Parameters:
    -----------
    raw_file : str
        원시 데이터 파일 경로

    Returns:
    --------
    success : bool
        처리 성공 여부
    """
    try:
        print(f"\n{'='*60}")
        print(f"처리 시작: {os.path.basename(raw_file)}")
        print(f"{'='*60}")

        # 1. 파일명 파싱
        info = utils.parse_filename(raw_file)
        print(f"이름: {info['name']}, 성별: {info['gender']}, 나이: {info['age']}")

        # 2. 원시 데이터 복사
        raw_path = utils.copy_to_raw_data(raw_file, info)

        # 3. 뇌파 분석
        print("\n뇌파 분석 중...")
        analysis_result = analyzer.analyze_eeg(raw_path, info)

        # 4. 분석 데이터 저장
        print("\n분석 데이터 저장 중...")
        utils.save_analysis_data(analysis_result, info)
        utils.save_metadata(analysis_result, info)

        # 5. 그래프 생성
        print("\n그래프 생성 중...")
        graph_paths = graph_generator.generate_graphs(analysis_result, info)

        # 6. 해석 생성
        print("\n해석 생성 중...")
        interpretations = report_generator.generate_interpretations(analysis_result)

        # 7. HTML 보고서 생성
        print("\nHTML 보고서 생성 중...")
        html_path = report_generator.generate_report(info, graph_paths, interpretations, analysis_result)

        # 8. PDF 변환
        print("\nPDF 변환 중...")
        pdf_path = report_generator.convert_to_pdf(html_path, info)

        # 9. 통계 분석 Excel 생성
        print("\n통계 분석 Excel 생성 중...")
        import statistics_exporter
        excel_path = statistics_exporter.export_detailed_statistics(analysis_result, info)

        print(f"\n{'='*60}")
        print(f"처리 완료: {info['name']}_{info['gender']}_{info['age']}")
        print(f"{'='*60}")
        print(f"HTML 보고서: {html_path}")
        if pdf_path:
            print(f"PDF 보고서: {pdf_path}")
        print(f"통계 Excel: {excel_path}")

        return True

    except Exception as e:
        print(f"\n에러 발생: {raw_file}")
        print(f"에러 메시지: {str(e)}")
        traceback.print_exc()
        return False


def process_batch(raw_files):
    """
    배치 처리

    Parameters:
    -----------
    raw_files : list of str
        원시 데이터 파일 경로 리스트

    Returns:
    --------
    results : dict
        {'success': int, 'failed': int, 'total': int}
    """
    total = len(raw_files)
    success_count = 0
    failed_count = 0

    print(f"\n총 {total}개 파일 배치 처리 시작")
    print("="*60)

    for i, raw_file in enumerate(raw_files, 1):
        print(f"\n[{i}/{total}] 처리 중...")

        if process_single_file(raw_file):
            success_count += 1
        else:
            failed_count += 1

    print(f"\n{'='*60}")
    print(f"배치 처리 완료")
    print(f"{'='*60}")
    print(f"성공: {success_count}개")
    print(f"실패: {failed_count}개")
    print(f"전체: {total}개")

    return {
        'success': success_count,
        'failed': failed_count,
        'total': total
    }


def interactive_mode():
    """대화형 모드"""
    print("\n" + "="*60)
    print("EEG 실시간 분석 시스템 - 대화형 모드")
    print("="*60)

    while True:
        print("\n옵션을 선택하세요:")
        print("1. 단일 파일 처리")
        print("2. 폴더 전체 처리")
        print("3. 종료")

        choice = input("\n선택 (1/2/3): ").strip()

        if choice == '1':
            file_path = input("파일 경로 입력: ").strip().strip('"')
            if os.path.exists(file_path):
                process_single_file(file_path)
            else:
                print(f"파일을 찾을 수 없습니다: {file_path}")

        elif choice == '2':
            folder_path = input("폴더 경로 입력: ").strip().strip('"')
            if os.path.isdir(folder_path):
                # Excel 및 CSV 파일 찾기
                patterns = ['*.xlsx', '*.xls', '*.csv', '*.txt']
                files = []
                for pattern in patterns:
                    files.extend(glob(os.path.join(folder_path, pattern)))

                if files:
                    print(f"\n발견된 파일: {len(files)}개")
                    for f in files:
                        print(f"  - {os.path.basename(f)}")

                    confirm = input("\n처리를 시작하시겠습니까? (y/n): ").strip().lower()
                    if confirm == 'y':
                        process_batch(files)
                else:
                    print("처리 가능한 파일이 없습니다.")
            else:
                print(f"폴더를 찾을 수 없습니다: {folder_path}")

        elif choice == '3':
            print("\n프로그램을 종료합니다.")
            break

        else:
            print("잘못된 선택입니다. 1, 2, 또는 3을 입력하세요.")


def main():
    """메인 함수"""
    # 프로젝트 초기화
    initialize_project()

    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(description='EEG 실시간 분석 시스템')
    parser.add_argument('--file', type=str, help='단일 파일 경로')
    parser.add_argument('--folder', type=str, help='폴더 경로 (배치 처리)')

    args = parser.parse_args()

    # 모드 선택
    if args.file:
        # 단일 파일 모드
        if os.path.exists(args.file):
            process_single_file(args.file)
        else:
            print(f"파일을 찾을 수 없습니다: {args.file}")
            sys.exit(1)

    elif args.folder:
        # 배치 모드
        if os.path.isdir(args.folder):
            # Excel 및 CSV 파일 찾기
            patterns = ['*.xlsx', '*.xls', '*.csv', '*.txt']
            files = []
            for pattern in patterns:
                files.extend(glob(os.path.join(args.folder, pattern)))

            if files:
                process_batch(files)
            else:
                print("처리 가능한 파일이 없습니다.")
                sys.exit(1)
        else:
            print(f"폴더를 찾을 수 없습니다: {args.folder}")
            sys.exit(1)

    else:
        # 대화형 모드
        interactive_mode()


if __name__ == "__main__":
    main()
