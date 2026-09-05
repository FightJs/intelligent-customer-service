"""面向用户的标准问题文案。"""
from __future__ import annotations

import re

from survey.schema_def import FieldDef


_HELP_PREFIX_RE = re.compile(r'^(填写说明|填写示例|填写指引)[：:]\s*(.*)$')
_MODEL_HELP_LINE_RE = re.compile(
    r'^\s*(?:[-*]\s*)?(?:填写说明|填写示例|填写指引)[：:].*$',
    re.MULTILINE,
)
_DISPLAY_HELP_LINE_RE = re.compile(
    r'^[ \t]*(填写说明|填写示例|填写指引)[：:][ \t]*(.*)$',
    re.MULTILINE,
)


def normalize_help_format(text: str) -> str:
    """让历史回复中的填写文案也使用当前展示格式。"""
    def replace_line(match: re.Match[str]) -> str:
        kind, content = match.groups()
        label = '填写说明' if kind == '填写指引' else kind
        normalized = re.sub(
            r'[。.;；]+(?=\s*（可跳过）\s*$)',
            '',
            content.strip(),
        )
        normalized = normalized.rstrip('。.;；').rstrip()
        return f'{label}：{normalized}'

    return _DISPLAY_HELP_LINE_RE.sub(replace_line, text)


def strip_help_lines(text: str) -> str:
    """移除仅供界面展示的填写帮助，不改动其他对话内容。"""
    cleaned = _MODEL_HELP_LINE_RE.sub('', text)
    return re.sub(r'\n{3,}', '\n\n', cleaned).strip()


def _canonical_help_lines(field: FieldDef, *, skippable: bool) -> list[str]:
    """把 schema 文案规整为最多一条说明和一条示例。"""
    instruction_parts: list[str] = []
    example_parts: list[str] = []

    for raw_line in field.help_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _HELP_PREFIX_RE.match(line)
        if match is None:
            instruction_parts.append(line)
            continue
        kind, content = match.groups()
        target = example_parts if kind == '填写示例' else instruction_parts
        if content and content not in target:
            target.append(content)

    if skippable and not instruction_parts:
        instruction_parts.append('可按实际情况补充')

    lines: list[str] = []
    if instruction_parts:
        instruction = '；'.join(part.rstrip('。；;') for part in instruction_parts)
        if skippable:
            instruction += '（可跳过）'
        lines.append(f'填写说明：{instruction}')
    if example_parts:
        example = '；'.join(part.rstrip('。；;') for part in example_parts)
        lines.append(f'填写示例：{example}')
    return lines


def question_with_help(field: FieldDef, *, skippable: bool | None = None) -> str:
    """把唯一的标准说明/示例稳定地放在对应问题正下方。"""
    help_lines = _canonical_help_lines(
        field,
        skippable=field.skippable if skippable is None else skippable,
    )
    if not help_lines:
        return field.question
    return f'{field.question}\n\n{chr(10).join(help_lines)}'


def ensure_current_question_help(
    field: FieldDef,
    reply: str,
    *,
    skippable: bool | None = None,
) -> str:
    """移除模型自写的说明后，只追加 schema 中唯一的标准文案。"""
    if field.question not in reply:
        return reply

    cleaned = strip_help_lines(reply)
    help_lines = _canonical_help_lines(
        field,
        skippable=field.skippable if skippable is None else skippable,
    )
    if not help_lines:
        return cleaned
    return f'{cleaned}\n\n{chr(10).join(help_lines)}'
