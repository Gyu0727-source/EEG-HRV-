"""
BrainBay ARC 파일 리더

ARC 파일을 직접 읽어서 pandas DataFrame으로 변환
Excel 변환 과정 없이 바로 분석 가능
"""

import struct
import numpy as np
import pandas as pd
import os


class ARCReader:
    """BrainBay ARC 파일 파서"""

    def __init__(self, file_path):
        """
        Parameters:
        -----------
        file_path : str
            ARC 파일 경로
        """
        self.file_path = file_path
        self.header = {}
        self.data = None
        self.sampling_rate = 250  # OpenBCI 기본 샘플링 레이트

    def read(self):
        """ARC 파일 읽기"""
        with open(self.file_path, 'rb') as f:
            # 헤더 읽기
            self._read_header(f)

            # 데이터 읽기
            self._read_data(f)

        return self.data

    def _read_header(self, f):
        """헤더 정보 읽기"""
        # BrainBay Archive File (첫 줄)
        line1 = f.read(256).decode('ascii', errors='ignore').strip('\x00').strip()
        self.header['file_type'] = line1.split('\r\n')[0]

        # Integer Values 또는 Float Values
        # OpenBCI 8 Channels 등
        print(f"파일 타입: {self.header['file_type']}")

    def _read_data(self, f):
        """데이터 부분 읽기 (Integer Values 형식)"""
        # 헤더 끝 위치 찾기 (일반적으로 256바이트)
        f.seek(256)

        # 나머지 모든 데이터 읽기
        raw_data = f.read()

        # BrainBay ARC 파일 구조 분석
        # 실제로는 2바이트 signed integer (int16)가 사용됨
        # 32바이트 블록 단위로 데이터가 저장됨 (8채널 × 2바이트 = 16바이트 + 메타데이터 16바이트)

        num_channels = 8
        bytes_per_value = 2  # int16
        block_size = 32  # 전체 블록 크기

        # 전체 샘플 개수 계산
        total_bytes = len(raw_data)
        num_blocks = total_bytes // block_size

        print(f"총 바이트: {total_bytes}")
        print(f"블록 개수: {num_blocks}")

        # 데이터 언팩
        # 각 블록에서 8채널 데이터 추출
        data_array = []

        for i in range(num_blocks):
            block_offset = i * block_size
            row = []

            # 각 블록의 처음 16바이트가 8채널 데이터 (2바이트씩)
            for ch in range(num_channels):
                offset = block_offset + (ch * bytes_per_value)
                if offset + bytes_per_value <= total_bytes:
                    # Big-endian 2바이트 signed integer
                    value = struct.unpack('>h', raw_data[offset:offset+bytes_per_value])[0]
                    row.append(value)

            if len(row) == num_channels:
                data_array.append(row)

        # DataFrame 생성
        columns = [
            'EEG Channel 0',
            'EEG Channel 1',
            'EEG Channel 2',
            'EEG Channel 3',
            'EEG Channel 4',
            'EEG Channel 5',
            'EEG Channel 6',
            'EEG Channel 7'
        ]

        self.data = pd.DataFrame(data_array, columns=columns)

        # OpenBCI 스케일 변환 적용
        # BrainBay Filetrans.con 파일에서 발견한 공식: A/0.0223/100
        # 즉, raw_value / 2.23 = uV 값
        scale_factor = 2.23
        for col in columns:
            self.data[col] = self.data[col] / scale_factor

        # 실제로는 채널 이름이 다를 수 있으므로 일반적인 이름 사용
        # 소소 기기: OpenBCI 8 Channels
        # 보통 Fp1, Fp2는 Channel 0, Channel 1에 해당

        # Sample Index 추가
        self.data.insert(0, 'Sample Index', range(len(self.data)))

        print(f"DataFrame 생성 완료: {self.data.shape}")

        return self.data

    def to_excel(self, output_path):
        """Excel로 저장"""
        if self.data is None:
            self.read()

        self.data.to_excel(output_path, index=False)
        print(f"Excel 저장 완료: {output_path}")

        return output_path

    def get_channel_data(self, channel_name):
        """특정 채널 데이터 추출"""
        if self.data is None:
            self.read()

        if channel_name in self.data.columns:
            return self.data[channel_name].values
        else:
            raise ValueError(f"채널 '{channel_name}'을 찾을 수 없습니다. 사용 가능한 채널: {list(self.data.columns)}")


def convert_arc_to_excel(arc_path, excel_path=None):
    """
    ARC 파일을 Excel로 변환하는 간단한 함수

    Parameters:
    -----------
    arc_path : str
        입력 ARC 파일 경로
    excel_path : str, optional
        출력 Excel 파일 경로 (기본값: ARC 파일과 같은 이름.xlsx)

    Returns:
    --------
    excel_path : str
        생성된 Excel 파일 경로
    """
    if excel_path is None:
        excel_path = arc_path.replace('.arc', '.xlsx')

    reader = ARCReader(arc_path)
    reader.read()
    reader.to_excel(excel_path)

    return excel_path


def batch_convert_arc_folder(arc_folder, output_folder=None):
    """
    폴더 내 모든 ARC 파일을 Excel로 일괄 변환

    Parameters:
    -----------
    arc_folder : str
        ARC 파일이 있는 폴더
    output_folder : str, optional
        출력 폴더 (기본값: arc_folder/converted)

    Returns:
    --------
    converted_files : list
        변환된 파일 경로 리스트
    """
    if output_folder is None:
        output_folder = os.path.join(arc_folder, 'converted')

    os.makedirs(output_folder, exist_ok=True)

    arc_files = [f for f in os.listdir(arc_folder) if f.endswith('.arc')]
    converted_files = []

    print(f"총 {len(arc_files)}개의 ARC 파일 발견")

    for idx, arc_file in enumerate(arc_files, 1):
        arc_path = os.path.join(arc_folder, arc_file)
        excel_file = arc_file.replace('.arc', '.xlsx')
        excel_path = os.path.join(output_folder, excel_file)

        print(f"\n[{idx}/{len(arc_files)}] 변환 중: {arc_file}")

        try:
            convert_arc_to_excel(arc_path, excel_path)
            converted_files.append(excel_path)
        except Exception as e:
            print(f"오류 발생: {e}")

    print(f"\n변환 완료: {len(converted_files)}/{len(arc_files)} 파일")

    return converted_files


if __name__ == "__main__":
    # 테스트: 단일 파일 읽기
    test_arc = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 숫자.arc"

    print("=" * 60)
    print("ARC 파일 리더 테스트")
    print("=" * 60)

    reader = ARCReader(test_arc)
    df = reader.read()

    print("\n데이터 미리보기:")
    print(df.head(10))

    print("\n데이터 통계:")
    print(df.describe())

    # Excel로 저장 테스트
    output_path = test_arc.replace('.arc', '_converted.xlsx')
    reader.to_excel(output_path)
