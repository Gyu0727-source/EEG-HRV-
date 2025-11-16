"""
EEG 실시간 분석 프로젝트 - 보고서 생성 모듈

주요 기능:
1. 변화 패턴 자동 해석
2. HTML 보고서 생성
3. PDF 변환
"""

import os
import base64
import numpy as np
from datetime import datetime
import config


# 해석 템플릿 정의
INTERPRETATION_TEMPLATES = {
    'delta': {
        'increase_increase_increase': """
            측정 시간 동안 지속적으로 델타파가 증가했습니다.
            깊은 이완 상태로 진입하고 있으며, 수면 준비 상태에 가까워지고 있습니다.
        """,
        'decrease_decrease_decrease': """
            측정 시간 동안 델타파가 계속 감소했습니다.
            점점 각성 상태로 전환되고 있으며, 측정 환경에 적응하는 과정입니다.
        """,
        'increase_stable': """
            초반에 델타파가 증가한 후 안정화되었습니다.
            편안한 이완 상태를 유지하고 있습니다.
        """,
        'decrease_stable': """
            초반에 델타파가 감소한 후 안정화되었습니다.
            적절한 각성 수준을 유지하고 있습니다.
        """,
        'default': """
            델타파의 자연스러운 변화가 관찰되었습니다.
            이완과 각성 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'theta': {
        'increase_increase_increase': """
            세타파가 지속적으로 증가했습니다.
            명상적 상태가 깊어지고 있으며, 창의적 사고가 활성화되고 있습니다.
        """,
        'decrease_decrease_decrease': """
            세타파가 계속 감소했습니다.
            주의 집중 상태로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 세타파가 증가한 후 안정화되었습니다.
            명상적 집중 상태를 잘 유지하고 있습니다.
        """,
        'decrease_stable': """
            초반에 세타파가 감소한 후 안정화되었습니다.
            안정적인 각성 상태를 유지하고 있습니다.
        """,
        'default': """
            세타파의 균형잡힌 변화가 관찰되었습니다.
            이완과 집중 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'alpha': {
        'increase_increase_increase': """
            알파파가 지속적으로 증가했습니다.
            편안하고 이완된 각성 상태가 깊어지고 있으며, 스트레스가 감소하고 있습니다.
        """,
        'decrease_decrease_decrease': """
            알파파가 계속 감소했습니다.
            주의 집중이 필요한 활동으로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 알파파가 증가한 후 안정화되었습니다.
            이상적인 이완 상태를 잘 유지하고 있습니다.
        """,
        'stable_increase': """
            후반부에 알파파가 증가했습니다.
            측정에 적응하면서 점점 편안해지고 있습니다.
        """,
        'decrease_stable': """
            초반에 알파파가 감소한 후 안정화되었습니다.
            적절한 각성 수준을 유지하고 있습니다.
        """,
        'default': """
            알파파의 자연스러운 변화가 관찰되었습니다.
            이완된 각성 상태를 적절히 유지하고 있습니다.
        """
    },
    'beta': {
        'increase_increase_increase': """
            베타파가 지속적으로 증가했습니다.
            인지 활동과 집중력이 높아지고 있습니다.
        """,
        'decrease_decrease_decrease': """
            베타파가 계속 감소했습니다.
            긴장이 풀리고 이완 상태로 전환되고 있습니다.
        """,
        'increase_stable': """
            초반에 베타파가 증가한 후 안정화되었습니다.
            적절한 집중 상태를 유지하고 있습니다.
        """,
        'decrease_stable': """
            초반에 베타파가 감소한 후 안정화되었습니다.
            편안한 상태를 유지하고 있습니다.
        """,
        'default': """
            베타파의 균형잡힌 변화가 관찰되었습니다.
            집중과 이완 사이의 적절한 조절이 이루어지고 있습니다.
        """
    },
    'gamma': {
        'increase_increase_increase': """
            감마파가 지속적으로 증가했습니다.
            고도의 인지 처리와 정보 통합이 활발히 일어나고 있습니다.
        """,
        'decrease_decrease_decrease': """
            감마파가 계속 감소했습니다.
            인지 부하가 줄어들고 있습니다.
        """,
        'increase_stable': """
            초반에 감마파가 증가한 후 안정화되었습니다.
            활발한 인지 활동을 유지하고 있습니다.
        """,
        'decrease_stable': """
            초반에 감마파가 감소한 후 안정화되었습니다.
            편안한 인지 상태를 유지하고 있습니다.
        """,
        'default': """
            감마파의 자연스러운 변화가 관찰되었습니다.
            균형잡힌 인지 활동이 이루어지고 있습니다.
        """
    }
}


def generate_pattern_key(change_types):
    """
    변화 타입 리스트를 패턴 키로 변환

    예: ['increase', 'increase', 'stable'] → 'increase_increase_stable'
    """
    if not change_types:
        return 'default'

    return '_'.join(change_types)


def generate_interpretation(band_name, smoothed_data, change_points, change_types):
    """
    변화 패턴을 분석하여 자동 해석 생성

    Parameters:
    -----------
    band_name : str
        주파수 대역 이름
    smoothed_data : ndarray
        스무딩된 데이터
    change_points : list
        변화점 인덱스
    change_types : list
        변화 방향

    Returns:
    --------
    interpretation_html : str
        HTML 형식의 해석 텍스트
    """
    # 패턴 키 생성
    pattern_key = generate_pattern_key(change_types)

    # 템플릿 선택
    templates = INTERPRETATION_TEMPLATES.get(band_name, {})
    interpretation = templates.get(pattern_key, templates.get('default', '변화 패턴이 관찰되었습니다.'))

    # 통계 정보 추가
    mean_power = np.mean(smoothed_data)
    std_power = np.std(smoothed_data)
    cv = (std_power / mean_power * 100) if mean_power > 0 else 0

    stats_html = f"""
        <div class="stats">
            <strong>통계:</strong> 평균 {mean_power:.2f} μV², 변동계수 {cv:.1f}%
        </div>
    """

    # HTML 포맷팅
    interpretation_html = f"""
        <div class="interpretation">
            <p>{interpretation.strip()}</p>
            {stats_html}
        </div>
    """

    return interpretation_html


def generate_interpretations(analysis_result):
    """
    모든 주파수 대역의 해석 생성

    Returns:
    --------
    interpretations : dict
        {'delta': html, 'theta': html, ...}
    """
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


def generate_report(info, graph_paths, interpretations, analysis_result):
    """
    HTML 보고서 생성

    Parameters:
    -----------
    info : dict
        개인 정보
    graph_paths : dict
        그래프 파일 경로들
    interpretations : dict
        각 대역별 해석 텍스트
    analysis_result : dict
        분석 결과

    Returns:
    --------
    output_path : str
        생성된 HTML 파일 경로
    """
    from utils import get_output_paths

    paths = get_output_paths(info)
    template_path = os.path.join(config.TEMPLATES_DIR, 'report_template.html')

    # 템플릿 로드
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    else:
        # 기본 템플릿 사용
        template = create_default_template()

    # 그래프를 base64로 인코딩
    graph_data = {}
    for band, path in graph_paths.items():
        with open(path, 'rb') as f:
            graph_data[band] = base64.b64encode(f.read()).decode()

    # 변수 치환
    html = template.replace('{{NAME}}', info['name'])
    html = html.replace('{{GENDER}}', info['gender'])
    html = html.replace('{{AGE}}', str(info['age']))
    html = html.replace('{{DATE}}', datetime.now().strftime('%Y년 %m월 %d일'))
    html = html.replace('{{DURATION}}', f"{analysis_result['duration']/60:.1f}")

    # 각 주파수 대역별 그래프와 해석 치환
    for band in config.FREQUENCY_BANDS.keys():
        band_upper = band.upper()
        html = html.replace(
            f'{{{{GRAPH_{band_upper}}}}}',
            f'data:image/png;base64,{graph_data[band]}'
        )
        html = html.replace(
            f'{{{{ANALYSIS_{band_upper}}}}}',
            interpretations[band]
        )

    # 저장
    os.makedirs(os.path.dirname(paths['report_html']), exist_ok=True)
    with open(paths['report_html'], 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML 보고서 저장: {paths['report_html']}")

    return paths['report_html']


def convert_to_pdf(html_path, info):
    """
    HTML을 PDF로 변환

    Parameters:
    -----------
    html_path : str
        HTML 파일 경로
    info : dict
        파일 정보

    Returns:
    --------
    pdf_path : str
        생성된 PDF 파일 경로
    """
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
    """기본 HTML 템플릿 생성"""
    return """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>뇌파 분석 보고서 - {{NAME}}</title>
    <style>
        body { font-family: 'Malgun Gothic', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .info { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .band-section { margin: 40px 0; border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .band-section h2 { color: #16a085; }
        img { width: 100%; max-width: 1000px; height: auto; margin: 20px 0; }
        .interpretation { background: #f9f9f9; padding: 15px; border-left: 4px solid #3498db; margin: 10px 0; }
        .stats { color: #7f8c8d; font-size: 0.9em; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>뇌파 분석 보고서</h1>

    <div class="info">
        <p><strong>이름:</strong> {{NAME}}</p>
        <p><strong>성별:</strong> {{GENDER}}</p>
        <p><strong>나이:</strong> {{AGE}}세</p>
        <p><strong>측정 날짜:</strong> {{DATE}}</p>
        <p><strong>측정 시간:</strong> {{DURATION}}분</p>
    </div>

    <div class="band-section">
        <h2>델타파 (Delta, 0.5-4Hz) - 깊은 이완 및 수면</h2>
        <img src="{{GRAPH_DELTA}}" alt="델타파 그래프">
        {{ANALYSIS_DELTA}}
    </div>

    <div class="band-section">
        <h2>세타파 (Theta, 4-8Hz) - 명상 및 창의적 사고</h2>
        <img src="{{GRAPH_THETA}}" alt="세타파 그래프">
        {{ANALYSIS_THETA}}
    </div>

    <div class="band-section">
        <h2>알파파 (Alpha, 8-13Hz) - 편안한 각성 상태</h2>
        <img src="{{GRAPH_ALPHA}}" alt="알파파 그래프">
        {{ANALYSIS_ALPHA}}
    </div>

    <div class="band-section">
        <h2>베타파 (Beta, 13-30Hz) - 집중 및 활동 상태</h2>
        <img src="{{GRAPH_BETA}}" alt="베타파 그래프">
        {{ANALYSIS_BETA}}
    </div>

    <div class="band-section">
        <h2>감마파 (Gamma, 30-50Hz) - 고도의 인지 활동</h2>
        <img src="{{GRAPH_GAMMA}}" alt="감마파 그래프">
        {{ANALYSIS_GAMMA}}
    </div>

    <div class="info" style="margin-top: 40px; background: #e8f8f5;">
        <p style="font-size: 0.9em; color: #555;">
            본 보고서는 EEG 실시간 분석 시스템에 의해 자동 생성되었습니다.
        </p>
    </div>
</body>
</html>"""
