"""
EEG 실시간 분석 프로젝트 - 보고서 생성 모듈 V2 (개선 버전)

주요 개선사항:
1. 더 정교한 해석 (초반/중반/후반 구분)
2. 참고 보고서 스타일 적용
3. 변화점 정보 포함
"""

import os
import base64
import numpy as np
from datetime import datetime
import config


# 개선된 해석 템플릿 정의
INTERPRETATION_TEMPLATES = {
    'delta': {
        'increase_increase': """
            델타파가 지속적으로 증가하여 깊은 이완 상태로 진입했습니다.
            측정 중 수면 준비 상태에 가까워졌음을 의미합니다.
        """,
        'decrease_decrease': """
            델타파가 계속 감소하여 각성 수준이 높아졌습니다.
            측정 환경에 적응하면서 주의력이 증가하는 자연스러운 반응입니다.
        """,
        'increase_stable': """
            초반에 이완이 증가한 후 안정적인 상태를 유지했습니다.
            편안한 측정 환경에서 일정한 휴식 상태를 보이고 있습니다.
        """,
        'decrease_stable': """
            초반에 각성도가 높아진 후 안정화되었습니다.
            적절한 주의 수준을 유지하고 있습니다.
        """,
        'stable_increase': """
            중반부터 이완이 증가했습니다.
            측정에 익숙해지면서 긴장이 풀리고 있습니다.
        """,
        'stable_decrease': """
            중반부터 각성도가 높아졌습니다.
            측정 과제에 집중하고 있음을 나타냅니다.
        """,
        'default': """
            델타파의 자연스러운 변화가 관찰되었습니다.
            이완과 각성 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'theta': {
        'increase_increase': """
            세타파가 지속적으로 증가했습니다.
            명상적 상태가 깊어지고 창의적 사고가 활성화되었습니다.
        """,
        'decrease_decrease': """
            세타파가 계속 감소했습니다.
            주의 집중 상태로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 명상적 상태가 증가한 후 유지되었습니다.
            안정적인 이완 집중 상태를 보이고 있습니다.
        """,
        'stable_decrease': """
            중반부터 세타파가 감소했습니다.
            보다 깨어있는 각성 상태로 전환되고 있습니다.
        """,
        'default': """
            세타파의 균형잡힌 변화가 관찰되었습니다.
            이완과 집중 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'alpha': {
        'increase_increase': """
            알파파가 지속적으로 증가했습니다.
            편안하고 이완된 각성 상태가 깊어지고 있으며, 스트레스가 효과적으로 감소하고 있습니다.
        """,
        'decrease_decrease': """
            알파파가 계속 감소했습니다.
            주의 집중이 필요한 활동으로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 알파파가 증가한 후 안정화되었습니다.
            이상적인 이완 상태를 잘 유지하고 있습니다.
        """,
        'stable_increase': """
            중반부터 알파파가 증가했습니다.
            측정에 적응하면서 점점 편안해지고 있습니다.
        """,
        'decrease_stable': """
            초반에 알파파가 감소한 후 안정화되었습니다.
            적절한 각성 수준을 유지하고 있습니다.
        """,
        'stable_stable': """
            전체 구간에서 알파파가 안정적으로 유지되었습니다.
            일정한 이완된 각성 상태를 잘 유지하고 있습니다.
        """,
        'default': """
            알파파의 자연스러운 변화가 관찰되었습니다.
            이완된 각성 상태를 적절히 유지하고 있습니다.
        """
    },
    'beta': {
        'increase_increase': """
            베타파가 지속적으로 증가했습니다.
            인지 활동과 집중력이 점점 높아지고 있습니다.
        """,
        'decrease_decrease': """
            베타파가 계속 감소했습니다.
            긴장이 풀리고 이완 상태로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 집중도가 증가한 후 유지되었습니다.
            적절한 집중 상태를 안정적으로 유지하고 있습니다.
        """,
        'decrease_stable': """
            초반에 긴장이 풀린 후 안정화되었습니다.
            편안하면서도 깨어있는 상태를 유지하고 있습니다.
        """,
        'default': """
            베타파의 균형잡힌 변화가 관찰되었습니다.
            집중과 이완 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'gamma': {
        'increase_increase': """
            감마파가 지속적으로 증가했습니다.
            고도의 인지 처리와 정보 통합이 활발히 일어나고 있습니다.
        """,
        'decrease_decrease': """
            감마파가 계속 감소했습니다.
            인지 부하가 줄어들고 있습니다.
        """,
        'increase_stable': """
            초반에 인지 활동이 증가한 후 유지되었습니다.
            활발한 정보 처리를 안정적으로 수행하고 있습니다.
        """,
        'decrease_stable': """
            초반에 인지 부하가 감소한 후 안정화되었습니다.
            적절한 수준의 정보 처리를 유지하고 있습니다.
        """,
        'default': """
            감마파의 자연스러운 변화가 관찰되었습니다.
            균형잡힌 인지 활동이 이루어지고 있습니다.
        """
    }
}


def generate_interpretation(band_name, smoothed_data, change_points, change_types):
    """
    변화 패턴을 분석하여 자동 해석 생성 (정교한 버전)

    초반/중반/후반으로 구간을 나누어 상세 분석
    """
    # 시계열 데이터 길이 (초 단위)
    total_duration = len(smoothed_data)

    # 초반/중반/후반 구간 나누기
    early_end = total_duration // 3
    mid_end = (total_duration * 2) // 3

    # 각 구간의 평균값 계산
    early_mean = np.mean(smoothed_data[:early_end])
    mid_mean = np.mean(smoothed_data[early_end:mid_end])
    late_mean = np.mean(smoothed_data[mid_end:])

    # 구간별 변화 판단
    def get_trend(val1, val2):
        diff = ((val2 - val1) / val1 * 100) if val1 > 0 else 0
        if diff > 10:
            return "증가", "increase"
        elif diff < -10:
            return "감소", "decrease"
        else:
            return "유지", "stable"

    early_to_mid_kr, early_to_mid_en = get_trend(early_mean, mid_mean)
    mid_to_late_kr, mid_to_late_en = get_trend(mid_mean, late_mean)

    # 시간 포맷팅
    def format_duration(seconds):
        if seconds < 60:
            return f"{seconds}초"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            if secs > 0:
                return f"{minutes}분 {secs}초"
            return f"{minutes}분"

    early_time = format_duration(early_end)
    mid_time = format_duration(mid_end)
    total_time = format_duration(total_duration)

    # 구간별 상세 설명
    phase_html = f"""
        <span class="phase">초반(0-{early_time}):</span> {early_mean:.1f} μV² - {early_to_mid_kr}<br>
        <span class="phase">중반({early_time}-{mid_time}):</span> {mid_mean:.1f} μV² - {mid_to_late_kr}<br>
        <span class="phase">후반({mid_time}-{total_time}):</span> {late_mean:.1f} μV²
    """

    # 객관적 변화 추이 기록 (해석 제거)
    change_description = f"초반 대비 중반 {abs((mid_mean-early_mean)/early_mean*100):.1f}% {early_to_mid_kr}, "
    change_description += f"중반 대비 후반 {abs((late_mean-mid_mean)/mid_mean*100):.1f}% {mid_to_late_kr}"

    # 전체 추세
    overall_change = ((late_mean - early_mean) / early_mean * 100) if early_mean > 0 else 0
    if overall_change > 10:
        overall_trend = f"전체적으로 {abs(overall_change):.1f}% 증가"
    elif overall_change < -10:
        overall_trend = f"전체적으로 {abs(overall_change):.1f}% 감소"
    else:
        overall_trend = "전체적으로 안정적 유지"

    # 변화점 정보 (팩트만)
    change_points_desc = ""
    if change_points and len(change_points) > 0:
        change_details = []
        for cp, ct in zip(change_points, change_types):
            time_str = format_duration(cp)
            ct_kr = "증가" if ct == "increase" else "감소" if ct == "decrease" else "안정"
            change_details.append(f"{time_str} 시점에서 {ct_kr}")
        change_points_desc = f"<br><strong>변화점:</strong> " + ", ".join(change_details)

    # 통계 정보
    mean_power = np.mean(smoothed_data)
    max_power = np.max(smoothed_data)
    min_power = np.min(smoothed_data)
    std_power = np.std(smoothed_data)

    # HTML 포맷팅 (해석 제거, 팩트만)
    interpretation_html = f"""
        <div class="analysis-box">
            {phase_html}
            <div class="interpretation">
                <strong>변화 추이:</strong> {change_description}<br>
                <strong>전체 경향:</strong> {overall_trend}
                {change_points_desc}
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">평균</div>
                    <div class="stat-value">{mean_power:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">최대</div>
                    <div class="stat-value">{max_power:.1f}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">최소</div>
                    <div class="stat-value">{min_power:.1f}</div>
                </div>
            </div>
        </div>
    """

    return interpretation_html


def generate_interpretations(analysis_result):
    """모든 주파수 대역의 해석 생성"""
    interpretations = {}

    for band in config.FREQUENCY_BANDS.keys():
        interpretation = generate_interpretation(
            band_name=band,
            smoothed_data=analysis_result['smooth'][band],
            change_points=analysis_result['change_points'][band],
            change_types=analysis_result['change_types'][band]
        )
        interpretations[band] = interpretation

    return interpretations


def generate_hrv_interpretation(hrv_metrics):
    """HRV 지표 해석 HTML 생성"""
    time_domain = hrv_metrics['time_domain']
    freq_domain = hrv_metrics['frequency_domain']
    interp = hrv_metrics['interpretation']
    quality = hrv_metrics.get('quality', 'unknown')
    quality_message = hrv_metrics.get('quality_message', '품질 정보 없음')

    # 품질 경고 메시지 생성
    quality_warning = ""
    if quality != 'good':
        quality_warning = f"""
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
                <strong>⚠️ 데이터 품질 경고:</strong> {quality_message}<br>
                <span style="font-size: 13px; color: #856404;">
                HRV 측정값이 표시되지 않습니다. EEG 신호에서 심박 성분 추출이 원활하지 않았습니다.
                보다 정확한 HRV 분석을 위해서는 PPG 또는 ECG 센서를 사용하는 것을 권장합니다.
                </span>
            </div>
        """

    hrv_html = f"""
        <div class="hrv-section" style="background: #f8f9fa; padding: 30px; border-radius: 10px; margin-top: 40px;">
            <h2 style="font-size: 24px; font-weight: 700; margin-bottom: 25px; color: #212529; padding-bottom: 15px; border-bottom: 3px solid #667eea;">
                💓 심박변이도 (HRV) 분석
            </h2>

            {quality_warning}

            <!-- HRV 시각화 그래프 -->
            <div style="text-align: center; margin-bottom: 30px; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <img src="{{{{GRAPH_HRV}}}}" alt="HRV 시각화 그래프" style="max-width: 100%; height: auto; border-radius: 8px;">
            </div>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 25px; margin-bottom: 30px;">
                <!-- 시간 영역 지표 -->
                <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 15px; color: #667eea;">⏱️ 시간 영역 지표</h3>
                    <div style="line-height: 2;">
                        <div><strong>평균 심박수:</strong> {time_domain['mean_hr']} bpm</div>
                        <div><strong>SDNN:</strong> {time_domain['sdnn']} ms</div>
                        <div><strong>RMSSD:</strong> {time_domain['rmssd']} ms</div>
                        <div><strong>pNN50:</strong> {time_domain['pnn50']}%</div>
                    </div>
                    <div style="margin-top: 15px; padding: 10px; background: #e3f2fd; border-radius: 5px; font-size: 13px;">
                        <strong>✓ SDNN:</strong> 전체 심박변이도 (높을수록 양호)<br>
                        <strong>✓ RMSSD/pNN50:</strong> 부교감신경 활성
                    </div>
                </div>

                <!-- 주파수 영역 지표 -->
                <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 15px; color: #667eea;">📊 주파수 영역 지표</h3>
                    <div style="line-height: 2;">
                        <div><strong>VLF Power:</strong> {freq_domain['vlf']}</div>
                        <div><strong>LF Power:</strong> {freq_domain['lf']}</div>
                        <div><strong>HF Power:</strong> {freq_domain['hf']}</div>
                        <div><strong>Total Power:</strong> {freq_domain['total_power']}</div>
                        <div><strong style="color: #e74c3c;">LF/HF Ratio:</strong> {freq_domain['lf_hf_ratio']}</div>
                    </div>
                    <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border-radius: 5px; font-size: 13px;">
                        <strong>✓ HF:</strong> 부교감신경 (이완)<br>
                        <strong>✓ LF/HF Ratio:</strong> 교감/부교감 균형
                    </div>
                </div>
            </div>

            <!-- 해석 -->
            <div style="background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <h3 style="font-size: 18px; font-weight: 700; margin-bottom: 20px; color: #667eea;">📋 종합 해석</h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                    <div style="padding: 15px; background: #f1f8ff; border-left: 4px solid #2196f3; border-radius: 5px;">
                        <div style="font-weight: 700; color: #2196f3; margin-bottom: 8px;">스트레스 수준</div>
                        <div style="font-size: 20px; font-weight: 700;">{interp['stress_level']}</div>
                    </div>
                    <div style="padding: 15px; background: #f1f8ff; border-left: 4px solid #4caf50; border-radius: 5px;">
                        <div style="font-weight: 700; color: #4caf50; margin-bottom: 8px;">자율신경 균형</div>
                        <div style="font-size: 20px; font-weight: 700;">{interp['autonomic_balance']}</div>
                    </div>
                    <div style="padding: 15px; background: #f1f8ff; border-left: 4px solid #9c27b0; border-radius: 5px;">
                        <div style="font-weight: 700; color: #9c27b0; margin-bottom: 8px;">부교감신경 상태</div>
                        <div style="font-size: 16px; font-weight: 700;">{interp['parasympathetic_status']}</div>
                    </div>
                    <div style="padding: 15px; background: #f1f8ff; border-left: 4px solid #ff9800; border-radius: 5px;">
                        <div style="font-weight: 700; color: #ff9800; margin-bottom: 8px;">교감신경 상태</div>
                        <div style="font-size: 16px; font-weight: 700;">{interp['sympathetic_status']}</div>
                    </div>
                </div>

                <div style="margin-top: 20px; padding: 15px; background: #e8f5e9; border-radius: 5px; line-height: 1.8;">
                    <strong>💡 권장사항:</strong><br>
                    {get_hrv_recommendation(interp)}
                </div>
            </div>
        </div>
    """

    return hrv_html


def get_hrv_recommendation(interp):
    """HRV 해석에 따른 권장사항 생성"""
    recommendations = []

    # 스트레스 수준에 따른 권장사항
    if interp['stress_level'] == '높음':
        recommendations.append("• 스트레스 관리가 필요합니다. 규칙적인 휴식과 이완 훈련을 권장합니다.")
    elif interp['stress_level'] == '낮음':
        recommendations.append("• 우수한 스트레스 관리 상태를 유지하고 있습니다.")

    # 자율신경 균형에 따른 권장사항
    if interp['autonomic_balance'] == '교감신경 우세':
        recommendations.append("• 이완 활동(명상, 요가, 호흡법)을 통해 부교감신경을 활성화하는 것이 도움됩니다.")
    elif interp['autonomic_balance'] == '부교감신경 우세':
        recommendations.append("• 적절한 운동으로 균형을 맞추는 것이 좋습니다.")
    else:
        recommendations.append("• 자율신경 균형이 양호합니다. 현재 상태를 유지하세요.")

    # 부교감신경 상태에 따른 권장사항
    if '긴장' in interp['parasympathetic_status']:
        recommendations.append("• 복식 호흡, 바이오피드백 훈련 등으로 이완 능력을 향상시킬 수 있습니다.")

    if not recommendations:
        recommendations.append("• 전반적으로 양호한 자율신경 상태를 보이고 있습니다.")

    return "<br>".join(recommendations)


def generate_report(info, graph_paths, interpretations, analysis_result):
    """HTML 보고서 생성 (V3 템플릿 사용)"""
    from utils import get_output_paths

    paths = get_output_paths(info)
    # V3 템플릿 우선 사용
    template_path = os.path.join(config.TEMPLATES_DIR, 'report_template_v3.html')

    # 템플릿 로드 (V3 → V2 → V1 순서)
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        template_path = os.path.join(config.TEMPLATES_DIR, 'report_template_v2.html')
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            template_path = os.path.join(config.TEMPLATES_DIR, 'report_template.html')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
            else:
                template = create_default_template()

    # 그래프를 base64로 인코딩
    graph_data = {}
    for band, path in graph_paths.items():
        if os.path.exists(path):
            with open(path, 'rb') as f:
                graph_data[band] = base64.b64encode(f.read()).decode()

    # 변수 치환
    html = template.replace('{{NAME}}', info['name'])
    html = html.replace('{{GENDER}}', info['gender'])
    html = html.replace('{{AGE}}', str(info['age']))
    html = html.replace('{{DATE}}', datetime.now().strftime('%Y년 %m월 %d일'))
    html = html.replace('{{DURATION}}', f"{analysis_result['duration']/60:.1f}")

    # 주파수 대역 비율 그래프 치환
    if 'band_ratio' in graph_data:
        html = html.replace(
            '{{GRAPH_BAND_RATIO}}',
            f'data:image/png;base64,{graph_data["band_ratio"]}'
        )

    # 좌뇌/우뇌 균형 그래프 치환
    if 'brain_balance' in graph_data:
        html = html.replace(
            '{{GRAPH_BRAIN_BALANCE}}',
            f'data:image/png;base64,{graph_data["brain_balance"]}'
        )

    # 각 주파수 대역별 그래프와 해석 치환
    for band in config.FREQUENCY_BANDS.keys():
        band_upper = band.upper()
        if band in graph_data:
            html = html.replace(
                f'{{{{GRAPH_{band_upper}}}}}',
                f'data:image/png;base64,{graph_data[band]}'
            )
        if band in interpretations:
            html = html.replace(
                f'{{{{ANALYSIS_{band_upper}}}}}',
                interpretations[band]
            )

    # HRV 해석 추가 (먼저 삽입)
    if 'hrv_metrics' in analysis_result:
        hrv_html = generate_hrv_interpretation(analysis_result['hrv_metrics'])
        html = html.replace('{{HRV_SECTION}}', hrv_html)
    else:
        html = html.replace('{{HRV_SECTION}}', '')

    # HRV 시각화 그래프 치환 (HRV 섹션 삽입 후)
    if 'hrv_visualization' in graph_data:
        html = html.replace(
            '{{GRAPH_HRV}}',
            f'data:image/png;base64,{graph_data["hrv_visualization"]}'
        )

    # 저장
    os.makedirs(os.path.dirname(paths['report_html']), exist_ok=True)
    with open(paths['report_html'], 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML 보고서 저장: {paths['report_html']}")

    return paths['report_html']


def convert_to_pdf(html_path, info):
    """HTML을 PDF로 변환"""
    try:
        from weasyprint import HTML
        from utils import get_output_paths

        paths = get_output_paths(info)
        pdf_path = paths['report_pdf']

        HTML(html_path).write_pdf(pdf_path)
        print(f"PDF 보고서 저장: {pdf_path}")

        return pdf_path

    except ImportError:
        print("경고: weasyprint가 설치되지 않아 PDF 변환을 건너뜁니다.")
        return None
    except Exception as e:
        print(f"PDF 변환 실패: {e}")
        return None


def create_default_template():
    """기본 HTML 템플릿 생성 (fallback)"""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>뇌파 분석 보고서</title>
</head>
<body>
    <h1>{{NAME}} - 뇌파 분석 보고서</h1>
    <p>성별: {{GENDER}}, 나이: {{AGE}}세</p>
    <p>측정일: {{DATE}}, 측정시간: {{DURATION}}분</p>
</body>
</html>"""
