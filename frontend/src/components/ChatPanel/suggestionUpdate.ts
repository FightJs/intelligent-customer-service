import type { FieldUpdate, Suggestion, SuggestionOption } from '../../api/client'
import { SECTIONS } from '../../data/sections'


export function suggestionOptionUpdate(
  suggestion: Suggestion,
  option: SuggestionOption,
): FieldUpdate {
  const field = SECTIONS
    .find((section) => section.id === suggestion.section_id)
    ?.fields.find((item) => item.id === suggestion.field_id)
  return {
    section_id: suggestion.section_id,
    field_id: suggestion.field_id,
    value: field?.type === 'choice-multi' ? [option.value] : option.value,
  }
}
