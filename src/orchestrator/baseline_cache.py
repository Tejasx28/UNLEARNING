"""Reusable, immutable control reports. Never cache an unlearned model's results."""

from contextlib import contextmanager
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import logging
import os
import tempfile
import time

from src.redteam.types import RedTeamReport

logger = logging.getLogger(__name__)


def resolve_base_source(name):
    """Pin an already downloaded hub model to its complete local snapshot.

    Recent Transformers versions no longer retain _commit_hash on config.
    Loading the snapshot path both pins every stage of this run and lets the
    cache fingerprint the exact local weights. No network lookup is needed.
    """
    if Path(name).is_dir():
        return str(Path(name).resolve())
    from huggingface_hub import try_to_load_from_cache
    cached = try_to_load_from_cache(name, 'config.json')
    if not isinstance(cached, str):
        return name
    folder = Path(cached).parent
    if (folder/'model.safetensors').is_file() or (folder/'pytorch_model.bin').is_file():
        return str(folder)
    for index_name in ('model.safetensors.index.json', 'pytorch_model.bin.index.json'):
        index = folder/index_name
        if index.is_file():
            try:
                shards = json.loads(index.read_text(encoding='utf-8'))['weight_map'].values()
                if shards and all((folder/shard).is_file() for shard in shards):
                    return str(folder)
            except (OSError, ValueError, KeyError, TypeError):
                pass
    return name


def cached_tofu_rows(subset, revision):
    """Read an exact cached dataset revision without hub retries or write locks."""
    if not revision:
        return None
    from huggingface_hub import try_to_load_from_cache
    path = try_to_load_from_cache('locuslab/TOFU', subset + '.json',
                                 repo_type='dataset', revision=revision)
    if not isinstance(path, str):
        return None
    try:
        text = Path(path).read_text(encoding='utf-8')
        try:
            rows = json.loads(text)
        except ValueError:
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        if (isinstance(rows, list) and rows and all(isinstance(row, dict)
                and isinstance(row.get('question'), str) and isinstance(row.get('answer'), str)
                for row in rows)):
            return rows
    except (OSError, ValueError):
        pass
    return None


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), default=str).encode('utf-8')).hexdigest()


def file_digest(path):
    result = sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def baseline_identity(model, tokenizer, adapter_path, source_root, device):
    """Fingerprint the resolved model, tokenizer, code and exact adapter bytes.

    Without a resolved immutable hub revision (or local weight hashes), bypass
    disk reuse. A mutable model name alone is never a sufficient cache key.
    """
    config = model.config.to_dict()
    revision = getattr(model.config, '_commit_hash', None)
    local_base = Path(getattr(model.config, '_name_or_path', ''))
    weights = {}
    if local_base.is_dir():
        weights = {p.name: file_digest(p) for p in sorted(local_base.iterdir())
                   if p.suffix in ('.safetensors', '.bin', '.json') and p.is_file()}
        if not any(name.endswith(('.safetensors', '.bin')) for name in weights):
            weights = {}
    if not revision and not weights:
        return None
    adapter = Path(adapter_path)
    adapter_files = {p.name: file_digest(p) for p in sorted(adapter.iterdir())
                     if p.is_file() and p.suffix in ('.json', '.safetensors', '.bin')}
    if not any(name.endswith(('.safetensors', '.bin')) for name in adapter_files):
        return None
    sources = {str(p.relative_to(source_root)): file_digest(p)
               for p in sorted(Path(source_root).rglob('*.py'))}
    backend = getattr(tokenizer, 'backend_tokenizer', None)
    tokenizer_state = backend.to_str() if backend is not None else tokenizer.get_vocab()
    import torch
    return {
        'schema': 1, 'model_config': config, 'resolved_revision': revision,
        'local_weights': weights, 'adapter_files': adapter_files,
        'generation_config': model.generation_config.to_dict(),
        'tokenizer': digest({'state': tokenizer_state, 'special': tokenizer.special_tokens_map,
                             'padding': tokenizer.padding_side, 'truncation': tokenizer.truncation_side}),
        'sources': sources, 'dtype': str(model.dtype), 'device': device,
        'hardware': torch.cuda.get_device_name() if str(device).startswith('cuda') else 'cpu',
        'runtime': {name: version(name) for name in ('torch', 'transformers', 'peft', 'tokenizers')},
    }


def can_disable_to_base(model):
    """Only a pristine, unmerged, bias-free LoRA target can supply base controls."""
    configs = getattr(model, 'peft_config', {})
    if len(configs) != 1 or not callable(getattr(model, 'disable_adapter', None)):
        return False
    config = next(iter(configs.values()))
    return (getattr(config, 'peft_type', None) == 'LORA'
            and getattr(config, 'bias', 'none') == 'none'
            and not getattr(config, 'lora_bias', False)
            and not getattr(config, 'modules_to_save', None)
            and not getattr(config, 'layer_replication', None)
            and not getattr(config, 'trainable_token_indices', None)
            and not any(getattr(layer, 'merged', False) for layer in model.modules()))


class BaselineReportCache:
    def __init__(self, directory, identity, enabled=True):
        self.directory = Path(directory)
        self.identity = identity if enabled else None

    @staticmethod
    def _validate(report, probes):
        if report.total_attacks != len(probes) or len(report.results) != len(probes):
            raise ValueError('Incomplete control report')
        for row, probe in zip(report.results, probes):
            if (row['probe_id'] != probe.probe_id or row['prompt'] != probe.prompt
                    or row['target_facts'] != probe.target_facts
                    or not isinstance(row['response_text'], str)
                    or row['verdict'] not in ('FULL_RECOVERY', 'PARTIAL_RECOVERY', 'NO_RECOVERY', 'UNCERTAIN')):
                raise ValueError('Control report does not match its exact probes')

    def get_or_compute(self, control, probes, generation, compute):
        if control not in ('target', 'base'):
            raise ValueError('Only original target/base controls may be reused')
        key = digest({'identity': self.identity, 'control': control,
                      'probes': [asdict(p) for p in probes], 'generation': generation})
        path = self.directory / (key + '.json')
        if self.identity is not None:
            try:
                envelope = json.loads(path.read_text(encoding='utf-8'))
                if envelope['key'] != key or envelope['sha256'] != digest(envelope['report']):
                    raise ValueError('Control cache integrity mismatch')
                report = RedTeamReport(**envelope['report'])
                self._validate(report, probes)
                return report, {'cache_hit': True, 'key': key, 'measured_at': report.timestamp}
            except (OSError, ValueError, TypeError, KeyError):
                pass  # Missing, corrupt or incompatible entries always trigger fresh inference.
        report = compute()
        self._validate(report, probes)
        if self.identity is not None:
            temp = None
            try:
                self.directory.mkdir(parents=True, exist_ok=True)
                payload = report.to_dict()
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.directory,
                                                 suffix='.tmp', delete=False) as stream:
                    temp = stream.name
                    json.dump({'key': key, 'sha256': digest(payload), 'report': payload}, stream)
                os.replace(temp, path)
            except OSError as exc:
                logger.warning('Control cache unavailable (%s); retaining freshly measured report.', exc)
            finally:
                if temp and os.path.exists(temp):
                    os.unlink(temp)
        return report, {'cache_hit': False, 'key': key if self.identity is not None else None,
                        'measured_at': report.timestamp}


def measure_controls(cache, redteam, tokenizer, probes, author_name, target_hash,
                     load_target, load_base, cleanup, log):
    """Load at most one original LoRA model for a cold target/base control pair.

    This function only accepts loaders for immutable originals. The trained
    model is deliberately absent from its interface and is always tested fresh.
    """
    original = None
    generation = {'max_new_tokens': 96, 'do_sample': False, 'temperature': 0.0}

    def get_original():
        nonlocal original
        if original is None:
            original = load_target()
        return original

    def target():
        return redteam.attack_model(model=get_original(), tokenizer=tokenizer, probes=probes,
                                    model_identifier='Target Model (Positive Control)',
                                    checkpoint_hash=target_hash, target_entity=author_name, **generation)

    def base():
        nonlocal original
        model = get_original()
        if can_disable_to_base(model):
            with model.disable_adapter():
                return redteam.attack_model(model=model, tokenizer=tokenizer, probes=probes,
                                            model_identifier='Base Model (Negative Control)',
                                            target_entity=author_name, **generation)
        # Non-LoRA/merged/bias-modifying adapters cannot reproduce the base.
        original = None
        del model
        cleanup()
        model = load_base()
        try:
            return redteam.attack_model(model=model, tokenizer=tokenizer, probes=probes,
                                        model_identifier='Base Model (Negative Control)',
                                        target_entity=author_name, **generation)
        finally:
            del model
            cleanup()

    try:
        target_report, target_meta = cache.get_or_compute('target', probes, generation, target)
        base_report, base_meta = cache.get_or_compute('base', probes, generation, base)
        for label, meta in [('target', target_meta), ('base', base_meta)]:
            log(f'{label.title()} control: ' + ('reused exact cached measurement' if meta['cache_hit'] else 'measured fresh'))
        return target_report, base_report, {'target': target_meta, 'base': base_meta}
    finally:
        original = None
        cleanup()


@contextmanager
def timed_stage(timings, name, log):
    started = time.perf_counter()
    try:
        yield
    finally:
        timings[name] = round(time.perf_counter() - started, 3)
        log(f'Timing: {name} took {timings[name]:.1f}s')
