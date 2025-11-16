# 🧠 EEG 실시간 분석 시스템

원시 EEG 데이터를 2초 윈도우 기반 시계열 분석하여 개인별 뇌파 분석 보고서를 자동 생성하는 시스템입니다.

## 📋 주요 기능

- **2초 윈도우 시계열 분석**: 전체 평균이 아닌 1초마다 변화하는 뇌파 패턴 추적
- **Savitzky-Golay 스무딩**: 노이즈를 제거한 부드러운 추세선 생성
- **자동 변화점 감지**: 통계적으로 유의미한 2-3개 변화점 자동 탐지
- **5개 주파수 대역 분석**: Delta, Theta, Alpha, Beta, Gamma
- **자동 해석 생성**: 변화 패턴에 따른 자동 텍스트 해석
- **HTML/PDF 보고서**: 전문적인 개인별 보고서 자동 생성

## 📁 프로젝트 구조

```
01.EEG실시간 분석 데이터/
│
├── main.py                    # 메인 실행 파일
├── config.py                  # 설정 파일
├── utils.py                   # 유틸리티 함수
├── analyzer.py                # 뇌파 분석 모듈
├── graph_generator.py         # 그래프 생성 모듈
├── report_generator.py        # 보고서 생성 모듈
├── requirements.txt           # 필요한 패키지 목록
│
├── raw_data/                  # 원시 데이터 백업 (자동 생성)
├── analysis_data/             # 분석 데이터 CSV/JSON (자동 생성)
├── reports/                   # HTML/PDF 보고서 (자동 생성)
├── graphs/                    # 그래프 이미지 (자동 생성)
├── templates/                 # HTML 템플릿
│   └── report_template.html
│
├── 분석 데이터/               # 테스트 데이터 (사용자 제공)
├── 참고 개발코드/             # 기존 역공학 알고리즘
└── CLAUDE_CODE_INSTRUCTIONS.md
```

## 🚀 설치 및 실행

### 1. Python 패키지 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- numpy>=1.24.0
- pandas>=2.0.0
- scipy>=1.10.0
- matplotlib>=3.7.0
- openpyxl>=3.1.0
- weasyprint>=59.0 (PDF 생성, 선택사항)
- ruptures>=1.1.8 (변화점 감지, 선택사항)

### 2. 실행 방법

#### 방법 1: 단일 파일 처리
```bash
python main.py --file "경로/파일명.xlsx"
```

예시:
```bash
python main.py --file "분석 데이터/김선근 44 남.xlsx"
```

#### 방법 2: 폴더 전체 배치 처리
```bash
python main.py --folder "분석 데이터/"
```

#### 방법 3: 대화형 모드
```bash
python main.py
```
그 후 메뉴에서 선택

## 📊 입력 파일 형식

### 파일명 규칙
- 형식: `이름_성별_나이.xlsx` 또는 `이름 나이 성별.xlsx`
- 예시: `김선근_남_44.xlsx`, `김선근 44 남.xlsx`
- 성별: `남`, `여`, `M`, `F`, `male`, `female`

### 데이터 형식
- Excel (.xlsx, .xls) 또는 CSV/TXT 파일
- 최소 2개 컬럼: Fp1, Fp2 전극 데이터
- 샘플링 레이트: 250Hz (설정 변경 가능)
- 최소 측정 시간: 60초 이상 권장

## 📈 출력 결과

각 개인마다 다음 파일들이 자동 생성됩니다:

### 1. 원시 데이터 백업
`raw_data/이름_성별_나이.xlsx`

### 2. 분석 데이터
- `analysis_data/이름_성별_나이_analysis.csv` - 시계열 데이터
- `analysis_data/이름_성별_나이_metadata.json` - 메타데이터

**CSV 구조 예시:**
```csv
time_sec,delta_raw,delta_smooth,theta_raw,theta_smooth,...
0,38.2,38.5,22.1,21.8,...
1,37.8,38.3,23.4,22.1,...
2,39.1,38.1,21.9,22.4,...
```

### 3. 그래프 (5개)
- `graphs/이름_성별_나이_delta.png`
- `graphs/이름_성별_나이_theta.png`
- `graphs/이름_성별_나이_alpha.png`
- `graphs/이름_성별_나이_beta.png`
- `graphs/이름_성별_나이_gamma.png`

### 4. 보고서
- `reports/이름_성별_나이_report.html` - HTML 보고서
- `reports/이름_성별_나이_report.pdf` - PDF 보고서 (선택사항)

## ⚙️ 설정 변경

[config.py](config.py)에서 다음을 변경할 수 있습니다:

```python
# 분석 파라미터
WINDOW_SIZE = 2.0  # 초 (윈도우 크기)
OVERLAP = 0.5  # 오버랩 비율
SMOOTHING_WINDOW = 51  # 스무딩 윈도우
N_CHANGE_POINTS = 3  # 변화점 개수

# 그래프 설정
GRAPH_WIDTH = 14  # 인치
GRAPH_HEIGHT = 5  # 인치
GRAPH_DPI = 300

# 주파수 대역 (Hz)
FREQUENCY_BANDS = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta': (13, 30),
    'gamma': (30, 50)
}
```

## 🔬 핵심 알고리즘

### 1. 전처리
- 60Hz notch filter (전원선 노이즈 제거)
- 0.5-50Hz bandpass filter
- 기존 역공학 알고리즘과 동일한 검증된 방법 사용

### 2. 시계열 분석
- **윈도우 크기**: 2초 (500 샘플 @ 250Hz)
- **오버랩**: 50% (1초씩 이동)
- **결과**: 1초마다 새로운 파워 값 생성
- 예: 15분(900초) 측정 → 약 900개 데이터 포인트

### 3. 스무딩
- Savitzky-Golay 필터 (window=51, poly=3)
- 노이즈 제거하면서 추세 보존

### 4. 변화점 감지
- 2차 미분으로 곡률 계산
- 통계적으로 유의미한 2-3개 변화점만 선택
- 각 변화점의 방향 판단 (증가/감소/안정)

## 📝 사용 예시

### Windows CMD
```cmd
cd "C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터"
python main.py --folder "분석 데이터"
```

### Windows PowerShell
```powershell
cd "C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터"
python main.py --folder "분석 데이터"
```

### 대화형 모드 사용
```bash
python main.py

# 메뉴 선택
# 1. 단일 파일 처리
# 2. 폴더 전체 처리
# 3. 종료
```

## 🐛 문제 해결

### 패키지 설치 오류
```bash
# pip 업그레이드
python -m pip install --upgrade pip

# 개별 설치
pip install numpy pandas scipy matplotlib openpyxl
```

### PDF 생성 실패
- weasyprint 설치가 필요합니다
- 설치 불가 시 HTML 보고서만 생성됩니다

### 파일명 인식 오류
- 파일명이 `이름_성별_나이` 형식인지 확인
- 성별: `남`, `여`, `M`, `F` 중 하나
- 나이: 숫자

### 데이터 품질 경고
- 최소 60초 이상 측정 데이터 권장
- Fp1, Fp2 채널이 모두 있는지 확인

## 📞 참고 문서

- [CLAUDE_CODE_INSTRUCTIONS.md](CLAUDE_CODE_INSTRUCTIONS.md) - 상세 설계 문서
- [참고 개발코드/프로젝트_완료_보고서.md](참고%20개발코드/뇌파알고리즘%20역공학/프로젝트_완료_보고서.md) - 기존 알고리즘 역공학 보고서

## 🎯 완료 체크리스트

- [x] 프로젝트 폴더 구조 생성
- [x] 핵심 분석 알고리즘 구현
- [x] 2초 윈도우 시계열 분석
- [x] Savitzky-Golay 스무딩
- [x] 변화점 자동 감지
- [x] 그래프 생성 (5개 주파수 대역)
- [x] 자동 해석 생성
- [x] HTML 템플릿 및 보고서
- [x] PDF 변환 기능
- [x] 배치 처리 기능
- [x] 대화형 모드
- [ ] 테스트 데이터 검증 (실행 필요)

## 🚀 다음 단계

1. **패키지 설치**: `pip install -r requirements.txt`
2. **테스트 실행**: `python main.py --folder "분석 데이터"`
3. **결과 확인**: `reports/` 폴더의 HTML 보고서 확인
4. **필요시 설정 조정**: `config.py` 파라미터 수정

---

**작성일**: 2025-11-01
**버전**: 1.0
**프로젝트**: EEG 실시간 분석 자동화 시스템
