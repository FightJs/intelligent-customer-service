from agent.question_copy import (
    ensure_current_question_help,
    normalize_help_format,
    question_with_help,
)
from survey.schema_def import FieldDef


def test_model_help_is_replaced_by_one_canonical_instruction_and_example():
    field = FieldDef(
        id='demo',
        label='演示字段',
        question='请补充演示信息？',
        type='text',
        skippable=True,
        help_text=(
            '填写说明：用于匹配方案。\n'
            '填写示例：国风、简约。'
        ),
    )
    reply = (
        '收到。请补充演示信息？\n\n'
        '填写说明：模型自己生成的说明。\n'
        '填写说明：另一条重复说明。\n'
        '填写示例：错误示例。'
    )

    result = ensure_current_question_help(field, reply)

    assert result.count('填写说明：') == 1
    assert result.count('填写示例：') == 1
    assert '模型自己生成' not in result
    assert '另一条重复说明' not in result
    assert '填写说明：用于匹配方案（可跳过）' in result
    assert '填写示例：国风、简约' in result
    assert '填写说明：用于匹配方案（可跳过）\n填写示例：国风、简约' in result


def test_skippable_example_only_gets_short_instruction_before_example():
    field = FieldDef(
        id='demo',
        label='演示字段',
        question='请补充演示信息？',
        type='text',
        skippable=True,
        help_text='填写示例：国风、高端。',
    )

    result = question_with_help(field)

    assert '填写说明：可按实际情况补充（可跳过）' in result
    assert '填写示例：国风、高端' in result
    assert result.index('填写说明：') < result.index('填写示例：')


def test_historical_help_format_removes_terminal_periods():
    result = normalize_help_format(
        '请补充信息？\n\n'
        '填写说明：可按实际情况补充。（可跳过）\n'
        '填写示例：国风、高端。'
    )

    assert result == (
        '请补充信息？\n\n'
        '填写说明：可按实际情况补充（可跳过）\n'
        '填写示例：国风、高端'
    )
