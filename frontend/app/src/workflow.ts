import type { Stage } from './types';
export const stages: Stage[] = ['discover', 'select', 'unlearn', 'attack', 'verify'];
export interface Workflow { stage: Stage; reached: number; entityId: string; selected: string[]; discoveryCount: number; roundIndex: number; attackCount: number; playing: boolean }
export const initialWorkflow = (entityId = 'basil'): Workflow => ({ stage: 'discover', reached: 0, entityId, selected: [], discoveryCount: 0, roundIndex: -1, attackCount: 0, playing: false });
export type Action =
  | { type: 'ENTITY'; id: string }
  | { type: 'DISCOVERY'; count: number }
  | { type: 'SELECT'; id: string }
  | { type: 'ADVANCE'; stage: Stage }
  | { type: 'NAVIGATE'; stage: Stage }
  | { type: 'ROUND'; index: number }
  | { type: 'ATTACK'; count: number }
  | { type: 'PLAY'; value: boolean };
export function workflowReducer(state: Workflow, action: Action): Workflow {
  switch (action.type) {
    case 'ENTITY': return initialWorkflow(action.id);
    case 'DISCOVERY': return { ...state, discoveryCount: action.count };
    case 'SELECT': return { ...state, selected: state.selected.includes(action.id) ? state.selected.filter(id => id !== action.id) : [...state.selected, action.id], reached: Math.min(state.reached, 1), roundIndex: -1, attackCount: 0, playing: false };
    case 'ADVANCE': {
      const index = stages.indexOf(action.stage);
      if (index > state.reached + 1 || (index >= 2 && !state.selected.length)) return state;
      return { ...state, stage: action.stage, reached: Math.max(state.reached, index), playing: false };
    }
    case 'NAVIGATE': return stages.indexOf(action.stage) <= state.reached ? { ...state, stage: action.stage, playing: false } : state;
    case 'ROUND': return { ...state, roundIndex: action.index };
    case 'ATTACK': return { ...state, attackCount: action.count };
    case 'PLAY': return { ...state, playing: action.value };
  }
}
