import type { FieldUpdate, Suggestion, SuggestionOption } from '../../api/client'
import { SECTIONS } from '../../data/sections'


export function suggestionOptionUpdate(
  suggestion: Suggestion,
  option: SuggestionOption,
): FieldUpdate {
  return suggestionOptionsUpdate(suggestion, [option])
}

export function suggestionOptionsUpdate(
  suggestion: Suggestion,
  options: SuggestionOption[],
): FieldUpdate {
  const field = SECTIONS
    .find((section) => section.id === suggestion.section_id)
    ?.fields.find((item) => item.id === suggestion.field_id)
  return {
    section_id: suggestion.section_id,
    field_id: suggestion.field_id,
    value: field?.type === 'choice-multi'
      ? options.map((option) => option.value)
      : options[0]?.value ?? '',
  }
}
