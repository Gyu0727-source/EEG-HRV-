"""
시스템 설정 테스트 스크립트
패키지 설치 없이 기본 구조 확인
"""

import os
import sys

def test_file_structure():
    """파일 구조 확인"""
    print("="*60)
    print("파일 구조 테스트")
    print("="*60)

    required_files = [
        'main.py',
        'config.py',
        'utils.py',
        'analyzer.py',
        'graph_generator.py',
        'report_generator.py',
        'requirements.txt',
        'templates/report_template.html'
    ]

    all_exist = True
    for filepath in required_files:
        exists = os.path.exists(filepath)
        status = "✓" if exists else "✗"
        print(f"{status} {filepath}")
        if not exists:
            all_exist = False

    print()
    if all_exist:
        print("✅ 모든 필수 파일이 존재합니다!")
    else:
        print("❌ 일부 파일이 누락되었습니다.")

    return all_exist


def test_imports():
    """Python 모듈 임포트 테스트"""
    print("\n" + "="*60)
    print("Python 모듈 임포트 테스트")
    print("="*60)

    modules_to_test = [
        ('config', '설정 모듈'),
        ('utils', '유틸리티 모듈'),
        ('analyzer', '분석 모듈'),
        ('graph_generator', '그래프 생성 모듈'),
        ('report_generator', '보고서 생성 모듈')
    ]

    all_imported = True
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {description} ({module_name})")
        except ImportError as e:
            print(f"✗ {description} ({module_name}) - 오류: {e}")
            all_imported = False

    print()
    if all_imported:
        print("✅ 모든 모듈을 임포트할 수 있습니다!")
    else:
        print("❌ 일부 모듈 임포트에 실패했습니다.")
        print("   필요한 패키지를 설치하세요: pip install -r requirements.txt")

    return all_imported


def test_folders():
    """폴더 구조 확인 및 생성"""
    print("\n" + "="*60)
    print("폴더 구조 테스트")
    print("="*60)

    required_folders = [
        'raw_data',
        'analysis_data',
        'reports',
        'graphs',
        'templates'
    ]

    for folder in required_folders:
        if os.path.exists(folder):
            print(f"✓ {folder}/ (존재)")
        else:
            os.makedirs(folder, exist_ok=True)
            print(f"✓ {folder}/ (생성됨)")

    print("\n✅ 모든 필요한 폴더가 준비되었습니다!")
    return True


def test_data_files():
    """테스트 데이터 파일 확인"""
    print("\n" + "="*60)
    print("테스트 데이터 파일 확인")
    print("="*60)

    test_folder = "분석 데이터"

    if not os.path.exists(test_folder):
        print(f"❌ '{test_folder}' 폴더를 찾을 수 없습니다.")
        return False

    import glob
    test_files = glob.glob(os.path.join(test_folder, "*.xlsx"))

    print(f"발견된 테스트 파일: {len(test_files)}개\n")
    for i, filepath in enumerate(test_files, 1):
        filename = os.path.basename(filepath)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  {i}. {filename} ({size_mb:.2f} MB)")

    if test_files:
        print(f"\n✅ {len(test_files)}개의 테스트 파일이 준비되어 있습니다!")
        return True
    else:
        print("\n❌ 테스트 파일이 없습니다.")
        return False


def main():
    """메인 테스트"""
    print("\n")
    print("🧠 EEG 실시간 분석 시스템 - 설정 테스트")
    print("="*60)
    print()

    # 작업 디렉토리 확인
    cwd = os.getcwd()
    print(f"현재 디렉토리: {cwd}\n")

    # 테스트 실행
    results = {}
    results['files'] = test_file_structure()
    results['folders'] = test_folders()
    results['data'] = test_data_files()
    results['imports'] = test_imports()

    # 최종 결과
    print("\n" + "="*60)
    print("최종 결과")
    print("="*60)

    if all(results.values()):
        print("✅ 모든 테스트 통과!")
        print("\n다음 단계:")
        print("1. pip install -r requirements.txt")
        print("2. python main.py --folder \"분석 데이터\"")
    else:
        print("⚠️ 일부 테스트 실패")
        print("\n조치 사항:")
        if not results['imports']:
            print("- pip install -r requirements.txt 실행")
        if not results['data']:
            print("- 테스트 데이터 파일 준비")

    print()


if __name__ == "__main__":
    main()
