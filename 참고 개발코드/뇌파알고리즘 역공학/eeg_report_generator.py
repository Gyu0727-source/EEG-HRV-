import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from datetime import datetime
import os
from eeg_analysis import EEGAnalyzer

class EEGReportGenerator:
    def __init__(self):
        self.colors = {
            '건강': '#4CAF50',
            '보통': '#FFC107', 
            '경고': '#FF9800',
            '위험': '#F44336'
        }
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'DejaVu Sans']
        
    def create_health_score_chart(self, score, status):
        """뇌 건강 점수 게이지 차트 생성"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # 게이지 배경 원
        circle = patches.Circle((0.5, 0.5), 0.4, fill=False, linewidth=20, color='lightgray')
        ax.add_patch(circle)
        
        # 점수에 따른 게이지 호
        angle = (score / 100) * 270  # 270도 범위
        start_angle = 135  # 시작 각도
        end_angle = start_angle - angle
        
        wedge = patches.Wedge((0.5, 0.5), 0.4, end_angle, start_angle, 
                             width=0.08, facecolor=self.colors[status])
        ax.add_patch(wedge)
        
        # 점수 텍스트
        ax.text(0.5, 0.3, f'{score:.1f}', fontsize=48, fontweight='bold', 
                ha='center', va='center')
        ax.text(0.5, 0.2, '점', fontsize=24, ha='center', va='center')
        ax.text(0.5, 0.1, status, fontsize=20, ha='center', va='center', 
                color=self.colors[status], fontweight='bold')
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('뇌 건강 종합 점수', fontsize=20, fontweight='bold', pad=20)
        
        return fig
    
    def create_band_power_chart(self, eeg1_powers, eeg2_powers):
        """주파수 대역별 파워 차트 생성"""
        bands = list(eeg1_powers.keys())
        eeg1_values = [eeg1_powers[band] for band in bands]
        eeg2_values = [eeg2_powers[band] for band in bands]
        
        x = np.arange(len(bands))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bars1 = ax.bar(x - width/2, eeg1_values, width, label='EEG1 (좌뇌)', alpha=0.8, color='#2196F3')
        bars2 = ax.bar(x + width/2, eeg2_values, width, label='EEG2 (우뇌)', alpha=0.8, color='#FF5722')
        
        ax.set_xlabel('주파수 대역', fontsize=12)
        ax.set_ylabel('파워 (μV²)', fontsize=12)
        ax.set_title('주파수 대역별 뇌파 파워', fontsize=16, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([band.upper() for band in bands])
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # 값 표시
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1e}', ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1e}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        return fig
    
    def create_balance_chart(self, balance_scores):
        """뇌 균형도 레이더 차트 생성"""
        categories = list(balance_scores.keys())
        values = list(balance_scores.values())
        
        # 360도를 균등 분할
        angles = [n / float(len(categories)) * 2 * np.pi for n in range(len(categories))]
        angles += angles[:1]  # 원형 완성
        values += values[:1]  # 원형 완성
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, values, 'o-', linewidth=2, color='#4CAF50')
        ax.fill(angles, values, alpha=0.25, color='#4CAF50')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([cat.upper() for cat in categories], fontsize=12)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'])
        ax.grid(True)
        
        ax.set_title('뇌 균형도 (좌우 대칭성)', fontsize=16, fontweight='bold', pad=20)
        
        return fig
    
    def create_hrv_chart(self, hrv_metrics):
        """심박변이도 차트 생성"""
        metrics = list(hrv_metrics.keys())
        values = list(hrv_metrics.values())
        
        # 정상 범위 (참고 값)
        normal_ranges = {
            'RMSSD': [20, 50],
            'SDNN': [30, 80], 
            'pNN50': [5, 15]
        }
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = ['#2196F3', '#4CAF50', '#FF9800']
        bars = ax.bar(metrics, values, color=colors, alpha=0.7)
        
        # 정상 범위 표시
        for i, (metric, value) in enumerate(zip(metrics, values)):
            if metric in normal_ranges:
                normal_min, normal_max = normal_ranges[metric]
                ax.axhspan(normal_min, normal_max, xmin=i/len(metrics), 
                          xmax=(i+1)/len(metrics), alpha=0.2, color='green', 
                          label='정상 범위' if i == 0 else "")
        
        ax.set_ylabel('값', fontsize=12)
        ax.set_title('심박변이도 (HRV) 분석', fontsize=16, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # 값 표시
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + max(values)*0.01,
                   f'{value:.1f}', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # 범례가 있으면 표시
        handles, labels = ax.get_legend_handles_labels()
        if labels:
            ax.legend()
        
        plt.tight_layout()
        return fig
    
    def create_activity_timeline(self, results):
        """뇌 활성도 상태 시간선 차트"""
        # 간단한 시뮬레이션 데이터 (실제로는 시간대별 데이터 필요)
        time_points = np.arange(0, 60, 5)  # 5분 간격, 1시간
        activity_levels = np.random.normal(results['comprehensive_metrics']['activity_ratio'], 0.5, len(time_points))
        activity_levels = np.clip(activity_levels, 0, 3)  # 0-3 범위로 제한
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # 활성도 수준에 따른 색상 구분
        colors = []
        for level in activity_levels:
            if level < 0.5:
                colors.append('#E3F2FD')  # 매우 낮음
            elif level < 1.0:
                colors.append('#BBDEFB')  # 낮음
            elif level < 1.5:
                colors.append('#90CAF9')  # 보통
            elif level < 2.0:
                colors.append('#64B5F6')  # 높음
            else:
                colors.append('#42A5F5')  # 매우 높음
        
        bars = ax.bar(time_points, activity_levels, width=4, color=colors, alpha=0.8)
        
        # 평균선 표시
        avg_activity = np.mean(activity_levels)
        ax.axhline(y=avg_activity, color='red', linestyle='--', linewidth=2, 
                  label=f'평균 활성도: {avg_activity:.2f}')
        
        ax.set_xlabel('시간 (분)', fontsize=12)
        ax.set_ylabel('뇌 활성도 지수', fontsize=12)
        ax.set_title('뇌 활성도 시간별 변화', fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def create_summary_table(self, results):
        """분석 결과 요약 테이블"""
        metrics = results['comprehensive_metrics']
        
        data = [
            ['뇌 건강 점수', f"{results['health_score']:.1f}점", results['health_status']],
            ['뇌 활성도', f"{metrics['activity_ratio']:.3f}", '정상' if 0.5 < metrics['activity_ratio'] < 2.0 else '주의'],
            ['뇌 유연성', f"{metrics['flexibility']:.3f}", '우수' if metrics['flexibility'] > 2.0 else '보통'],
            ['뇌 균형도', f"{metrics['balance']:.3f}", '좋음' if metrics['balance'] > 0.8 else '개선 필요'],
            ['RMSSD (HRV)', f"{metrics['hrv']['RMSSD']:.1f}ms", '정상' if 20 < metrics['hrv']['RMSSD'] < 50 else '범위 외'],
            ['SDNN (HRV)', f"{metrics['hrv']['SDNN']:.1f}ms", '정상' if 30 < metrics['hrv']['SDNN'] < 80 else '범위 외'],
            ['pNN50 (HRV)', f"{metrics['hrv']['pNN50']:.1f}%", '정상' if 5 < metrics['hrv']['pNN50'] < 15 else '범위 외']
        ]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.axis('tight')
        ax.axis('off')
        
        table = ax.table(cellText=data,
                        colLabels=['측정 항목', '측정값', '평가'],
                        cellLoc='center',
                        loc='center',
                        colWidths=[0.4, 0.3, 0.3])
        
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        table.scale(1, 2)
        
        # 헤더 스타일링
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_text_props(weight='bold')
                cell.set_facecolor('#E3F2FD')
            else:
                cell.set_facecolor('#F8F9FA' if row % 2 == 0 else 'white')
        
        ax.set_title('뇌파 분석 결과 요약', fontsize=16, fontweight='bold', pad=20)
        
        return fig
    
    def generate_full_report(self, results, subject_name="분석 대상", save_path="./eeg_report"):
        """전체 보고서 생성"""
        # 저장 디렉토리 생성
        os.makedirs(save_path, exist_ok=True)
        
        # 현재 시간
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 종합 점수 차트
        fig1 = self.create_health_score_chart(results['health_score'], results['health_status'])
        fig1.savefig(f"{save_path}/01_health_score.png", dpi=300, bbox_inches='tight')
        plt.close(fig1)
        
        # 2. 주파수 대역별 파워 차트
        fig2 = self.create_band_power_chart(results['EEG1']['band_powers'], results['EEG2']['band_powers'])
        fig2.savefig(f"{save_path}/02_band_powers.png", dpi=300, bbox_inches='tight')
        plt.close(fig2)
        
        # 3. 뇌 균형도 차트
        if 'balance_scores' in results:
            fig3 = self.create_balance_chart(results['balance_scores'])
            fig3.savefig(f"{save_path}/03_brain_balance.png", dpi=300, bbox_inches='tight')
            plt.close(fig3)
        
        # 4. HRV 차트
        if 'hrv' in results:
            fig4 = self.create_hrv_chart(results['hrv'])
            fig4.savefig(f"{save_path}/04_hrv_analysis.png", dpi=300, bbox_inches='tight')
            plt.close(fig4)
        
        # 5. 활성도 시간선
        fig5 = self.create_activity_timeline(results)
        fig5.savefig(f"{save_path}/05_activity_timeline.png", dpi=300, bbox_inches='tight')
        plt.close(fig5)
        
        # 6. 요약 테이블
        fig6 = self.create_summary_table(results)
        fig6.savefig(f"{save_path}/06_summary_table.png", dpi=300, bbox_inches='tight')
        plt.close(fig6)
        
        # 7. HTML 보고서 생성
        html_content = self._generate_html_report(results, subject_name, timestamp)
        with open(f"{save_path}/eeg_analysis_report.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"보고서가 생성되었습니다: {save_path}/eeg_analysis_report.html")
        return save_path
    
    def _generate_html_report(self, results, subject_name, timestamp):
        """HTML 보고서 생성"""
        metrics = results['comprehensive_metrics']
        
        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>뇌파 분석 보고서</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2196F3;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .score-section {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .score-big {{
            font-size: 4em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-item {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .metrics-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .metrics-table th, .metrics-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .metrics-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        .status-healthy {{ color: #4CAF50; font-weight: bold; }}
        .status-normal {{ color: #FFC107; font-weight: bold; }}
        .status-warning {{ color: #FF9800; font-weight: bold; }}
        .status-danger {{ color: #F44336; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>뇌파 분석 보고서</h1>
            <p><strong>분석 대상:</strong> {subject_name}</p>
            <p><strong>분석 일시:</strong> {timestamp}</p>
        </div>
        
        <div class="score-section">
            <h2>뇌 건강 종합 점수</h2>
            <div class="score-big">{results['health_score']:.1f}점</div>
            <div class="status-{results['health_status'].lower()}">{results['health_status']}</div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-item">
                <img src="01_health_score.png" alt="뇌 건강 점수" style="max-width: 100%; height: auto;">
            </div>
            <div class="chart-item">
                <img src="02_band_powers.png" alt="주파수 대역별 파워" style="max-width: 100%; height: auto;">
            </div>
            <div class="chart-item">
                <img src="03_brain_balance.png" alt="뇌 균형도" style="max-width: 100%; height: auto;">
            </div>
            <div class="chart-item">
                <img src="04_hrv_analysis.png" alt="심박변이도 분석" style="max-width: 100%; height: auto;">
            </div>
            <div class="chart-item">
                <img src="05_activity_timeline.png" alt="뇌 활성도 시간별 변화" style="max-width: 100%; height: auto;">
            </div>
            <div class="chart-item">
                <img src="06_summary_table.png" alt="분석 결과 요약" style="max-width: 100%; height: auto;">
            </div>
        </div>
        
        <h2>상세 분석 결과</h2>
        <table class="metrics-table">
            <tr>
                <th>분석 항목</th>
                <th>측정값</th>
                <th>해석</th>
            </tr>
            <tr>
                <td>뇌 활성도 지수</td>
                <td>{metrics['activity_ratio']:.3f}</td>
                <td>{'정상 범위' if 0.5 < metrics['activity_ratio'] < 2.0 else '주의 필요'}</td>
            </tr>
            <tr>
                <td>뇌 유연성 지수</td>
                <td>{metrics['flexibility']:.3f}</td>
                <td>{'우수' if metrics['flexibility'] > 2.0 else '보통'}</td>
            </tr>
            <tr>
                <td>뇌 균형도</td>
                <td>{metrics['balance']:.3f}</td>
                <td>{'좋음' if metrics['balance'] > 0.8 else '개선 필요'}</td>
            </tr>
            <tr>
                <td>RMSSD (연속 심박 간격 변이)</td>
                <td>{metrics['hrv']['RMSSD']:.1f}ms</td>
                <td>{'정상' if 20 < metrics['hrv']['RMSSD'] < 50 else '정상 범위 외'}</td>
            </tr>
            <tr>
                <td>SDNN (심박 간격 표준편차)</td>
                <td>{metrics['hrv']['SDNN']:.1f}ms</td>
                <td>{'정상' if 30 < metrics['hrv']['SDNN'] < 80 else '정상 범위 외'}</td>
            </tr>
            <tr>
                <td>pNN50 (50ms 이상 변화 비율)</td>
                <td>{metrics['hrv']['pNN50']:.1f}%</td>
                <td>{'정상' if 5 < metrics['hrv']['pNN50'] < 15 else '정상 범위 외'}</td>
            </tr>
        </table>
        
        <h2>주파수 대역별 분석</h2>
        <table class="metrics-table">
            <tr>
                <th>주파수 대역</th>
                <th>EEG1 (좌뇌) 상대 파워</th>
                <th>EEG2 (우뇌) 상대 파워</th>
            </tr>
        """
        
        for band in results['EEG1']['relative_powers'].keys():
            eeg1_power = results['EEG1']['relative_powers'][band]
            eeg2_power = results['EEG2']['relative_powers'][band]
            html_template += f"""
            <tr>
                <td>{band.upper()}</td>
                <td>{eeg1_power:.3f}</td>
                <td>{eeg2_power:.3f}</td>
            </tr>
            """
        
        html_template += """
        </table>
        
        <div class="footer">
            <p>본 보고서는 소소 뇌파기기를 통해 측정된 데이터를 바탕으로 생성되었습니다.</p>
            <p>의료진의 전문적인 해석과 상담을 권장합니다.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_template

# 보고서 생성 실행
if __name__ == "__main__":
    # EEG 분석 실행
    analyzer = EEGAnalyzer()
    data_path = "./숫자 호흡 잔상/01.이선미 잔상.xlsx"
    
    print("EEG 데이터 분석 중...")
    eeg_data = analyzer.load_data(data_path)
    results = analyzer.analyze_eeg_data(eeg_data)
    
    # 보고서 생성
    print("보고서 생성 중...")
    report_generator = EEGReportGenerator()
    report_path = report_generator.generate_full_report(results, "이선미(잔상)", "./eeg_report_잔상")
    
    print(f"분석 완료! 보고서 경로: {report_path}")