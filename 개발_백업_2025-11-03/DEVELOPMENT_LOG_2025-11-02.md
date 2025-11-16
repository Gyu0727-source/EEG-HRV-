# EEG 실시간 분석 시스템 개발 로그
**작성일**: 2025년 11월 2일
**프로젝트**: EEG 실시간 분석 데이터 처리 시스템

---

## 프로젝트 개요

### 목적
- 2채널 EEG 데이터(Fp1, Fp2) 실시간 분석 시스템 구축
- 뇌파 주파수 대역 분석 및 시각화
- 심박변이도(HRV) 분석 추가
- 좌뇌/우뇌 균형도 분석
- 연구용 상세 통계 데이터 생성

### 데이터 사양
- **채널**: Fp1(좌뇌), Fp2(우뇌)
- **샘플링 레이트**: 250Hz
- **분석 윈도우**: 2초 (50% 오버랩)
- **주파수 대역**: Delta, Theta, Alpha, Low Beta, High Beta, Gamma

---

## 시스템 아키텍처

### 핵심 모듈 구조

```
01.EEG실시간 분석 데이터/
├── main.py                    # 메인 실행 파일
├── config.py                  # 설정 파일 (주파수 대역, 색상 등)
├── analyzer.py                # 핵심 분석 엔진 (FFT, HRV)
├── graph_generator_v2.py      # 시각화 생성
├── report_generator_v2.py     # HTML 리포트 생성
├── statistics_exporter.py     # Excel 통계 출력
├── utils.py                   # 유틸리티 함수
│
├── raw_data/                  # 원본 Excel 데이터
├── analysis_data/             # 분석 결과 CSV/JSON
├── graphs/                    # 생성된 그래프
└── reports/                   # HTML 리포트 및 Excel 통계
```

---

## 주요 기능 구현 내역

### 1. 주파수 대역 분석 (analyzer.py)

**구현된 주파수 대역**:
- **Delta** (0.5-4Hz): 깊은 수면, 무의식 상태
- **Theta** (4-8Hz): 명상, 창의성
- **Alpha** (8-13Hz): 이완, 휴식
- **Low Beta** (13-18Hz): 집중, 각성
- **High Beta** (18-30Hz): 긴장, 스트레스
- **Gamma** (30-50Hz): 고차원 인지

**분석 방법**:
```python
# 2초 윈도우, 50% 오버랩 방식
window_size = int(2.0 * sampling_rate)  # 500 샘플
step_size = window_size // 2  # 250 샘플 (50% 오버랩)

# FFT 기반 파워 스펙트럼 분석
freqs, psd = welch(data, fs=sampling_rate, nperseg=window_size)
```

**개별 채널 추적**:
- Fp1 파워: 좌뇌 활성도
- Fp2 파워: 우뇌 활성도
- 전체 파워: (Fp1 + Fp2) / 2

### 2. 심박변이도(HRV) 분석

**데이터 품질 검증 (5단계)**:
1. **피크 개수 검증**: 최소 30개 이상
2. **유효 데이터 비율**: 50% 이상
3. **생리학적 심박수**: 40-180 bpm 범위
4. **변이도 계수**: CV < 50%
5. **주파수 영역 타당성**: VLF/LF/HF 분포 확인

**시간 영역 지표**:
```python
time_domain = {
    'mean_hr': 평균 심박수 (bpm),
    'sdnn': NN 간격 표준편차 (ms),
    'rmssd': 연속 NN 간격 차이의 제곱근 평균 (ms),
    'pnn50': 50ms 이상 차이 비율 (%)
}
```

**주파수 영역 지표**:
```python
frequency_domain = {
    'vlf': 초저주파 (0.003-0.04Hz),
    'lf': 저주파 (0.04-0.15Hz) - 교감신경,
    'hf': 고주파 (0.15-0.4Hz) - 부교감신경,
    'lf_hf_ratio': 자율신경 균형 지표,
    'lf_norm': LF 정규화 값 (%),
    'hf_norm': HF 정규화 값 (%)
}
```

**해석 로직**:
```python
# 스트레스 수준
if lf_hf_ratio > 2.5: stress = '높음'
elif lf_hf_ratio > 1.5: stress = '보통'
else: stress = '낮음'

# 자율신경 균형
if 1.0 <= lf_hf_ratio <= 2.0: balance = '균형'
elif lf_hf_ratio > 2.0: balance = '교감신경 우세'
else: balance = '부교감신경 우세'
```

### 3. 좌뇌/우뇌 균형도 분석

**비대칭 지수 계산**:
```python
# 단순 차이
diff = fp2_mean - fp1_mean

# 비율
ratio = fp2_mean / fp1_mean

# 정규화 비대칭 지수 (-100 ~ +100)
total = fp1_mean + fp2_mean
asymmetry_index = ((fp2_mean - fp1_mean) / total) * 100

# 해석
if asymmetry_index > 5: dominant = '우뇌 우세'
elif asymmetry_index < -5: dominant = '좌뇌 우세'
else: dominant = '균형'
```

---

## 시각화 구현

### 1. 주파수 대역 그래프 (6개)
- Delta, Theta, Alpha, Low Beta, High Beta, Gamma
- 시간에 따른 파워 변화 라인 그래프
- 좌뇌/우뇌 개별 표시

### 2. 주파수 대역 비율 막대그래프
- 전체 파워 대비 각 대역의 비율(%)
- 절대 파워 값(μV²) 표시
- 최대 비율 대역 금색 테두리 강조

### 3. HRV 종합 시각화 (4패널)

**좌상단: 시간 영역 지표 (ubio 스타일)**
```python
# 평균 맥박: 40~140 범위, 정상 60~100 (녹색)
# SDNN: 0~150 범위, 정상 30~120 (녹색)
# RMSSD: 0~150 범위, 정상 20~100 (녹색)
# 빨간 화살표로 현재 값 표시
```

**우상단: 주파수 영역 지표**
```python
# LF (교감활성): 0~10 범위, 정상 4~6
# HF (부교감활성): 0~10 범위, 정상 4~6
# LF/HF Ratio: 0~5 범위, 정상 1~2
```

**좌하단: 스트레스 수준 게이지**
```python
# 0-100 스케일 계산
stress_score = 0

# LF/HF 기여도
if lf_hf_ratio > 2.5: stress_score += 40
elif lf_hf_ratio > 1.5: stress_score += 25
elif lf_hf_ratio > 1.0: stress_score += 10

# SDNN 기여도
if sdnn < 30: stress_score += 40
elif sdnn < 50: stress_score += 25
elif sdnn < 70: stress_score += 10

# 녹색(0-33) / 주황(33-66) / 빨강(66-100)
```

**우하단: 자율신경 균형 좌우 막대**
```python
# 왼쪽: 교감신경 (LF_norm, 빨강)
# 오른쪽: 부교감신경 (HF_norm, 파랑)
# 중앙선 기준 좌우 대칭 표시
```

### 4. 좌뇌/우뇌 균형도 그래프

**상단 6개 서브플롯**: 주파수 대역별 타임시리즈
```python
# 중앙선(0) 기준
# 위쪽(양수): 우뇌 우세 (파랑)
# 아래쪽(음수): 좌뇌 우세 (빨강)
diff = fp2_data - fp1_data
```

**하단 게이지**: 전체 평균 균형도
```python
# 반원 게이지 (Wedge 패치 사용)
# 좌뇌 영역 (빨강): 180~135도
# 균형 영역 (녹색): 135~45도
# 우뇌 영역 (파랑): 45~0도

# 바늘 각도 계산
needle_angle = np.radians(90 - balance_index * 0.9)
# balance_index: -100(좌뇌) ~ 0(균형) ~ +100(우뇌)
```

---

## Excel 통계 출력 (statistics_exporter.py)

### 생성되는 7개 시트

**1. 기본정보**
- 이름, 성별, 나이
- 측정 시간(초/분)
- 샘플링 레이트

**2. 절대파워_통계**
```python
columns = [
    '주파수대역',
    '주파수범위(Hz)',
    '평균(μV²)',
    '표준편차',
    '최소값',
    '최대값',
    '좌뇌평균(Fp1)',
    '우뇌평균(Fp2)'
]
# 6개 주파수 대역별 통계
```

**3. 절대파워_시계열**
- 시간(초) 컬럼
- 각 대역별: 전체, Fp1, Fp2 (18개 컬럼)
- 최대 500개 포인트로 샘플링

**4. 상대파워**
```python
# 전체 파워 대비 비율(%)
rel_power = (mean_power / total_power) * 100

columns = [
    '주파수대역',
    '상대파워(%)',
    '좌뇌상대파워(%)',
    '우뇌상대파워(%)'
]
```

**5. 좌우비대칭**
```python
columns = [
    '주파수대역',
    '좌뇌평균(Fp1)',
    '우뇌평균(Fp2)',
    '차이(Fp2-Fp1)',
    '비율(Fp2/Fp1)',
    '비대칭지수',  # -100 ~ +100
    '우세반구'      # 좌뇌/우뇌/균형
]
```

**6. HRV상세**
```python
metrics = [
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
]
```

**7. 시계열원데이터**
- 전체 시계열 데이터 (최대 100,000행)
- Excel 행 제한 고려하여 샘플링

---

## 품질 관리 시스템

### HRV 데이터 품질 검증

```python
# 1. 피크 개수 검증
if len(nn_intervals) < 30:
    return 'insufficient_data'

# 2. 유효 데이터 비율
valid_ratio = len(filtered) / len(total)
if valid_ratio < 0.5:
    return 'low_quality_ratio'

# 3. 생리학적 타당성
if mean_hr < 40 or mean_hr > 180:
    return 'abnormal_heart_rate'

# 4. 변이도 타당성
cv_nn = (std / mean) * 100
if cv_nn > 50:
    return 'excessive_variability'

# 5. 통과
return 'good'
```

### 품질 경고 표시

```python
# HTML 리포트에 경고 박스 표시
if quality != 'good':
    warning = f"""
        <div style="background: #fff3cd; border-left: 4px solid #ffc107;">
            <strong>⚠️ 데이터 품질 경고:</strong> {quality_message}<br>
            HRV 측정값이 표시되지 않습니다.
        </div>
    """
```

---

## 기술적 구현 세부사항

### 1. 한글 폰트 처리

```python
def setup_korean_font():
    system = platform.system()
    if system == 'Windows':
        plt.rcParams['font.family'] = 'Malgun Gothic'
    elif system == 'Darwin':
        plt.rcParams['font.family'] = 'AppleGothic'
    else:
        plt.rcParams['font.family'] = 'NanumGothic'

    # 마이너스 기호 깨짐 방지
    plt.rcParams['axes.unicode_minus'] = False

    # 이모지 경고 억제
    warnings.filterwarnings('ignore', message='Glyph.*missing from font')
```

### 2. 뇌 균형 게이지 렌더링

```python
from matplotlib.patches import Wedge

# Wedge 패치로 각 영역 그리기
wedge_left = Wedge((0, 0), 1.0, 135, 180, width=0.1,
                   facecolor='#ff5722', edgecolor='none', alpha=0.5)
wedge_center = Wedge((0, 0), 1.0, 45, 135, width=0.1,
                     facecolor='#4caf50', edgecolor='none', alpha=0.5)
wedge_right = Wedge((0, 0), 1.0, 0, 45, width=0.1,
                    facecolor='#2196f3', edgecolor='none', alpha=0.5)

# 바늘 각도 계산 (balance_index: -100~100)
needle_angle = np.radians(90 - balance_index * 0.9)
needle_x = needle_length * np.cos(needle_angle)
needle_y = needle_length * np.sin(needle_angle)
```

### 3. 배치 처리 시스템

```python
# main.py --folder 옵션
if args.folder:
    excel_files = glob.glob(os.path.join(args.folder, "*.xlsx"))

    for idx, file_path in enumerate(excel_files):
        print(f"[{idx+1}/{total}] 처리 중...")

        # 1. 데이터 로드
        # 2. 분석 수행
        # 3. 그래프 생성
        # 4. 리포트 생성
        # 5. Excel 통계 생성
```

---

## 처리 완료 데이터

### 2025년 11월 2일 배치 처리 결과

**처리된 파일 (6건)**:
1. **김선근_남_44** - 275.2초 (4.6분)
2. **방지수_남_37** - 311.2초 (5.2분)
3. **변미정_남_48** - 309.4초 (5.2분)
4. **이동미_여_44** - 313.7초 (5.2분)
5. **이찬희_남_28** - 318.1초 (5.3분)
6. **한진우_남_38** - 312.2초 (5.2분)

**각 피험자당 생성된 파일**:
- 그래프 11개 (PNG)
- HTML 리포트 1개
- Excel 통계 파일 1개 (7개 시트)
- 분석 CSV 1개
- 메타데이터 JSON 1개

**총 생성 파일**: 90개 (6명 × 15개)

---

## 사용 방법

### 단일 파일 처리

```bash
python main.py --file "raw_data/이동미_여_44.xlsx"
```

### 폴더 배치 처리

```bash
python main.py --folder "raw_data"
```

### 출력 결과 확인

```bash
# HTML 리포트
reports/이동미_여_44_report.html

# Excel 통계
reports/이동미_여_44_statistics.xlsx

# 그래프
graphs/이동미_여_44_*.png
```

---

## 설정 파일 (config.py)

### 주파수 대역 정의

```python
FREQUENCY_BANDS = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'low_beta': (13, 18),
    'high_beta': (18, 30),
    'gamma': (30, 50)
}
```

### 색상 팔레트

```python
COLORS = {
    'delta': '#1f77b4',    # 파랑
    'theta': '#ff7f0e',    # 주황
    'alpha': '#2ca02c',    # 녹색
    'low_beta': '#d62728',  # 빨강
    'high_beta': '#9467bd', # 보라
    'gamma': '#8c564b'      # 갈색
}
```

### 그래프 설정

```python
GRAPH_DPI = 150
SMOOTH_WINDOW = 5  # 스무딩 윈도우 크기
```

---

## 의존성 패키지

```python
# requirements.txt
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
scipy>=1.10.0
openpyxl>=3.1.0
```

---

## 향후 개선 사항

### 1. 추가 분석 기능
- [ ] 뇌파 동기화 분석 (Coherence)
- [ ] 전극 간 상관관계 분석
- [ ] 시간-주파수 분석 (Wavelet)

### 2. 시각화 개선
- [ ] 대화형 그래프 (Plotly)
- [ ] 3D 토포그래피 맵
- [ ] 애니메이션 시계열

### 3. 데이터 관리
- [ ] 데이터베이스 통합
- [ ] 피험자 비교 분석
- [ ] 종단 연구 지원

### 4. 성능 최적화
- [ ] 멀티프로세싱 지원
- [ ] 메모리 효율성 개선
- [ ] 실시간 스트리밍 분석

---

## 문제 해결 이력

### 해결된 이슈

**1. 뇌 균형 게이지 렌더링 오류**
- **문제**: fill() 함수 사용 시 각도 계산 오류
- **해결**: matplotlib.patches.Wedge 사용으로 정확한 각도 렌더링
- **날짜**: 2025-11-02

**2. HRV 데이터 신뢰성 문제**
- **문제**: EEG에서 추출한 PPG 신호 품질 불안정
- **해결**: 5단계 품질 검증 시스템 구축
- **날짜**: 2025-11-02

**3. Excel 용량 제한**
- **문제**: 시계열 데이터가 Excel 행 제한(1,048,576) 초과
- **해결**: 스마트 샘플링 (최대 100,000행)
- **날짜**: 2025-11-02

---

## 참고 자료

### 학술 기반

**EEG 주파수 대역**:
- Delta: 깊은 수면, 무의식 상태
- Theta: 명상, 창의성, 기억 통합
- Alpha: 이완 상태, 눈 감고 휴식
- Beta: 각성, 집중, 인지 활동
- Gamma: 고차원 인지, 의식 통합

**HRV 해석 기준**:
- SDNN: 전체 자율신경 활성도
- RMSSD: 부교감신경 활성도
- LF/HF Ratio: 자율신경 균형
  - 정상: 1.0~2.0
  - 교감신경 우세: > 2.0
  - 부교감신경 우세: < 1.0

### 참조 파일
- `참고 개발코드/01.Results_0128.xlsx` - Excel 통계 포맷 참고
- `참고 개발코드/ubio 샘플.pdf` - HRV 시각화 스타일 참고
- `참고 개발코드/화면 캡처 2025-11-01 234552.png` - 좌뇌/우뇌 그래프 샘플

---

## 연락처 및 유지보수

**프로젝트 폴더**: `/mnt/c/Users/bach1/OneDrive/문서/05.claude/01.EEG실시간 분석 데이터`

**핵심 파일**:
- `main.py` - 실행 진입점
- `analyzer.py` - 분석 로직
- `graph_generator_v2.py` - 시각화
- `statistics_exporter.py` - Excel 출력

**로그 파일**: `DEVELOPMENT_LOG_YYYY-MM-DD.md`

---

## 버전 히스토리

### v2.0 (2025-11-02)
- HRV 품질 검증 시스템 추가
- 좌뇌/우뇌 균형도 그래프 추가
- Excel 상세 통계 출력 기능 추가
- ubio 스타일 HRV 시각화 개선
- 뇌 균형 게이지 렌더링 수정

### v1.0 (이전 버전)
- 기본 EEG 주파수 분석
- 기본 그래프 생성
- HTML 리포트 생성

---

**마지막 업데이트**: 2025년 11월 2일
**작성자**: Claude Code (AI Assistant)
**상태**: 프로덕션 완료, 6건 배치 처리 성공
