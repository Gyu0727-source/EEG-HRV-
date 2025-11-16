# 🧠 EEG 실시간 분석 프로젝트 - 클로드 코드 명령서

## 📋 프로젝트 개요

**목적**: 원시 EEG 데이터를 분석하여 개인별 뇌파 분석 보고서를 자동 생성하는 시스템 구축

**핵심 요구사항**:
1. 원시 데이터 자동 저장 및 관리
2. 2초 윈도우 기반 시계열 분석
3. 부드러운 추세선 생성 (Savitzky-Golay 필터)
4. 의미있는 변화점 자동 감지
5. 연구용 분석 데이터 테이블 생성
6. 개인별 HTML 보고서 자동 생성

---

## 📁 디렉토리 구조

```
C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\
│
├── 참고 개발코드\              # 기존 역공학 알고리즘 (참고용)
│   └── [기존 분석 코드들]
│
├── raw_data\                  # 원시 데이터 저장 (자동 생성)
│   ├── 노인규_남_35.csv
│   ├── 김영희_여_28.csv
│   └── ...
│
├── analysis_data\             # 분석 데이터 저장 (자동 생성)
│   ├── 노인규_남_35_analysis.csv
│   ├── 김영희_여_28_analysis.csv
│   └── ...
│
├── reports\                   # 개인별 보고서 (자동 생성)
│   ├── 노인규_남_35_report.html
│   ├── 노인규_남_35_report.pdf
│   ├── 김영희_여_28_report.html
│   └── ...
│
├── graphs\                    # 그래프 이미지 (자동 생성)
│   ├── 노인규_남_35_delta.png
│   ├── 노인규_남_35_theta.png
│   └── ...
│
└── templates\                 # HTML 템플릿 (수동 배치)
    └── report_template.html
```

---

## 🎯 주요 작업 단계

### **Phase 1: 프로젝트 초기화**

1. 필요한 폴더 구조 자동 생성
   ```python
   folders = ['raw_data', 'analysis_data', 'reports', 'graphs', 'templates']
   ```

2. 필요한 패키지 확인 및 설치
   ```python
   requirements = [
       'numpy',
       'pandas',
       'scipy',
       'matplotlib',
       'weasyprint',  # PDF 생성용
       'ruptures'     # 변화점 감지용
   ]
   ```

### **Phase 2: 원시 데이터 처리**

**입력**: 사용자가 지정한 원시 EEG 데이터 파일 경로

**처리**:
1. 파일명에서 정보 파싱
   - 형식: `이름_성별_나이.csv` 또는 `.txt`
   - 예: `노인규_남_35.csv` → 이름=노인규, 성별=남, 나이=35

2. 원시 데이터를 `raw_data/` 폴더로 복사
   - 원본 파일명 유지

3. 데이터 검증
   - Fp1, Fp2 채널 존재 확인
   - Sampling rate 확인
   - 최소 측정 시간 확인 (1분 이상)

### **Phase 3: 뇌파 분석 (핵심)**

**참고**: `참고 개발코드\` 폴더의 기존 알고리즘을 기반으로 수정

**분석 파이프라인**:

```python
1. 전처리
   - 60Hz notch filter
   - 0.5-50Hz bandpass filter
   - Artifact 제거

2. 시계열 분석 (2초 윈도우)
   - 윈도우 크기: 2초
   - 오버랩: 50% (1초)
   - 결과: 1초마다 새로운 파워 값
   
   예시: 15분 측정 = 900초 = 900개 데이터 포인트

3. 주파수 대역별 파워 계산
   - Delta (0.5-4Hz)
   - Theta (4-8Hz)
   - Alpha (8-13Hz)
   - Beta (13-30Hz)
   - Gamma (30-50Hz)
   
   각 대역마다 900개 시계열 값 생성

4. 데이터 스무딩
   - Savitzky-Golay 필터 적용
   - window_length = 51
   - polyorder = 3
   
   목적: 자글자글한 원본 → 부드러운 추세선

5. 변화점 감지
   - 2차 미분으로 곡률 계산
   - 통계적으로 유의미한 2-3개 변화점만 선택
   - 각 변화점의 방향 판단 (증가/감소/안정)
```

### **Phase 4: 분석 데이터 생성**

**출력 파일**: `analysis_data/{이름}_{성별}_{나이}_analysis.csv`

**테이블 구조**:

```csv
time_sec,delta_raw,delta_smooth,theta_raw,theta_smooth,alpha_raw,alpha_smooth,beta_raw,beta_smooth,gamma_raw,gamma_smooth
0,38.2,38.5,22.1,21.8,15.3,15.1,20.5,20.4,28.1,27.9
1,37.8,38.3,23.4,22.1,15.8,15.4,20.1,20.5,27.5,27.8
2,39.1,38.1,21.9,22.4,16.2,15.7,19.8,20.6,28.3,27.7
...
```

**컬럼 설명**:
- `time_sec`: 측정 시간 (초)
- `{band}_raw`: 원본 파워 값 (노이즈 포함)
- `{band}_smooth`: 스무딩된 파워 값 (그래프용)

**추가 메타데이터 파일**: `analysis_data/{이름}_{성별}_{나이}_metadata.json`

```json
{
  "name": "노인규",
  "gender": "남",
  "age": 35,
  "measurement_date": "2025-11-01",
  "duration_seconds": 900,
  "sampling_rate": 250,
  "window_size": 2,
  "overlap": 0.5,
  "change_points": {
    "delta": [140, 310, 540],
    "theta": [180, 420],
    "alpha": [120, 450, 720],
    "beta": [380, 650],
    "gamma": [90, 510, 780]
  },
  "change_types": {
    "delta": ["decrease", "stable", "decrease"],
    "theta": ["increase", "decrease"],
    ...
  }
}
```

### **Phase 5: 그래프 생성**

**각 주파수 대역별로 개별 PNG 생성**:

파일명 패턴: `graphs/{이름}_{성별}_{나이}_{band}.png`

예시:
- `graphs/노인규_남_35_delta.png`
- `graphs/노인규_남_35_theta.png`
- `graphs/노인규_남_35_alpha.png`
- `graphs/노인규_남_35_beta.png`
- `graphs/노인규_남_35_gamma.png`

**그래프 스펙**:
- 크기: 1400 x 500 픽셀
- DPI: 300
- 배경: 흰색
- 부드러운 추세선 (스무딩된 데이터)
- 의미있는 변화점 2-3개 표시 (화살표 + 타임스탬프)
- 평균선 표시 (점선)
- 가변 시간축 (자동 조정)

### **Phase 6: 해석 텍스트 자동 생성**

**각 주파수 대역별 자동 해석**:

```python
def generate_interpretation(band_name, smoothed_data, change_points, change_types):
    """
    변화 패턴을 분석하여 자동 해석 생성
    
    Returns:
    --------
    interpretation_html : str
        HTML 형식의 해석 텍스트
    """
    
    # 구간 나누기
    phases = classify_phases(smoothed_data, change_points)
    # 예: ['초반: 증가', '중반: 안정', '후반: 감소']
    
    # 템플릿 기반 해석 생성
    interpretation = template_by_pattern[band_name][pattern]
    
    return interpretation
```

**해석 템플릿 예시** (각 패턴별로 미리 정의):

```python
INTERPRETATIONS = {
    'alpha': {
        'increase_increase_stable': """
            초반부터 점진적으로 증가하여 후반부에 안정적인 이완 상태를 보였습니다.
            뇌가 긴장을 풀고 안정을 찾았다는 신호입니다.
            <span class="tech-note">(Cortical inhibition activation)</span>
        """,
        'stable_increase_increase': """
            중반부터 점점 편안하고 이완된 상태가 되었습니다.
            측정에 적응하면서 자연스럽게 긴장이 풀렸습니다.
        """,
        # ... 더 많은 패턴
    },
    'delta': {
        'decrease_decrease_stable': """
            처음에는 깊은 이완 상태였다가 점점 각성도가 높아졌습니다.
            측정 환경에 적응하는 자연스러운 반응입니다.
        """,
        # ...
    },
    # ... 나머지 주파수 대역
}
```

### **Phase 7: HTML 보고서 생성**

**입력**:
- 개인 정보 (이름, 성별, 나이, 측정시간)
- 5개 그래프 이미지 (PNG)
- 5개 해석 텍스트 (HTML)
- 메타데이터 (JSON)

**처리**:
1. `templates/report_template.html` 읽기
2. 그래프 이미지를 base64로 인코딩하여 HTML에 삽입
3. 변수 치환
   - `{{NAME}}` → 실제 이름
   - `{{GRAPH_DELTA}}` → base64 이미지 데이터
   - `{{ANALYSIS_DELTA}}` → 해석 텍스트
   - 등등
4. 완성된 HTML 저장

**출력**: `reports/{이름}_{성별}_{나이}_report.html`

### **Phase 8: PDF 변환**

```python
from weasyprint import HTML

HTML(f'reports/{filename}_report.html').write_pdf(
    f'reports/{filename}_report.pdf'
)
```

**출력**: `reports/{이름}_{성별}_{나이}_report.pdf`

---

## 🔧 핵심 함수 구조

### **main.py** (메인 실행 파일)

```python
def main():
    """메인 실행 함수"""
    
    # 1. 프로젝트 초기화
    initialize_project()
    
    # 2. 원시 데이터 입력 받기
    raw_file_path = input("원시 데이터 파일 경로를 입력하세요: ")
    # 또는 폴더 전체 스캔
    
    # 3. 배치 처리
    process_batch(raw_file_path)
    
    print("✅ 완료!")

def process_batch(raw_files):
    """배치 처리"""
    for raw_file in raw_files:
        try:
            # 파일명 파싱
            info = parse_filename(raw_file)
            
            # 원시 데이터 복사
            copy_to_raw_data(raw_file, info)
            
            # 분석
            analysis_result = analyze_eeg(raw_file, info)
            
            # 분석 데이터 저장
            save_analysis_data(analysis_result, info)
            
            # 그래프 생성
            graphs = generate_graphs(analysis_result, info)
            
            # 해석 생성
            interpretations = generate_interpretations(analysis_result, info)
            
            # 보고서 생성
            generate_report(info, graphs, interpretations)
            
            # PDF 변환
            convert_to_pdf(info)
            
            print(f"✓ {info['name']} 처리 완료")
            
        except Exception as e:
            print(f"✗ {raw_file} 처리 실패: {e}")
            continue
```

### **analyzer.py** (분석 모듈)

```python
def analyze_eeg(raw_file, info):
    """
    EEG 원시 데이터 분석
    
    참고: 참고 개발코드\ 폴더의 알고리즘 기반
    
    Returns:
    --------
    result : dict
        {
            'time': array,
            'delta_raw': array,
            'delta_smooth': array,
            'theta_raw': array,
            ...
            'change_points': dict,
            'change_types': dict
        }
    """
    
    # 1. 데이터 로드
    data = load_raw_data(raw_file)
    
    # 2. 전처리
    fp1_clean, fp2_clean = preprocess(data)
    
    # 3. 2초 윈도우 분석
    time_array, band_powers = compute_band_powers_timeseries(
        fp1_clean, fp2_clean,
        window_size=2.0,
        overlap=0.5
    )
    
    # 4. 스무딩
    band_powers_smooth = {}
    for band, values in band_powers.items():
        band_powers_smooth[band] = smooth_signal(values)
    
    # 5. 변화점 감지
    change_points = {}
    change_types = {}
    for band, values in band_powers_smooth.items():
        cp, ct = detect_significant_changes(values, n_changes=3)
        change_points[band] = cp
        change_types[band] = ct
    
    return {
        'time': time_array,
        'raw': band_powers,
        'smooth': band_powers_smooth,
        'change_points': change_points,
        'change_types': change_types,
        'info': info
    }
```

### **graph_generator.py** (그래프 생성)

```python
def generate_graphs(analysis_result, info):
    """
    5개 주파수 대역별 그래프 생성
    
    Returns:
    --------
    graph_paths : dict
        {'delta': 'path/to/delta.png', ...}
    """
    
    graphs = {}
    
    for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        graph_path = plot_clean_timeseries(
            time_array=analysis_result['time'],
            raw_data=analysis_result['raw'][band],
            smoothed_data=analysis_result['smooth'][band],
            change_points=analysis_result['change_points'][band],
            change_types=analysis_result['change_types'][band],
            band_info=BAND_CONFIGS[band],
            save_path=f"graphs/{info['name']}_{info['gender']}_{info['age']}_{band}.png"
        )
        graphs[band] = graph_path
    
    return graphs
```

### **report_generator.py** (보고서 생성)

```python
def generate_report(info, graphs, interpretations):
    """
    HTML 보고서 생성
    
    Parameters:
    -----------
    info : dict
        개인 정보
    graphs : dict
        그래프 파일 경로들
    interpretations : dict
        각 대역별 해석 텍스트
    """
    
    # 템플릿 로드
    with open('templates/report_template.html', 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 그래프를 base64로 변환
    graph_data = {}
    for band, path in graphs.items():
        with open(path, 'rb') as f:
            graph_data[band] = base64.b64encode(f.read()).decode()
    
    # 변수 치환
    html = template.replace('{{NAME}}', info['name'])
    html = html.replace('{{GENDER}}', info['gender'])
    html = html.replace('{{AGE}}', str(info['age']))
    html = html.replace('{{DURATION}}', str(info['duration']))
    
    for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        html = html.replace(
            f'{{{{GRAPH_{band.upper()}}}}}',
            f'data:image/png;base64,{graph_data[band]}'
        )
        html = html.replace(
            f'{{{{ANALYSIS_{band.upper()}}}}}',
            interpretations[band]
        )
    
    # 저장
    output_path = f"reports/{info['name']}_{info['gender']}_{info['age']}_report.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path
```

---

## 📝 필요한 파일들

### **1. 코드 파일**
- `main.py` - 메인 실행
- `analyzer.py` - 뇌파 분석
- `graph_generator.py` - 그래프 생성
- `report_generator.py` - 보고서 생성
- `utils.py` - 유틸리티 함수
- `config.py` - 설정값

### **2. 템플릿 파일**
- `templates/report_template.html` - HTML 보고서 템플릿

### **3. 설정 파일**
- `requirements.txt` - 패키지 목록
- `config.json` - 프로젝트 설정

---

## 🚀 실행 방법

### **방법 1: 단일 파일 처리**

```bash
python main.py --file "C:\path\to\노인규_남_35.csv"
```

### **방법 2: 폴더 전체 배치 처리**

```bash
python main.py --folder "C:\path\to\raw_files\"
```

### **방법 3: 대화형 모드**

```bash
python main.py
> 원시 데이터 경로: [입력]
> 처리 중...
> ✓ 노인규_남_35 완료
> ✓ 김영희_여_28 완료
> ✅ 전체 2명 처리 완료!
```

---

## ⚙️ 설정 가능 항목 (config.py)

```python
# 분석 파라미터
WINDOW_SIZE = 2.0  # 초
OVERLAP = 0.5  # 50%
SMOOTHING_WINDOW = 51
SMOOTHING_POLY = 3

# 변화점 감지
N_CHANGE_POINTS = 3  # 최대 변화점 개수
MIN_DISTANCE_RATIO = 0.2  # 변화점 간 최소 거리 (전체 길이의 20%)

# 그래프 설정
GRAPH_WIDTH = 14  # 인치
GRAPH_HEIGHT = 5  # 인치
GRAPH_DPI = 300

# 주파수 대역
BANDS = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta': (13, 30),
    'gamma': (30, 50)
}

# 색상
COLORS = {
    'delta': '#000080',
    'theta': '#8B008B',
    'alpha': '#228B22',
    'beta': '#FFA500',
    'gamma': '#FF4500'
}
```

---

## ✅ 체크리스트

### **Phase 1: 초기 설정**
- [ ] 폴더 구조 생성
- [ ] 패키지 설치
- [ ] 참고 개발코드 확인

### **Phase 2: 코어 기능 구현**
- [ ] 원시 데이터 로딩 함수
- [ ] 파일명 파싱 함수
- [ ] 전처리 파이프라인
- [ ] 2초 윈도우 분석 알고리즘
- [ ] 스무딩 함수
- [ ] 변화점 감지 함수

### **Phase 3: 데이터 저장**
- [ ] 분석 데이터 CSV 저장
- [ ] 메타데이터 JSON 저장

### **Phase 4: 시각화**
- [ ] 그래프 생성 함수
- [ ] 변화점 마커 표시
- [ ] 시간축 자동 조정

### **Phase 5: 보고서**
- [ ] HTML 템플릿 작성
- [ ] 해석 자동 생성 로직
- [ ] 보고서 생성 함수
- [ ] PDF 변환 기능

### **Phase 6: 테스트**
- [ ] 단일 파일 테스트
- [ ] 다양한 측정 시간 테스트 (5분, 15분, 40분)
- [ ] 에러 처리 테스트
- [ ] 배치 처리 테스트

---

## 🎯 최종 목표

**입력**: 원시 EEG 데이터 파일 (예: `노인규_남_35.csv`)

**출력**:
1. ✅ `raw_data/노인규_남_35.csv` - 원본 백업
2. ✅ `analysis_data/노인규_남_35_analysis.csv` - 연구용 시계열 데이터
3. ✅ `analysis_data/노인규_남_35_metadata.json` - 메타데이터
4. ✅ `graphs/노인규_남_35_delta.png` - 5개 그래프
5. ✅ `graphs/노인규_남_35_theta.png`
6. ✅ `graphs/노인규_남_35_alpha.png`
7. ✅ `graphs/노인규_남_35_beta.png`
8. ✅ `graphs/노인규_남_35_gamma.png`
9. ✅ `reports/노인규_남_35_report.html` - HTML 보고서
10. ✅ `reports/노인규_남_35_report.pdf` - PDF 보고서

**모든 과정 자동화**: 파일 경로 입력 → Enter → 완료!

---

## 💡 중요 참고사항

1. **기존 알고리즘 활용**
   - `참고 개발코드\` 폴더의 코드를 최대한 재사용
   - 검증된 전처리 파이프라인 유지
   - 주파수 대역 계산 방식 동일

2. **새로운 기능 추가**
   - 2초 윈도우 시계열 분석 (기존: 전체 평균)
   - Savitzky-Golay 스무딩 (새로운 기능)
   - 변화점 자동 감지 (새로운 기능)
   - 자동 해석 생성 (새로운 기능)

3. **에러 처리**
   - 잘못된 파일 형식
   - 불충분한 데이터 길이
   - 채널 누락
   - 등등

4. **확장성**
   - 추후 다른 전극 위치 추가 가능 (현재: Fp1, Fp2)
   - 다른 분석 지표 추가 가능
   - 보고서 템플릿 교체 가능

---

## 🔍 디버깅 팁

**로깅 추가**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('eeg_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("분석 시작...")
```

**진행 상황 표시**:
```python
from tqdm import tqdm

for file in tqdm(raw_files, desc="처리 중"):
    process_file(file)
```

---

## 📞 문제 발생 시

1. `eeg_analysis.log` 파일 확인
2. 특정 단계에서 멈춘 경우 해당 함수 단독 실행
3. 테스트 데이터로 각 함수 개별 검증

---

**작성자**: 노인규  
**작성일**: 2025-11-01  
**버전**: 1.0  
**프로젝트**: EEG 실시간 분석 자동화 시스템
