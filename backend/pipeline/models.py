"""F2–F5 管线契约模型。"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from knowledge.models import CollectionName, KnowledgeHit


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────
# F2 plan_document
# ──────────────────────────────────────────────────────────────

class PlanDocumentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['plan_document'] = 'plan_document'
    pipeline_run_id: str
    session_id: str
    form_state: dict[str, Any]
    delivery_id: int | None = None
    allow_incomplete: bool = False
    force: bool = False


class ExistingEquipment(BaseModel):
    model_config = ConfigDict(extra='forbid')

    type: str = ''
    model: str = ''
    qty: str | int = ''


class RequirementBrief(BaseModel):
    """form_state 规范化摘要（检索键 + 方案上下文）。"""

    model_config = ConfigDict(extra='forbid')

    brand: str = ''
    industry: str = 'other'
    subcategory: str = ''
    price_band: str = ''
    positioning: str = ''
    live_type: str = ''
    room_size: str = 'medium'
    area_band: str = ''
    budget_total: str = ''
    budget_equip: str = ''
    budget_decor: str = ''
    budget_flex: str = ''
    goal_core: str = ''
    goal_focus: list[str] = Field(default_factory=list)
    product_main: str = ''
    product_keywords: list[str] = Field(default_factory=list)
    host_count: str = ''
    host_movement: str = ''
    existing_equipment: list[ExistingEquipment] = Field(default_factory=list)
    window: str = ''
    window_pos: str = ''
    renovation: str = ''
    deadline: str = ''
    need_3d: str = ''
    other_notes: str = ''
    completeness: float = 0.0
    missing_core_fields: list[str] = Field(default_factory=list)


class RetrievalIntent(BaseModel):
    model_config = ConfigDict(extra='forbid')

    collection: CollectionName
    query: str
    filters: dict[str, Any] = Field(default_factory=dict)


class KnowledgeRef(BaseModel):
    model_config = ConfigDict(extra='forbid')

    collection: str
    id: int


class LayoutZone(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    notes: str = ''


class LayoutPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')

    zones: list[LayoutZone] = Field(default_factory=list)
    lighting_plan: str = ''
    camera_plan: str = ''
    background_plan: str = ''


class EquipmentItem(BaseModel):
    # 允许字段名 model（设备型号），避开 pydantic 保护命名空间
    model_config = ConfigDict(extra='forbid', protected_namespaces=())

    knowledge_id: int | None = None
    category: str
    name: str
    model: str = ''
    brand: str = ''
    qty: int = 1
    unit_price_band: str = 'mid'
    reason: str = ''
    is_custom: bool = False
    already_owned: bool = False
    must_buy: bool = False
    specs: dict[str, Any] = Field(default_factory=dict)
    purchase_price: str = ''
    rent_monthly: str = ''


class PackageItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str
    qty: int = 1
    model: str = ''
    brand: str = ''


class PackageTier(BaseModel):
    model_config = ConfigDict(extra='forbid')

    tier: str
    total_range: str
    items: list[PackageItem] = Field(default_factory=list)
    mode: Literal['rent', 'buy', 'mixed'] = 'mixed'
    monthly_rent_range: str = ''
    suitable: str = ''


class RentalChannel(BaseModel):
    """设备租赁/采购渠道（平台级，不编造具体小店名）。"""

    model_config = ConfigDict(extra='forbid')

    name: str
    kind: Literal['platform', 'local', 'brand', 'ecom'] = 'platform'
    note: str = ''
    categories: list[str] = Field(default_factory=list)


class SceneCard(BaseModel):
    """F3 生图唯一场景真相源，F3/F4 禁止重新发挥。"""

    model_config = ConfigDict(extra='forbid')

    room_size_band: str = 'medium'
    style_keywords: list[str] = Field(default_factory=list)
    color_palette: list[str] = Field(default_factory=list)
    color_temp: str = '4000K'
    furniture: list[str] = Field(default_factory=list)
    lighting_fixtures: list[str] = Field(default_factory=list)
    product_category: str = ''
    camera_angles: list[str] = Field(default_factory=lambda: ['front', 'left', 'rear'])
    forbidden: list[str] = Field(default_factory=list)


class PlanDraft(BaseModel):
    """中间真相源：F3/F4/F5 的唯一方案。"""

    model_config = ConfigDict(extra='forbid')

    meta: dict[str, Any] = Field(default_factory=dict)
    summary: str = ''
    layout: LayoutPlan = Field(default_factory=LayoutPlan)
    equipment_list: list[EquipmentItem] = Field(default_factory=list)
    package_tiers: list[PackageTier] = Field(default_factory=list)
    setup_steps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    scene_card: SceneCard = Field(default_factory=SceneCard)
    rental_channels: list[RentalChannel] = Field(default_factory=list)
    vertical_notes: list[str] = Field(default_factory=list)
    must_buy_list: list[str] = Field(default_factory=list)


class PlanDocumentOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['plan_document'] = 'plan_document'
    status: Literal['succeeded', 'degraded', 'failed']
    plan_json_path: str = ''
    pdf_path: str | None = None
    requirement_brief: dict[str, Any] = Field(default_factory=dict)
    knowledge_hits: list[dict[str, Any]] = Field(default_factory=list)
    scene_card: dict[str, Any] = Field(default_factory=dict)
    cost_cny: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    reused: bool = False


LLMJsonFn = Callable[[str, str], Awaitable[Any]]


# ──────────────────────────────────────────────────────────────
# F3 preview_images
# ──────────────────────────────────────────────────────────────

class PreviewImagesInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['preview_images'] = 'preview_images'
    pipeline_run_id: str
    plan_json_path: str
    image_count: int = 3
    quality: Literal['draft', 'standard', 'high'] = 'standard'
    allow_partial: bool = True
    force: bool = False


class PreviewImageItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    angle: str
    path: str
    width: int = 0
    height: int = 0
    sha256: str = ''
    model: str = ''
    cost_cny: float = 0.0
    seed: int | None = None


class PreviewImagesOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['preview_images'] = 'preview_images'
    status: Literal['succeeded', 'partial', 'failed']
    images: list[PreviewImageItem] = Field(default_factory=list)
    seed_used: int | None = None
    model: str = ''
    total_cost_cny: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


# ──────────────────────────────────────────────────────────────
# F4 preview_video
# ──────────────────────────────────────────────────────────────

class PreviewVideoInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['preview_video'] = 'preview_video'
    pipeline_run_id: str
    plan_json_path: str
    images: list[dict[str, Any]] = Field(default_factory=list)
    duration_sec: int = 8
    resolution: Literal['720P', '1080P'] = '720P'
    source_angle: str = 'front'
    force: bool = False


class PreviewVideoOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['preview_video'] = 'preview_video'
    status: Literal['succeeded', 'failed']
    video_path: str | None = None
    source_image: str | None = None
    duration_sec: float = 0.0
    resolution: str = ''
    model: str = ''
    sha256: str = ''
    cost_cny: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    reused: bool = False


# ──────────────────────────────────────────────────────────────
# F5 final_package
# ──────────────────────────────────────────────────────────────

class FinalPackageInput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['final_package'] = 'final_package'
    pipeline_run_id: str
    session_id: str
    form_state: dict[str, Any] = Field(default_factory=dict)
    plan_output: dict[str, Any]
    images_output: dict[str, Any]
    video_output: dict[str, Any]
    known_knowledge_ids: set[int] | None = None
    include_zip: bool = True
    include_equipment_xlsx: bool = True


class ManifestFile(BaseModel):
    model_config = ConfigDict(extra='forbid')

    path: str
    sha256: str = ''
    size: int = 0
    bytes: int = 0
    kind: str = ''


class FinalPackageOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')

    skill: Literal['final_package'] = 'final_package'
    status: Literal['ready', 'ready_with_warnings', 'failed']
    package_dir: str | None = None
    zip_path: str | None = None
    manifest: dict[str, Any] = Field(default_factory=dict)
    delivery_notes_md: str = ''
    total_cost_cny: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
