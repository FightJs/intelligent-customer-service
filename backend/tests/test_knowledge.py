"""F1 知识库单测：schema / mapping / ingest / hybrid_search / 降级。

不依赖真实 Qdrant 与外网密钥。
"""
from __future__ import annotations

import pytest

from knowledge.config import KnowledgeConfig
from knowledge.embedding import EmbeddingError, MockEmbedder
from knowledge.ingest import (
    business_id,
    chunk_vertical_text,
    equipment_row,
    ingest_rows,
    scheme_row,
    source_tag,
    vertical_row,
)
from knowledge.mapping import map_budget_level, map_room_size
from knowledge.models import (
    COLLECTION_EQUIPMENT,
    COLLECTION_SCHEMES,
    COLLECTION_VERTICAL,
)
from knowledge.rerank import IdentityReranker
from knowledge.schema import COLLECTION_SPECS, get_collection_spec
from knowledge.search import fuse_rrf, fuse_weighted, hybrid_search
from knowledge.store import (
    InMemoryVectorStore,
    RawHit,
    StoreUnavailable,
    build_filter,
)

CFG = KnowledgeConfig(embedding_provider='mock', rerank_provider='identity')


@pytest.fixture()
def store() -> InMemoryVectorStore:
    s = InMemoryVectorStore()
    s.ensure_collections()
    return s


@pytest.fixture()
def embedder() -> MockEmbedder:
    return MockEmbedder(dim=64)


# ── schema ───────────────────────────────────────────────────


def test_three_collections_defined():
    assert set(COLLECTION_SPECS) == {
        COLLECTION_EQUIPMENT,
        COLLECTION_SCHEMES,
        COLLECTION_VERTICAL,
    }
    for name, spec in COLLECTION_SPECS.items():
        assert spec.name == name
        field_names = spec.field_names()
        assert 'id' in field_names
        assert 'text' in field_names
        assert 'dense' in field_names
        assert 'sparse' in field_names
        assert 'source' in field_names
        assert 'updated_at' in field_names
        assert spec.dense_dim() == 1024


def test_equipment_schema_fields():
    spec = get_collection_spec(COLLECTION_EQUIPMENT)
    names = spec.field_names()
    for expected in (
        'name',
        'category',
        'brand',
        'price_band',
        'room_size',
        'industry',
        'specs',
    ):
        assert expected in names


def test_scheme_schema_fields():
    spec = get_collection_spec(COLLECTION_SCHEMES)
    names = spec.field_names()
    for expected in (
        'scheme_name',
        'budget_level',
        'live_type',
        'equipment_ids',
        'package_tiers',
        'layout_notes',
    ):
        assert expected in names


def test_vector_field_dims():
    dense = next(f for f in get_collection_spec(COLLECTION_EQUIPMENT).fields if f.name == 'dense')
    sparse = next(
        f for f in get_collection_spec(COLLECTION_EQUIPMENT).fields if f.name == 'sparse'
    )
    assert dense.dim == 1024
    assert sparse.dtype == 'SPARSE_FLOAT_VECTOR'
    assert get_collection_spec(COLLECTION_EQUIPMENT).output_fields()[0] != 'dense'


# ── mapping ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('area', 'size', 'expected'),
    [
        ('<10', None, 'small'),
        ('10-20', None, 'small'),
        ('20-30', None, 'medium'),
        ('30-50', None, 'medium'),
        ('50+', None, 'large'),
        ('50+', 90.0, 'xlarge'),
    ],
)
def test_map_room_size(area, size, expected):
    assert map_room_size(area, size) == expected


@pytest.mark.parametrize(
    ('total', 'equipment', 'expected'),
    [
        ('<1w', '<5k', 'low'),
        ('3-5w', '1-2w', 'mid'),
        ('5-10w', '2-5w', 'high'),
        ('20w+', '5w+', 'ultra'),
        ('5-10w', '<5k', 'mid'),  # 取较高档
        (None, '2-5w', 'high'),
        ('1-3w', None, 'low'),
    ],
)
def test_map_budget_level(total, equipment, expected):
    assert map_budget_level(total, equipment) == expected


def test_map_rejects_unknown():
    with pytest.raises(ValueError):
        map_room_size('100-200')
    with pytest.raises(ValueError):
        map_budget_level('10w')


# ── 业务主键 / source ────────────────────────────────────────


def test_business_id_stable_and_positive():
    a = business_id('爱图仕', '300D', 'file.pdf#abc')
    b = business_id('爱图仕', '300D', 'file.pdf#abc')
    c = business_id('爱图仕', '300D', 'file.pdf#def')
    assert a == b
    assert a != c
    assert a > 0


def test_source_tag_contains_hash8():
    tag = source_tag('handbook.pdf', b'hello')
    assert tag.startswith('handbook.pdf#')
    assert len(tag.split('#')[1]) == 8


# ── 切块 ─────────────────────────────────────────────────────


def test_chunk_vertical_by_headings_and_context():
    text = """一、布光要点
女装直播间主灯应放在主播 45 度侧上方，色温统一 5600K，避免面料偏色。
辅灯补阴影，背景灯拉开层次。小空间注意控制阴影面积。

二、背景
简洁高级的莫兰迪色墙更适合女装。高饱和撞色会抢商品视觉。
1.8m 背景布适合折叠收纳。
"""
    chunks = chunk_vertical_text(text, industry='women', scene='布光')
    assert len(chunks) >= 2
    for c in chunks:
        assert c.startswith('[适用场景 / 布光 / 行业 / women]')
        assert '布光' in c or '背景' in c


def test_chunk_respects_max_length():
    long_para = '女装直播间布光需要反复调试。' * 80  # 远超 500 汉字
    chunks = chunk_vertical_text(long_para, industry='women', min_chars=200, max_chars=500)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) < 800  # header + body


# ── ingest ───────────────────────────────────────────────────


def _sample_equipment(source: str = 'seed#00000001') -> dict:
    return equipment_row(
        name='爱图仕 300D',
        category='灯光',
        brand='爱图仕',
        price_band='high',
        room_size='medium',
        industry='women',
        specs={'power_w': 350, 'color_temp_k': 5600},
        text='爱图仕 300D 常亮灯，女装三点布光主灯，功率 350W，色温 5600K。',
        source=source,
    )


def test_ingest_rows_embeds_and_upserts(store, embedder):
    n = ingest_rows(
        COLLECTION_EQUIPMENT,
        [_sample_equipment()],
        store=store,
        embedder=embedder,
        config=CFG,
    )
    assert n == 1
    dumped = store.dump(COLLECTION_EQUIPMENT)
    assert len(dumped) == 1
    assert len(dumped[0]['dense']) == 64


def test_ingest_rows_rollback_on_embedding_failure(store):
    class BoomEmbedder:
        dim = 64

        def embed(self, texts):
            raise EmbeddingError('boom')

    with pytest.raises(EmbeddingError):
        ingest_rows(
            COLLECTION_EQUIPMENT,
            [_sample_equipment(), _sample_equipment('seed#00000002')],
            store=store,
            embedder=BoomEmbedder(),
            config=CFG,
        )
    assert store.dump(COLLECTION_EQUIPMENT) == []


def test_ingest_rows_idempotent_upsert(store, embedder):
    row = _sample_equipment()
    ingest_rows(COLLECTION_EQUIPMENT, [row], store=store, embedder=embedder, config=CFG)
    row2 = dict(row)
    row2['text'] = '爱图仕 300D 更新后的描述：女装主灯，适合 20㎡ 中型间。'
    ingest_rows(COLLECTION_EQUIPMENT, [row2], store=store, embedder=embedder, config=CFG)
    dumped = store.dump(COLLECTION_EQUIPMENT)
    assert len(dumped) == 1
    assert '更新后的描述' in dumped[0]['text']


# ── 过滤条件 ─────────────────────────────────────────────────


def test_build_filter_expands_industry_all():
    flt = build_filter(industry='women', room_size='medium', budget_level='mid')
    assert flt == {
        'industry': ['all', 'women'],
        'room_size': ['medium'],
        'budget_level': ['mid'],
    }


def test_build_filter_empty():
    assert build_filter() is None


# ── hybrid_search ────────────────────────────────────────────


def _seed_store(store, embedder) -> None:
    eq = [
        equipment_row(
            name='爱图仕 300D',
            category='灯光',
            brand='爱图仕',
            price_band='high',
            room_size='medium',
            industry='women',
            specs={'power_w': 350},
            text='爱图仕 300D 常亮灯 三点布光 女装直播间 主灯 350W 色温 5600K',
            source='seed#eq1',
        ),
        equipment_row(
            name='神牛 SL60W',
            category='灯光',
            brand='神牛',
            price_band='mid',
            room_size='small',
            industry='all',
            specs={'power_w': 60},
            text='神牛 SL60W 入门补光灯 通用 三点布光 小空间',
            source='seed#eq2',
        ),
        equipment_row(
            name='索尼 A7M4',
            category='相机',
            brand='索尼',
            price_band='ultra',
            room_size='large',
            industry='all',
            specs={'sensor': 'full-frame'},
            text='索尼 A7M4 全画幅相机 直播推流 高画质',
            source='seed#eq3',
        ),
    ]
    schemes = [
        scheme_row(
            scheme_name='女装 20㎡ 高级感平价套装',
            industry='women',
            budget_level='mid',
            room_size='medium',
            live_type='brand',
            equipment_ids=[eq[0]['id'], eq[1]['id']],
            package_tiers=[{'tier': 'standard', 'total_price_range': '1.5w-3w', 'items': []}],
            layout_notes='三点布光 + 背景层次',
            text='女装 20㎡ 中型直播间 高级感 平价 品牌自播 三点布光 爱图仕 搭建方案',
            source='seed#sc1',
        ),
        scheme_row(
            scheme_name='食品仓播基础方案',
            industry='food',
            budget_level='low',
            room_size='large',
            live_type='factory',
            equipment_ids=[],
            package_tiers=[],
            layout_notes='动线优先',
            text='食品 仓播 大空间 基础搭建 动线',
            source='seed#sc2',
        ),
    ]
    vertical = [
        vertical_row(
            industry='women',
            scene='布光',
            content='女装三点布光：主灯 45 度，辅灯补阴影，背景灯拉层次。',
            text='女装 三点布光 主灯 辅灯 背景灯 爱图仕',
            source='seed#vk1',
            chunk_index=0,
        ),
    ]
    ingest_rows(COLLECTION_EQUIPMENT, eq, store=store, embedder=embedder, config=CFG)
    ingest_rows(COLLECTION_SCHEMES, schemes, store=store, embedder=embedder, config=CFG)
    ingest_rows(COLLECTION_VERTICAL, vertical, store=store, embedder=embedder, config=CFG)


def test_chinese_query_retrieves_equipment_and_scheme(store, embedder):
    _seed_store(store, embedder)
    query = '女装 20㎡ 三点布光 爱图仕'

    eq_res = hybrid_search(
        COLLECTION_EQUIPMENT,
        query,
        industry='women',
        room_size='medium',
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert eq_res.degraded is False
    assert eq_res.hits
    names = [h.payload.get('name', '') for h in eq_res.hits]
    assert any('爱图仕' in n for n in names)

    sc_res = hybrid_search(
        COLLECTION_SCHEMES,
        query,
        industry='women',
        room_size='medium',
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert sc_res.hits
    assert any('女装' in h.payload.get('scheme_name', '') for h in sc_res.hits)


def test_filter_excludes_other_industry(store, embedder):
    _seed_store(store, embedder)
    res = hybrid_search(
        COLLECTION_SCHEMES,
        '搭建方案',
        industry='women',
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    industries = {h.payload.get('industry') for h in res.hits}
    assert industries <= {'women', 'all'}
    assert 'food' not in industries


def test_budget_filter(store, embedder):
    _seed_store(store, embedder)
    res = hybrid_search(
        COLLECTION_SCHEMES,
        '方案',
        budget_level='mid',
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert all(h.payload.get('budget_level') == 'mid' for h in res.hits)


def test_embedding_failure_falls_back_to_bm25(store):
    _seed_store(store, MockEmbedder(dim=64))

    class FailEmbedder:
        dim = 64

        def embed(self, texts):
            raise EmbeddingError('offline')

    res = hybrid_search(
        COLLECTION_EQUIPMENT,
        '爱图仕 三点布光',
        industry='women',
        store=store,
        embedder=FailEmbedder(),
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert res.degraded is True
    assert res.reason == 'embedding_failed_bm25_only'
    assert res.hits  # BM25-only 仍可召回


def test_store_unavailable_returns_degraded_empty(embedder):
    class DownStore:
        def ensure_collections(self):
            return None

        def upsert(self, collection, rows):
            raise StoreUnavailable('down')

        def search_dense(self, collection, vector, flt, limit):
            raise StoreUnavailable('connect timeout')

        def search_sparse(self, collection, query, flt, limit):
            raise StoreUnavailable('connect timeout')

        def close(self):
            return None

    res = hybrid_search(
        COLLECTION_EQUIPMENT,
        '任意',
        store=DownStore(),
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert res.degraded is True
    assert res.hits == []
    assert 'store_unavailable' in (res.reason or '')


def test_fusion_weighted_prefers_both_channels():
    dense = [RawHit(id=1, score=0.9, payload={'text': 'a'}), RawHit(id=2, score=0.1, payload={'text': 'b'})]
    sparse = [RawHit(id=2, score=10.0, payload={'text': 'b'}), RawHit(id=3, score=1.0, payload={'text': 'c'})]
    fused = fuse_weighted(
        dense, sparse, collection='equipment_specs', dense_weight=0.6, sparse_weight=0.4
    )
    ids = [h.id for h in fused]
    assert set(ids) == {1, 2, 3}
    assert fused[0].id in {1, 2}
    assert all(h.collection == 'equipment_specs' for h in fused)


def test_fusion_rrf():
    dense = [RawHit(id=1, score=0.9), RawHit(id=2, score=0.5)]
    sparse = [RawHit(id=2, score=9.0), RawHit(id=3, score=1.0)]
    fused = fuse_rrf(dense, sparse, collection='vertical_knowledge')
    assert {h.id for h in fused} == {1, 2, 3}
    assert fused[0].id == 2  # 双通道都靠前


def test_limit_respected(store, embedder):
    rows = []
    for i in range(12):
        rows.append(
            equipment_row(
                name=f'灯{i}',
                category='灯光',
                brand='测试',
                price_band='mid',
                room_size='medium',
                industry='women',
                specs={},
                text=f'女装 灯具 型号{i} 三点布光',
                source=f'seed#{i}',
            )
        )
    ingest_rows(COLLECTION_EQUIPMENT, rows, store=store, embedder=embedder, config=CFG)
    res = hybrid_search(
        COLLECTION_EQUIPMENT,
        '女装 灯具',
        limit=3,
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert len(res.hits) == 3


# ── PDF 路径（mock 文本抽取） ────────────────────────────────


def test_ingest_pdf_path(store, embedder, tmp_path, monkeypatch):
    from knowledge import ingest as ingest_mod

    pdf = tmp_path / '女装布光手册.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake')

    monkeypatch.setattr(
        ingest_mod,
        'extract_pdf_text',
        lambda p: (
            '一、布光\n女装三点布光要点：主灯 45 度，色温 5600K，避免偏色。\n'
            '二、背景\n莫兰迪色墙，避免高饱和撞色。' + '补充说明。' * 40
        ),
    )

    result = ingest_mod.ingest_pdf(
        pdf,
        industry='women',
        scene='布光',
        store=store,
        embedder=embedder,
        config=CFG,
    )
    assert result['chunks'] >= 1
    assert result['source'].startswith('女装布光手册.pdf#')

    res = hybrid_search(
        COLLECTION_VERTICAL,
        '女装 三点布光 色温',
        industry='women',
        store=store,
        embedder=embedder,
        reranker=IdentityReranker(),
        config=CFG,
    )
    assert res.hits
    assert any('布光' in str(h.payload.get('content', '')) for h in res.hits)


# ── OpenRouter embedder ──────────────────────────────────────


def test_openrouter_embedder_parses_openai_response(monkeypatch):
    from knowledge.embedding import OpenRouterEmbedder

    captured = {}

    class _Resp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                'data': [
                    {'index': 1, 'embedding': [0.0] * 1024},
                    {'index': 0, 'embedding': [1.0] * 1024},
                ]
            }

    def _post(url, *, json=None, headers=None, timeout=None):
        captured['url'] = url
        captured['json'] = json
        captured['headers'] = headers
        return _Resp()

    monkeypatch.setattr('knowledge.embedding.httpx.post', _post)
    emb = OpenRouterEmbedder(
        api_key='sk-or-test',
        model='openai/text-embedding-3-small',
        dim=1024,
        base_url='https://openrouter.ai/api/v1',
    )
    vecs = emb.embed(['a', 'b'])
    assert len(vecs) == 2
    assert len(vecs[0]) == 1024
    # 按 index 重排：0 在前
    assert vecs[0][0] == 1.0
    assert captured['url'].endswith('/embeddings')
    assert captured['json']['dimensions'] == 1024
    assert captured['headers']['Authorization'] == 'Bearer sk-or-test'


def test_openrouter_embedder_requires_key():
    from knowledge.embedding import EmbeddingError, OpenRouterEmbedder

    with pytest.raises(EmbeddingError):
        OpenRouterEmbedder(api_key='')


def test_get_embedder_openrouter(monkeypatch):
    from knowledge.config import KnowledgeConfig
    from knowledge.embedding import OpenRouterEmbedder, get_embedder

    cfg = KnowledgeConfig(
        embedding_provider='openrouter',
        openrouter_api_key='sk-or-x',
        embedding_model='openai/text-embedding-3-small',
        embedding_dim=1024,
    )
    emb = get_embedder(cfg)
    assert isinstance(emb, OpenRouterEmbedder)
    assert emb.dim == 1024
