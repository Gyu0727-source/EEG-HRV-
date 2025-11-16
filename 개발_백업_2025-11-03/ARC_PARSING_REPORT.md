# ARC 파일 직접 파싱 결과 보고서
**날짜**: 2025년 11월 2일

## 요약

BrainBay ARC 파일을 Python으로 직접 읽는 시도를 진행했습니다.

### 성공한 부분
✅ ARC 파일 구조 파악 완료
✅ 헤더 정보 읽기 성공
✅ 바이너리 데이터 파싱 성공
✅ OpenBCI 스케일 팩터 발견 (0.0223)
✅ Excel로 변환 기능 구현

### 문제점
❌ 파싱한 데이터와 기존 Excel 데이터의 불일치
- ARC 파싱: 94,541행, 값 범위 -14694~14349 (스케일 적용 후)
- 기존 Excel: 79,536행, 값 범위 -348~620

## 상세 분석

### 1. ARC 파일 구조

```
파일 구조:
├── 헤더 (256바이트)
│   ├── "BrainBay Archive File"
│   ├── "Integer Values"
│   └── "OpenBCI 8 Channels"
│
└── 데이터 부분 (32바이트 블록 반복)
    ├── 8채널 × 2바이트 (int16, big-endian)
    └── 메타데이터 16바이트
```

### 2. 발견한 변환 공식

Filetrans_band.con 파일 분석 결과:
```
expression=A/0.0223/100
```

즉:
```python
uV_value = raw_value / 0.0223 / 100 = raw_value / 2.23
```

### 3. 데이터 불일치 원인 분석

#### 가능성 1: BrainBay 추가 처리
원본 Excel 파일은 BrainBay에서 TXT로 변환한 후, 다음 처리가 추가되었을 가능성:
- 필터링 (노이즈 제거)
- 다운샘플링 (94,541 → 79,536행, 약 84% 유지)
- 아티팩트 제거
- 베이스라인 보정

#### 가능성 2: 잘못된 바이트 해석
현재 파싱 방법:
```python
# 32바이트 블록에서 처음 16바이트만 8채널 데이터로 해석
for i in range(8):
    value = struct.unpack('>h', data[i*2:(i+1)*2])[0]
```

실제로는 다른 구조일 수 있음:
- 24-bit 데이터일 가능성
- 다른 바이트 순서
- 압축 또는 인코딩

### 4. 비교 데이터

#### ARC 파싱 결과 (이찬희 숫자.arc)
```
행 개수: 94,541
채널 0 (Fp1 추정):
  평균: -215.45
  표준편차: 4442.90
  최소값: -14694.17
  최대값: 14349.33
```

#### 기존 Excel (이찬희_남_28.xlsx)
```
행 개수: 79,536
첫 번째 컬럼 (Fp1):
  평균: 15.76
  표준편차: 38.62
  최소값: -348.00
  최대값: 262.00
```

차이점:
- 행 개수: 약 15,000행 차이 (16% 차이)
- 값 범위: 약 50배 차이 (스케일 문제)
- 평균: 부호와 크기 모두 다름

## 결론 및 권장사항

### 현재 상태
ARC 파일을 직접 파싱하는 것은 **기술적으로 가능**하지만, 정확한 데이터 변환을 위해서는 다음이 필요합니다:

### 필요한 추가 정보

1. **BrainBay 실제 TXT 변환 파일**
   - ARC → TXT 변환 시 BrainBay가 생성한 원본 TXT 파일
   - 이를 통해 정확한 변환 로직 역공학 가능

2. **Filetrans.con 전체 파이프라인**
   - 현재 발견한 것: `A/0.0223/100`
   - 누락 가능성: 필터, 리샘플링, 정규화 등

3. **채널 매핑 정보**
   - OpenBCI 8채널 중 어느 것이 Fp1, Fp2인지
   - 현재 추정: Channel 0 = Fp1, Channel 1 = Fp2

### 권장 작업 순서

#### 옵션 1: 수동 변환 유지 (안전)
**권장**: BrainBay를 사용한 수동 변환 프로세스 유지
- 장점: 검증된 정확한 데이터
- 단점: 시간 소요

#### 옵션 2: 하이브리드 접근
1. ARC → TXT 변환은 BrainBay 사용 (자동화 가능)
2. TXT → Excel은 Python 스크립트
3. Excel → 분석은 기존 시스템

#### 옵션 3: 완전 자동화 (추가 개발 필요)
1. BrainBay 원본 TXT 파일 수집
2. ARC 파싱 로직 정확히 매칭
3. 검증 후 완전 자동화

### 구현된 기능

현재 `arc_reader.py`로 가능한 작업:

```python
from arc_reader import ARCReader

# ARC 파일 읽기
reader = ARCReader('파일.arc')
data = reader.read()

# Excel로 저장
reader.to_excel('파일.xlsx')

# 특정 채널 데이터 추출
fp1_data = reader.get_channel_data('EEG Channel 0')
```

### 차이점 해결을 위한 실험

다음 실험을 통해 정확한 파싱 방법을 찾을 수 있습니다:

1. **BrainBay TXT 파일 생성**
   ```
   - ARC 파일: 07.이찬희 숫자.arc
   - BrainBay로 TXT 변환
   - TXT와 현재 파싱 결과 비교
   ```

2. **스케일 팩터 조정**
   ```python
   # 현재: scale_factor = 2.23
   # 시도: scale_factor = 2.23 * 50  # 약 50배 차이 조정
   ```

3. **다운샘플링 적용**
   ```python
   # 94541 → 79536로 리샘플링
   # 약 84% 유지 = 6개당 1개 제거?
   ```

## 다음 단계

사용자 선택에 따라:

### A안: 검증 우선
1. BrainBay로 TXT 파일 하나 생성
2. ARC 파싱 결과와 비교
3. 차이점 분석 및 코드 수정

### B안: 현상 유지
1. 현재 BrainBay 수동 변환 유지
2. Python 분석 시스템은 Excel 기반 유지

### C안: 부분 자동화
1. ARC → TXT는 BrainBay 배치 처리
2. 나머지는 Python 자동화

## 파일 목록

- `arc_reader.py`: ARC 파일 리더 (기본 기능 구현)
- `ARC_PARSING_REPORT.md`: 본 보고서
- 테스트 파일: `07.이찬희 숫자_converted.xlsx`

## 기술적 세부사항

### ARC 파일 헤더
```
Offset 0x00: "BrainBay Archive File\r\n"
Offset 0x50: "Integer Values\r\n"
Offset 0x78: "OpenBCI 8 Channels\r\n"
Offset 0x100: Data starts
```

### 데이터 블록 (32바이트)
```
00-01: Channel 0 (int16, big-endian)
02-03: Channel 1 (int16, big-endian)
04-05: Channel 2 (int16, big-endian)
06-07: Channel 3 (int16, big-endian)
08-09: Channel 4 (int16, big-endian)
10-11: Channel 5 (int16, big-endian)
12-13: Channel 6 (int16, big-endian)
14-15: Channel 7 (int16, big-endian)
16-31: Metadata (주로 0x00 또는 고정 패턴)
```

### OpenBCI 스케일 정보
```
Resolution: 24-bit ADC (16,777,216)
Range: ±187,500 uV
Scale: 0.0223 uV per count (from Filetrans.con)
Final conversion: value / 2.23
```

---

**작성자**: Claude Code
**프로젝트**: EEG 실시간 분석 시스템
**관련 로그**: DEVELOPMENT_LOG_2025-11-02.md
