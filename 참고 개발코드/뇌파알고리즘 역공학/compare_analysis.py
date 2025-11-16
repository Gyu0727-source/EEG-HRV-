from eeg_analysis import EEGAnalyzer
import pandas as pd

def analyze_and_compare():
    analyzer = EEGAnalyzer()
    
    # 두 파일 분석
    files = {
        "숫자": "./숫자 호흡 잔상/01.이선미 숫자.txt",
        "잔상": "./숫자 호흡 잔상/01.이선미 잔상.txt"
    }
    
    results = {}
    
    for test_type, file_path in files.items():
        print(f"\n=== {test_type} 테스트 분석 ===")
        data = analyzer.load_data(file_path)
        if data:
            result = analyzer.analyze_eeg_data(data)
            results[test_type] = result
            
            print(f"뇌 건강 점수: {result['health_score']:.1f}점 ({result['health_status']})")
            print(f"뇌 활성도: {result['comprehensive_metrics']['activity_ratio']:.3f}")
            print(f"뇌 유연성: {result['comprehensive_metrics']['flexibility']:.3f}")
            print(f"뇌 균형도: {result['comprehensive_metrics']['balance']:.3f}")
            
            hrv = result['comprehensive_metrics']['hrv']
            print(f"HRV - RMSSD: {hrv['RMSSD']:.1f}ms, SDNN: {hrv['SDNN']:.1f}ms, pNN50: {hrv['pNN50']:.1f}%")
    
    # 비교 분석
    if len(results) == 2:
        print(f"\n=== 비교 분석 ===")
        숫자_result = results["숫자"]
        잔상_result = results["잔상"]
        
        print(f"뇌 건강 점수 차이: {잔상_result['health_score'] - 숫자_result['health_score']:.1f}점")
        print(f"뇌 활성도 차이: {잔상_result['comprehensive_metrics']['activity_ratio'] - 숫자_result['comprehensive_metrics']['activity_ratio']:.3f}")
        print(f"뇌 유연성 차이: {잔상_result['comprehensive_metrics']['flexibility'] - 숫자_result['comprehensive_metrics']['flexibility']:.3f}")
        print(f"뇌 균형도 차이: {잔상_result['comprehensive_metrics']['balance'] - 숫자_result['comprehensive_metrics']['balance']:.3f}")
        
        # 주파수 대역별 비교
        print(f"\n주파수 대역별 상대 파워 비교 (EEG1):")
        for band in 숫자_result['EEG1']['relative_powers'].keys():
            숫자_power = 숫자_result['EEG1']['relative_powers'][band]
            잔상_power = 잔상_result['EEG1']['relative_powers'][band]
            차이 = 잔상_power - 숫자_power
            print(f"  {band.upper()}: 숫자 {숫자_power:.3f} → 잔상 {잔상_power:.3f} (차이: {차이:+.3f})")

if __name__ == "__main__":
    analyze_and_compare()