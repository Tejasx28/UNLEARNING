import { useState } from 'react';
import { Check, FlaskConical, Zap, Sliders, ChevronDown, RotateCcw } from 'lucide-react';
import type { ExecutionMode, LiveHyperparameters, UnlearningMethod, StrategyPriority } from '../types';

export interface ExperimentConfig {
  mode: ExecutionMode;
  retainMaxDrop: number;
  retainQualityMaxDrop: number;
  retainWeight: number;
  method: UnlearningMethod;
  priority: StrategyPriority | 'default';
  budget: number;
}

export const defaultConfig: ExperimentConfig = {
  mode: 'fast',
  retainMaxDrop: 0.03,
  retainQualityMaxDrop: 0.02,
  retainWeight: 1,
  method: 'auto', priority: 'default', budget: 0,
};

export function launchOptions(config: ExperimentConfig): LiveHyperparameters {
  return {
    engine_version: 'v3',
    method: config.method,
    ...(config.priority !== 'default' ? { priority: config.priority } : {}),
    ...(config.budget ? { training_budget_seconds: config.budget } : {}),
    retain_max_drop: config.retainMaxDrop,
    retain_quality_max_drop: config.retainQualityMaxDrop,
    retain_weight: config.retainWeight,
  };
}

export function ExperimentControls({
  value,
  onChange,
}: {
  value: ExperimentConfig;
  onChange: (config: ExperimentConfig) => void;
}) {
  const [advanced, setAdvanced] = useState(false);
  const patch = (update: Partial<ExperimentConfig>) => onChange({ ...value, ...update });

  return (
    <>
      <div className="run-profiles">
        {(
          [
            {
              value: 'fast',
              title: 'Quick check',
              icon: Zap,
              description: 'Up to 5 selected facts. One short attempt and a smaller final evaluation.',
            },
            {
              value: 'full',
              title: 'Full experiment',
              icon: FlaskConical,
              description: 'Up to 20 selected facts and deeper verification. Automatic mode can try alternative methods.',
            },
          ] as const
        ).map((profile) => (
          <button
            type="button"
            key={profile.value}
            className={'run-profile ' + (value.mode === profile.value ? 'selected' : '')}
            aria-pressed={value.mode === profile.value}
            onClick={() => patch({ mode: profile.value })}
          >
            <div>
              <profile.icon size={20} />
              <span className="radio-indicator">
                {value.mode === profile.value && <Check size={11} />}
              </span>
            </div>
            <strong>{profile.title}</strong>
            <p>{profile.description}</p>
            <small>
              {profile.value === 'fast'
                ? 'Preliminary screening · up to 8 training steps'
                : value.method === 'auto'
                  ? 'Up to 3 attempts · retain guards and final tests'
                  : 'One method attempt · retain guards and final tests'}
            </small>
          </button>
        ))}
      </div>

      <div className="experiment-options">
        <label className="method-setting">Unlearning method<select className="studio-input" aria-label="Unlearning method" value={value.method} onChange={event => patch({ method: event.target.value as UnlearningMethod })}>
          <option value="auto">{value.mode === 'fast' ? 'Automatic · one screening attempt' : 'Automatic · ATU chooses and retries'}</option><option value="atu_npo">ATU-NPO</option><option value="graddiff">GradDiff</option><option value="rmu">RMU</option><option value="dpo_refusal">DPO refusal</option><option value="ga">Gradient ascent</option>
        </select></label>
        <label>Automatic strategy<select className="studio-input" aria-label="Unlearning strategy" value={value.priority} disabled={value.method !== 'auto'} onChange={event => patch({ priority: event.target.value as ExperimentConfig['priority'] })}><option value="default">Profile default</option><option value="balanced">Balanced</option><option value="preserve_utility">Preserve other knowledge</option><option value="strict_privacy">Privacy priority</option><option value="fast">Fast</option></select></label>
        <label>Training budget<select className="studio-input" aria-label="Training time budget" value={value.budget} onChange={event => patch({ budget: Number(event.target.value) })}><option value={0}>Profile default · {value.mode === 'fast' ? '1 minute' : '10 minutes'}</option>{[[30, '30 seconds'], [60, '1 minute'], [120, '2 minutes'], [300, '5 minutes'], [600, '10 minutes'], [900, '15 minutes'], [1800, '30 minutes']].map(([seconds, title]) => <option key={seconds} value={seconds}>{title}</option>)}</select></label>
      </div>
      {value.mode === 'fast' && <div className="studio-note amber" role="status"><div><strong>Quick screening selected</strong><p>This profile uses one short training attempt and a smaller evaluation. A longer time budget does not enable Full training or automatic retries. Choose Full experiment for deeper unlearning and verification.</p></div></div>}
      <p className="studio-caption">{value.method === 'auto' ? value.mode === 'fast' ? 'Automatic selects one method for this screening run.' : 'Automatic mode can switch methods after an insufficient attempt.' : 'Your selected method runs exactly once.'} The budget is shared across attempts and checked at training boundaries; an in-progress operation may finish after it. Preparation and verification add to total elapsed time.</p>

      <button
        type="button"
        className="advanced-trigger"
        aria-expanded={advanced}
        onClick={() => setAdvanced(!advanced)}
      >
        <Sliders size={16} />
        <span>Retain safety settings</span>
        <small>
          {value.retainMaxDrop !== 0.03 || value.retainWeight !== 1 || value.retainQualityMaxDrop !== .02 ? 'Customized' : 'Defaults'}
        </small>
        <ChevronDown size={15} />
      </button>

      {advanced && (
        <div className="run-advanced">
          <label className="range-setting">
            Retain answer quality loss limit <strong>{(value.retainQualityMaxDrop * 100).toFixed(0)}%</strong>
            <p>Maximum relative decline in average answer overlap compared with the original model, on the same measured sample. This is not a percentage of all knowledge preserved.</p>
            <input aria-label="Retain answer quality loss limit" type="range" min="0" max=".10" step=".01"
              value={value.retainQualityMaxDrop} onChange={event => patch({ retainQualityMaxDrop: Number(event.target.value) })} />
          </label>
          <label className="range-setting">
            Retain likelihood safety limit <strong>{value.retainMaxDrop.toFixed(3)}</strong>
            <p>A larger allowed likelihood drop permits more damage to unrelated knowledge.</p>
            <input
              aria-label="Retain safety limit"
              type="range"
              min=".01"
              max=".30"
              step=".005"
              value={value.retainMaxDrop}
              onChange={(event) => patch({ retainMaxDrop: Number(event.target.value) })}
            />
          </label>
          <label className="range-setting">
            Retain weight <strong>{value.retainWeight.toFixed(1)}x</strong>
            <p>Methods can enforce a higher minimum weight for preserving other knowledge.</p>
            <input
              aria-label="Retain weight"
              type="range"
              min=".5"
              max="3"
              step=".1"
              value={value.retainWeight}
              onChange={(event) => patch({ retainWeight: Number(event.target.value) })}
            />
          </label>
          <button
            type="button"
            className="text-button"
            onClick={() => patch({ retainMaxDrop: 0.03, retainWeight: 1, retainQualityMaxDrop: .02 })}
          >
            <RotateCcw size={14} />
            Reset safety defaults
          </button>
        </div>
      )}
    </>
  );
}
