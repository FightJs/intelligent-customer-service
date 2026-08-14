"""delivery 生成器图片嵌入测试。"""
import io
import zipfile

import store.uploads as uploads
from delivery.excel import generate_excel
from delivery.markdown import generate_markdown
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
    assert '![场地照片](data:image/png;base64,' in md


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
