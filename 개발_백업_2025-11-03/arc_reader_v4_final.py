"""
BrainBay ARC 파일 리더 v4 - 최종 완성본

회전 버퍼(Rotating Buffer) 디인터리빙 구현
"""

import struct
import numpy as np
import pandas as pd
import os


class ARCReaderV4:
    """
    BrainBay ARC 파일 파서 - 회전 버퍼 방식 완벽 구현

    발견 사항:
    - 32바이트 블록, 처음 16바이트가 8채널 데이터 (16-bit little-endian)
    - 데이터가 회전하며 저장됨 (각 블록마다 시작 위치가 이동)
    - 8채널을 순차적으로 회전하며 기록
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.header = {}
        self.data = None
        self.sampling_rate = 250

    def read(self):
        """ARC 파일 읽기"""
        with open(self.file_path, 'rb') as f:
            # 헤더 읽기
            self._read_header(f)

            # 회전 버퍼 데이터 파싱
            self._read_rotating_buffer(f)

        return self.data

    def _read_header(self, f):
        """헤더 파싱 (256바이트)"""
        header_bytes = f.read(256)
        header_text = header_bytes.decode('ascii', errors='ignore').strip('\x00')

        lines = header_text.split('\r\n')
        if lines:
            self.header['file_type'] = lines[0]

        print(f"파일 타입: {self.header.get('file_type', 'Unknown')}")

    def _read_rotating_buffer(self, f):
        """
        회전 버퍼 데이터 파싱

        구조:
        - 32바이트 블록
        - 처음 16바이트: 8개 위치 (각 2바이트, 16-bit little-endian signed)
        - 데이터가 회전하며 저장 (각 샘플이 다른 위치에 기록됨)
        """
        f.seek(256)
        raw_data = f.read()

        block_size = 32
        num_blocks = len(raw_data) // block_size

        print(f"\n총 바이트: {len(raw_data):,}")
        print(f"블록 크기: {block_size} bytes")
        print(f"블록 개수: {num_blocks:,}")

        # 8개 채널 버퍼 (회전 버퍼 디인터리빙)
        channels = [[] for _ in range(8)]

        current_channel = 0  # 현재 기록 중인 채널

        for block_idx in range(num_blocks):
            block_offset = block_idx * block_size
            block = raw_data[block_offset:block_offset + 16]  # 처음 16바이트만

            if len(block) < 16:
                break

            # 8개 위치에서 16-bit little-endian signed 값 읽기
            values = []
            for i in range(8):
                val = struct.unpack('<h', block[i*2:i*2+2])[0]
                values.append(val)

            # 회전 버퍼 로직:
            # 현재 채널부터 시작해서 순차적으로 데이터 추출
            for offset in range(8):
                ch_idx = (current_channel + offset) % 8
                value = values[offset]

                # 0이 아닌 값만 저장 (회전 버퍼의 특성)
                if value != 0:
                    channels[ch_idx].append(value)

            # 다음 블록은 다음 채널부터 시작
            current_channel = (current_channel + 1) % 8

        # 길이 맞추기 (가장 짧은 채널 길이로)
        min_length = min(len(ch) for ch in channels)

        print(f"\n채널별 데이터 개수:")
        for i, ch in enumerate(channels):
            print(f"  Channel {i}: {len(ch):,}")

        print(f"\n최소 길이로 통일: {min_length:,}")

        # DataFrame 생성
        data_dict = {}
        for i in range(8):
            data_dict[f'Channel {i}'] = channels[i][:min_length]

        self.data = pd.DataFrame(data_dict)

        # Sample Index 추가
        self.data.insert(0, 'Sample Index', range(len(self.data)))

        print(f"\nDataFrame 생성 완료: {self.data.shape}")
        print(f"\n첫 20행:")
        print(self.data.head(20))

        print(f"\n통계:")
        print(self.data.describe())

        return self.data

    def get_fp1_fp2_ppg(self):
        """Fp1, Fp2, PPG 추출"""
        if self.data is None:
            self.read()

        fp1_fp2_ppg = self.data[['Sample Index', 'Channel 0', 'Channel 1', 'Channel 2']].copy()
        fp1_fp2_ppg.columns = ['Sample Index', 'Fp1', 'Fp2', 'PPG']

        return fp1_fp2_ppg

    def to_excel(self, output_path):
        """Excel로 저장"""
        if self.data is None:
            self.read()

        self.data.to_excel(output_path, index=False)
        print(f"\nExcel 저장 완료: {output_path}")

        return output_path


if __name__ == "__main__":
    # 테스트
    test_arc = r"C:\Users\bach1\OneDrive\문서\05.claude\01.EEG실시간 분석 데이터\참고 개발코드\밴드형 및 이어형 디바이스 기기 연결 및 사용방법\ARC파일\07.이찬희 호흡.arc"

    print("=" * 80)
    print("ARC 파일 리더 v4 - 회전 버퍼 완전 구현")
    print("=" * 80)

    reader = ARCReaderV4(test_arc)
    df = reader.read()

    # Fp1, Fp2, PPG 추출
    print("\n" + "=" * 80)
    print("Fp1, Fp2, PPG 추출")
    print("=" * 80)

    analysis_df = reader.get_fp1_fp2_ppg()
    print(analysis_df.head(30))

    # TXT 파일과 비교
    txt_path = test_arc.replace('.arc', '.txt')
    if os.path.exists(txt_path):
        print("\n" + "=" * 80)
        print("TXT 파일과 비교")
        print("=" * 80)

        txt_df = pd.read_csv(txt_path, header=None)

        print(f"\nARC 파싱 결과:")
        print(f"  행 개수: {len(analysis_df):,}")
        print(f"  Fp1 범위: [{analysis_df['Fp1'].min():.2f}, {analysis_df['Fp1'].max():.2f}]")
        print(f"  Fp1 평균: {analysis_df['Fp1'].mean():.2f}")
        print(f"  Fp1 표준편차: {analysis_df['Fp1'].std():.2f}")

        print(f"\nTXT 파일:")
        print(f"  행 개수: {len(txt_df):,}")
        print(f"  Col0 범위: [{txt_df.iloc[:, 0].min():.2f}, {txt_df.iloc[:, 0].max():.2f}]")
        print(f"  Col0 평균: {txt_df.iloc[:, 0].mean():.2f}")
        print(f"  Col0 표준편차: {txt_df.iloc[:, 0].std():.2f}")

        # 상관계수 계산
        min_len = min(len(analysis_df), len(txt_df))
        arc_fp1 = analysis_df['Fp1'].values[:min_len]
        txt_col0 = txt_df.iloc[:min_len, 0].values

        correlation = np.corrcoef(arc_fp1, txt_col0)[0, 1]
        print(f"\n상관계수 (Fp1 vs TXT Col0): {correlation:.6f}")

        if correlation > 0.95:
            print("  => 매우 높은 일치도! (95% 이상)")
            print("  => ARC 직접 파싱 성공!")
        elif correlation > 0.8:
            print("  => 높은 일치도 (80% 이상)")
        elif correlation > 0.5:
            print("  => 중간 일치도 (50% 이상)")
        else:
            print("  => 낮은 일치도")

        # 행 개수 차이
        row_diff = abs(len(analysis_df) - len(txt_df))
        row_diff_pct = (row_diff / len(txt_df)) * 100
        print(f"\n행 개수 차이: {row_diff:,}행 ({row_diff_pct:.2f}%)")

        # 처음 20개 값 직접 비교
        print(f"\n처음 20개 값 직접 비교:")
        print(f"  ARC Fp1: {arc_fp1[:20]}")
        print(f"  TXT Col0: {txt_col0[:20]}")
