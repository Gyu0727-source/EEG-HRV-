"""
BrainBay ARC 파일 리더 v5 - 패킷 동기화 구현

OpenBCI 33바이트 패킷을 정확히 찾아서 파싱
"""

import struct
import numpy as np
import pandas as pd
import os


class ARCReaderV5:
    """
    BrainBay ARC 파일 파서 - OpenBCI 패킷 동기화 완벽 구현

    OpenBCI Cyton 패킷 구조 (33바이트):
    - Byte 0: 0xA0 (헤더)
    - Byte 1: Sample ID
    - Bytes 2-25: 8채널 EEG (각 3바이트, 24-bit MSB first)
    - Bytes 26-31: 가속도계 (3축, 각 2바이트)
    - Byte 32: 0xC0 (Footer)
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.header = {}
        self.data = None
        self.sampling_rate = 250
        self.scale_factor = 0.0223  # μV/count

    def read(self):
        """ARC 파일 읽기"""
        with open(self.file_path, 'rb') as f:
            # 헤더 읽기
            self._read_header(f)

            # OpenBCI 패킷 동기화 및 파싱
            self._read_synced_packets(f)

        return self.data

    def _read_header(self, f):
        """헤더 파싱 (256바이트)"""
        header_bytes = f.read(256)
        header_text = header_bytes.decode('ascii', errors='ignore').strip('\x00')

        lines = header_text.split('\r\n')
        if lines:
            self.header['file_type'] = lines[0]

        print(f"파일 타입: {self.header.get('file_type', 'Unknown')}")

    def _read_synced_packets(self, f):
        """
        OpenBCI 패킷 동기화 및 파싱

        0xA0 헤더를 찾아서 33바이트 패킷 추출
        """
        f.seek(256)
        raw_data = f.read()

        print(f"\n총 바이트: {len(raw_data):,}")

        # 0xA0 헤더 찾기 (패킷 동기화)
        packets = []
        i = 0

        while i < len(raw_data) - 33:
            # 0xA0 헤더 찾기
            if raw_data[i] == 0xA0:
                # 33바이트 패킷 추출
                packet = raw_data[i:i+33]

                # Footer 검증 (0xCX 형식)
                if len(packet) == 33 and (packet[32] & 0xF0) == 0xC0:
                    packets.append(packet)
                    i += 33  # 다음 패킷으로
                else:
                    i += 1  # 잘못된 패킷, 다음 바이트 검색
            else:
                i += 1

        print(f"동기화된 패킷 개수: {len(packets):,}")

        if len(packets) == 0:
            print("경고: 유효한 패킷을 찾지 못했습니다!")
            print("ARC 파일이 OpenBCI 형식이 아닐 수 있습니다.")
            return None

        # 패킷 파싱
        eeg_data = []
        aux_data = []

        for packet in packets:
            # EEG 8채널 (Bytes 2-25)
            eeg_channels = []
            for ch in range(8):
                byte_offset = 2 + (ch * 3)

                # 24-bit signed integer (MSB first / Big-endian)
                byte1 = packet[byte_offset]
                byte2 = packet[byte_offset + 1]
                byte3 = packet[byte_offset + 2]

                # 24-bit 조합
                value_24bit = (byte1 << 16) | (byte2 << 8) | byte3

                # Sign extension (24-bit → 32-bit signed)
                if value_24bit & 0x800000:  # 음수 체크
                    value_signed = value_24bit | 0xFF000000
                    value_signed = struct.unpack('>i', struct.pack('>I', value_signed))[0]
                else:
                    value_signed = value_24bit

                # μV로 변환
                value_uv = value_signed * self.scale_factor
                eeg_channels.append(value_uv)

            eeg_data.append(eeg_channels)

            # 가속도계 데이터 (Bytes 26-31)
            accel_x = struct.unpack('>h', packet[26:28])[0]
            accel_y = struct.unpack('>h', packet[28:30])[0]
            accel_z = struct.unpack('>h', packet[30:32])[0]

            aux_data.append([accel_x, accel_y, accel_z])

        # DataFrame 생성
        eeg_columns = [f'Channel {i+1}' for i in range(8)]
        self.data = pd.DataFrame(eeg_data, columns=eeg_columns)

        # 가속도계 추가
        aux_df = pd.DataFrame(aux_data, columns=['Accel_X', 'Accel_Y', 'Accel_Z'])
        self.data = pd.concat([self.data, aux_df], axis=1)

        # Sample Index 추가
        self.data.insert(0, 'Sample Index', range(len(self.data)))

        print(f"\nDataFrame 생성 완료: {self.data.shape}")
        print(f"\n첫 20행:")
        print(self.data.head(20))

        print(f"\n통계 (EEG 채널):")
        print(self.data[eeg_columns].describe())

        return self.data

    def get_fp1_fp2_ppg(self):
        """Fp1, Fp2, PPG 추출"""
        if self.data is None:
            self.read()

        fp1_fp2_ppg = self.data[['Sample Index', 'Channel 1', 'Channel 2', 'Channel 3']].copy()
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
    print("ARC 파일 리더 v5 - OpenBCI 패킷 동기화")
    print("=" * 80)

    reader = ARCReaderV5(test_arc)
    df = reader.read()

    if df is not None:
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
                print("  => SUCCESS! 매우 높은 일치도! (95% 이상)")
                print("  => ARC 직접 파싱 완전 성공!")
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
