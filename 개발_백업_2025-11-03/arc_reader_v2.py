"""
BrainBay ARC 파일 리더 v2
24-bit 데이터 구조 지원
"""

import struct
import numpy as np
import pandas as pd
import os


class ARCReaderV2:
    """BrainBay ARC 파일 파서 (개선 버전)"""

    def __init__(self, file_path):
        self.file_path = file_path
        self.header = {}
        self.data = None
        self.sampling_rate = 250  # OpenBCI 기본 샘플링 레이트

    def read(self):
        """ARC 파일 읽기"""
        with open(self.file_path, 'rb') as f:
            # 헤더 읽기
            self._read_header(f)

            # 데이터 읽기 (24-bit 버전 시도)
            self._read_data_24bit(f)

        return self.data

    def _read_header(self, f):
        """헤더 정보 읽기"""
        line1 = f.read(256).decode('ascii', errors='ignore').strip('\x00').strip()
        self.header['file_type'] = line1.split('\r\n')[0]
        print(f"파일 타입: {self.header['file_type']}")

    def _read_data_24bit(self, f):
        """
        데이터 부분 읽기 (24-bit 가능성)

        OpenBCI는 24-bit ADC 사용
        3바이트 × 8채널 = 24바이트 + 8바이트 메타데이터 = 32바이트
        """
        f.seek(256)
        raw_data = f.read()

        num_channels = 8
        bytes_per_value = 3  # 24-bit
        block_size = 32

        total_bytes = len(raw_data)
        num_blocks = total_bytes // block_size

        print(f"총 바이트: {total_bytes}")
        print(f"블록 개수: {num_blocks}")
        print(f"24-bit 모드 (3바이트/채널)")

        data_array = []

        for i in range(num_blocks):
            block_offset = i * block_size
            row = []

            # 24바이트 = 8채널 × 3바이트
            for ch in range(num_channels):
                offset = block_offset + (ch * bytes_per_value)
                if offset + bytes_per_value <= total_bytes:
                    # 3바이트를 읽어서 signed 24-bit integer로 변환
                    three_bytes = raw_data[offset:offset+bytes_per_value]

                    # Little-endian 24-bit signed integer
                    # 3바이트를 4바이트로 확장 후 int32로 변환
                    value_bytes = three_bytes + b'\x00'  # 4번째 바이트 추가
                    value = struct.unpack('<i', value_bytes)[0] >> 8  # 8비트 오른쪽 시프트

                    # 24-bit signed 값 처리 (sign extension)
                    if value & 0x800000:  # 음수인 경우
                        value = value - 0x1000000

                    row.append(value)

            if len(row) == num_channels:
                data_array.append(row)

        # DataFrame 생성
        columns = [f'Channel {i}' for i in range(num_channels)]
        self.data = pd.DataFrame(data_array, columns=columns)

        # OpenBCI 스케일 변환 적용
        # 24-bit ADC: ±187,500 μV range
        # Resolution: 187500 * 2 / 2^24 = 0.0223 μV
        scale_factor = 0.0223

        for col in columns:
            self.data[col] = self.data[col] * scale_factor

        # Sample Index 추가
        self.data.insert(0, 'Sample Index', range(len(self.data)))

        print(f"DataFrame 생성 완료: {self.data.shape}")
        print(f"\n첫 10행:")
        print(self.data.head(10))

        print(f"\n통계:")
        print(self.data.describe())

        return self.data

    def to_excel(self, output_path):
        """Excel로 저장"""
        if self.data is None:
            self.read()

        self.data.to_excel(output_path, index=False)
        print(f"Excel 저장 완료: {output_path}")

        return output_path

    def get_fp1_fp2_ppg(self):
        """Fp1, Fp2, PPG 추출 (Channel 0, 1, 2)"""
        if self.data is None:
            self.read()

        fp1_fp2_ppg = self.data[['Sample Index', 'Channel 0', 'Channel 1', 'Channel 2']].copy()
        fp1_fp2_ppg.columns = ['Sample Index', 'Fp1', 'Fp2', 'PPG']

        return fp1_fp2_ppg


if __name__ == "__main__":
    # 테스트: 24-bit 파싱
    test_arc = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 호흡.arc"

    print("=" * 80)
    print("ARC 파일 리더 v2 테스트 (24-bit)")
    print("=" * 80)

    reader = ARCReaderV2(test_arc)
    df = reader.read()

    # TXT 파일과 비교
    txt_path = test_arc.replace('.arc', '.txt')
    txt_df = pd.read_csv(txt_path, header=None)

    print("\n" + "=" * 80)
    print("TXT 파일과 비교")
    print("=" * 80)
    print(f"\nTXT 첫 10행:")
    print(txt_df.head(10))

    print(f"\nARC Channel 0 vs TXT Column 0:")
    print(f"  ARC: {df['Channel 0'].head(10).values}")
    print(f"  TXT: {txt_df[0].head(10).values}")

    print(f"\nARC Channel 1 vs TXT Column 1:")
    print(f"  ARC: {df['Channel 1'].head(10).values}")
    print(f"  TXT: {txt_df[1].head(10).values}")

    print(f"\nARC Channel 2 vs TXT Column 2:")
    print(f"  ARC: {df['Channel 2'].head(10).values}")
    print(f"  TXT: {txt_df[2].head(10).values}")
