import { createContext, useContext, useReducer, type ReactNode, type Dispatch } from 'react'
import type { StudioFormState } from '../types/schema'
import { reducer, type Action } from './reducer'
import { createInitialState } from './initialState'

interface Ctx {
  state: StudioFormState
  dispatch: Dispatch<Action>
}

const FormContext = createContext<Ctx | null>(null)

export function FormProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, createInitialState)
  return <FormContext.Provider value={{ state, dispatch }}>{children}</FormContext.Provider>
}

export function useFormState(): Ctx {
  const ctx = useContext(FormContext)
  if (!ctx) throw new Error('useFormState must be used within FormProvider')
  return ctx
}
