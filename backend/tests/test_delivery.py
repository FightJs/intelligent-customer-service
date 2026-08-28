"""delivery 生成器图片嵌入测试。"""
import io
import zipfile

import store.uploads as uploads
from delivery.excel import generate_excel
from delivery.markdown import generate_markdown
from delivery.render_data import build_render_data
from delivery.word import generate_word
from survey.state import create_initial_state
from tests.test_uploads import make_png_data_uri, uploads_root  # noqa: F401（fixture）


def _state_with_venue_image(uploads_root):
    """构造 venue_photo 带一张真实落盘图片的 state。"""
    saved = uploads.save_upload('sess1', make_png_data_uri())
    state = create_initial_state()
    state.sections['venue'].fields['venue_photo'].value = [saved.id]
    return state, saved


def test_markdown_embeds_images_as_data_uri(uploads_root):
    state, _ = _state_with_venue_image(uploads_root)
    md = generate_markdown(state)
    assert '![场地多角度照片](data:image/png;base64,' in md


def test_word_embeds_images(uploads_root):
    state, _ = _state_with_venue_image(uploads_root)
    content = generate_word(state)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        assert any(name.startswith('word/media/') for name in zf.namelist())


def test_excel_embeds_images_sheet(uploads_root):
    state, _ = _state_with_venue_image(uploads_root)
    content = generate_excel(state)
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        assert any(name.startswith('xl/media/') for name in zf.namelist())


def test_missing_image_files_silently_skipped(uploads_root):
    """ImageValue 里的 id 文件不存在时不崩溃、不内嵌。"""
    state = create_initial_state()
    state.sections['venue'].fields['venue_photo'].value = ['sess1/gone.jpg']
    md = generate_markdown(state)
    assert 'data:image' not in md
    # word/excel 也不应崩溃
    generate_word(state)
    generate_excel(state)


def test_filled_only_render_data_omits_empty_fields_and_sections():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    state.sections['venue'].fields['size'].value = {'宽': '4.5', '深': '', '高': ''}
    state.sections['status'].status = 'skipped'
    state.sections['equipment'].fields['inventory'].value = [
        {'type': '', 'model': '', 'qty': ''},
    ]

    data = build_render_data(state, filled_only=True)

    assert data['sections'] == [
        {
            'title': '一、基础信息采集',
            'fields': [
                {
                    'label': '品牌/公司名称',
                    'value': '云裳',
                    'filled': True,
                    'images': [],
                },
            ],
            'filled_count': 1,
            'total_count': 1,
            'skipped': False,
        },
        {
            'title': '四、场地条件信息',
            'fields': [
                {
                    'label': '具体尺寸（宽×深×高）',
                    'value': '宽4.5m',
                    'filled': True,
                    'images': [],
                },
            ],
            'filled_count': 0,
            'total_count': 0,
            'skipped': False,
        },
    ]


def test_filled_only_word_preview_excludes_empty_section_titles():
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'

    content = generate_word(state, filled_only=True)

    from docx import Document

    doc = Document(io.BytesIO(content))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]
    assert '一、基础信息采集' in paragraphs
    assert '二、行业与品类信息' not in paragraphs
    assert '四、场地条件信息' not in paragraphs


def test_customer_identity_uses_chinese_labels_in_delivery_preview():
    state = create_initial_state()
    state.sections['customer'].fields['identity'].value = ['owner', 'host']

    data = build_render_data(state, filled_only=True)
    identity = next(
        field
        for field in data['sections'][0]['fields']
        if field['label'] == '客户身份'
    )

    assert identity['value'] == '主理人（老板）、主播'


def test_filled_only_preview_keeps_full_required_progress_denominator():
    state = create_initial_state()
    customer = state.sections['customer'].fields
    customer['brand'].value = '云裳'
    customer['contact'].value = '小云'
    customer['phone'].value = '13800000000'
    customer['source'].value = 'douyin'
    industry = state.sections['industry'].fields
    industry['price_band'].value = '100-500'
    industry['positioning'].value = 'mid-high'
    industry['target_age'].value = '25-35'
    industry['target_gender'].value = 'balanced'
    industry['live_type'].value = 'brand'

    data = build_render_data(state, filled_only=True)

    assert data['progress'] == {'filled': 9, 'total': 24, 'pct': 38}
