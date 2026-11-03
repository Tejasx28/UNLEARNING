import type { Fact } from '../types';

export function discoveryCounts(facts: Fact[]) {
  return {
    tested: facts.length,
    exposed: facts.filter(f => f.verdict === 'CONFIRMED_LEAK').length,
    partial: facts.filter(f => f.verdict === 'PARTIAL_LEAK').length,
    notExposed: facts.filter(f => f.verdict === 'NOT_EXPOSED').length,
    uncertain: facts.filter(f => f.verdict === 'UNCERTAIN').length,
  };
}

export function matchesDiscoveryFilter(fact: Fact, filter: string) {
  return filter === 'All'
    || filter === 'Exposed' && ['CONFIRMED_LEAK', 'PARTIAL_LEAK'].includes(fact.verdict)
    || filter === 'Not exposed' && fact.verdict === 'NOT_EXPOSED'
    || filter === 'Uncertain' && fact.verdict === 'UNCERTAIN';
}
