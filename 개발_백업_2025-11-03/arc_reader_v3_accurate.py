"""
BrainBay ARC 파일 리더 v3 - 정확한 OpenBCI 파싱

BrainBay 소스코드 및 OpenBCI 공식 문서 기반으로 구현
"""

import struct
import numpy as np
import pandas as pd
import os


class ARCReaderV3:
    """
    BrainBay ARC 파일 파서 (OpenBCI 전용, 정확한 구현)

    기반:
    - BrainBay 소스코드 (files.cpp, ob_eeg.cpp)
    - OpenBCI Cyton 데이터 형식 공식 문서
    - Filetrans_band.con 설정 파일
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.header = {}
        self.data = None
        self.sampling_rate = 250  # OpenBCI Cyton 기본

        # OpenBCI 스케일 팩터
        # (Volts/count) = 4.5V / gain / (2^23 - 1)
        # gain = 24x (기본값)
        # 4.5 / 24 / (2^23 - 1) = 0.0223 μV/count
        self.scale_factor = 0.0223

    def read(self):
        """ARC 파일 읽기"""
        with open(self.file_path, 'rb') as f:
            # 헤더 읽기
            self._read_header(f)

            # OpenBCI 데이터 파싱
            self._read_openbci_data(f)

        return self.data

    def _read_header(self, f):
        """
        헤더 파싱 (256바이트)

        BrainBay Archive File 헤더 구조:
        - 파일 타입 설명
        - 데이터 형식 (Integer/Float/Text)
        - 디바이스 타입 (OpenBCI 8 Channels)
        """
        header_bytes = f.read(256)
        header_text = header_bytes.decode('ascii', errors='ignore').strip('\x00')

        lines = header_text.split('\r\n')
        if lines:
            self.header['file_type'] = lines[0]

        print(f"파일 타입: {self.header.get('file_type', 'Unknown')}")
        print(f"헤더 크기: 256 bytes")

    def _read_openbci_data(self, f):
        """
        OpenBCI 데이터 파싱

        데이터 구조 (BrainBay Integer Mode):
        - 33바이트 패킷 반복
        - Byte 0: 0xA0 (헤더)
        - Byte 1: Sample ID
        - Bytes 2-25: 8채널 EEG (각 3바이트, 24-bit MSB first)
        - Bytes 26-31: 가속도계 (3축, 각 2바이트)
        - Byte 32: 0xC0 (Footer)
        """
        # 헤더 이후 데이터 시작
        f.seek(256)
        raw_data = f.read()

        packet_size = 33  # OpenBCI Cyton 패킷 크기
        total_bytes = len(raw_data)
        num_packets = total_bytes // packet_size

        print(f"\n총 바이트: {total_bytes:,}")
        print(f"패킷 크기: {packet_size} bytes")
        print(f"패킷 개수: {num_packets:,}")

        # 데이터 추출
        eeg_data = []
        aux_data = []

        for i in range(num_packets):
            packet_offset = i * packet_size
            packet = raw_data[packet_offset:packet_offset + packet_size]

            if len(packet) < packet_size:
                break

            # 헤더 체크
            header_byte = packet[0]
            sample_id = packet[1]
            footer_byte = packet[32]

            # OpenBCI 패킷 검증 (선택사항)
            # if header_byte != 0xA0 or (footer_byte & 0xF0) != 0xC0:
            #     continue

            # EEG 채널 8개 (Bytes 2-25)
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
                    value_24bit |= 0xFF000000  # Sign extension
                    value_signed = struct.unpack('>i', struct.pack('>I', value_24bit))[0]
                else:
                    value_signed = value_24bit

                # μV로 변환
                value_uv = value_signed * self.scale_factor
                eeg_channels.append(value_uv)

            eeg_data.append(eeg_channels)

            # 가속도계 데이터 (Bytes 26-31)
            # 3축 × 2바이트 (16-bit signed, big-endian)
            accel_x = struct.unpack('>h', packet[26:28])[0]
            accel_y = struct.unpack('>h', packet[28:30])[0]
            accel_z = struct.unpack('>h', packet[30:32])[0]

            aux_data.append([accel_x, accel_y, accel_z])

        # DataFrame 생성
        eeg_columns = [f'Channel {i+1}' for i in range(8)]
        self.data = pd.DataFrame(eeg_data, columns=eeg_columns)

        # 가속도계 추가 (선택사항)
        aux_df = pd.DataFrame(aux_data, columns=['Accel_X', 'Accel_Y', 'Accel_Z'])
        self.data = pd.concat([self.data, aux_df], axis=1)

        # Sample Index 추가
        self.data.insert(0, 'Sample Index', range(len(self.data)))

        print(f"\nDataFrame 생성 완료: {self.data.shape}")
        print(f"\n첫 10행:")
        print(self.data.head(10))

        print(f"\n통계:")
        print(self.data[eeg_columns].describe())

        return self.data

    def get_fp1_fp2_ppg(self):
        """
        Fp1, Fp2, PPG 추출

        BrainBay TXT 파일에서:
        - Column 0: Channel 1 (Fp1 - 좌뇌)
        - Column 1: Channel 2 (Fp2 - 우뇌)
        - Column 2: Channel 3 (PPG - 심박)
        """
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
    print("ARC 파일 리더 v3 - 정확한 OpenBCI 파싱")
    print("=" * 80)

    reader = ARCReaderV3(test_arc)
    df = reader.read()

    # Fp1, Fp2, PPG 추출
    print("\n" + "=" * 80)
    print("Fp1, Fp2, PPG 추출")
    print("=" * 80)

    analysis_df = reader.get_fp1_fp2_ppg()
    print(analysis_df.head(20))

    # TXT 파일과 비교
    txt_path = test_arc.replace('.arc', '.txt')
    if os.path.exists(txt_path):
        print("\n" + "=" * 80)
        print("TXT 파일과 비교")
        print("=" * 80)

        txt_df = pd.read_csv(txt_path, header=None, names=['Fp1', 'Fp2', 'PPG'] + [f'Col{i}' for i in range(3, 11)])

        print(f"\nARC 파싱 결과:")
        print(f"  행 개수: {len(analysis_df):,}")
        print(f"  Fp1 범위: [{analysis_df['Fp1'].min():.2f}, {analysis_df['Fp1'].max():.2f}]")
        print(f"  Fp1 평균: {analysis_df['Fp1'].mean():.2f}")

        print(f"\nTXT 파일:")
        print(f"  행 개수: {len(txt_df):,}")
        print(f"  Fp1 범위: [{txt_df['Fp1'].min():.2f}, {txt_df['Fp1'].max():.2f}]")
        print(f"  Fp1 평균: {txt_df['Fp1'].mean():.2f}")

        # 상관계수 계산
        min_len = min(len(analysis_df), len(txt_df))
        arc_fp1 = analysis_df['Fp1'].values[:min_len]
        txt_fp1 = txt_df['Fp1'].values[:min_len]

        correlation = np.corrcoef(arc_fp1, txt_fp1)[0, 1]
        print(f"\n상관계수 (Fp1): {correlation:.4f}")

        if correlation > 0.95:
            print("  => 매우 높은 일치도! ARC 직접 파싱 성공!")
        elif correlation > 0.8:
            print("  => 높은 일치도 (일부 차이 있음)")
        else:
            print("  => 낮은 일치도 (추가 보정 필요)")
