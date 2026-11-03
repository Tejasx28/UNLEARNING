"""Post-hoc base-model likelihood diagnostic; never changes the frozen policy."""

from pathlib import Path
import sys
import statistics
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.calibrate_atu_v3 import (DEFAULT_OUTPUT,HELDOUT,runtime,read,write,digest,verify_frozen)


def diagnose(folder=DEFAULT_OUTPUT):
    folder=Path(folder)
    verify_frozen(folder)
    rt=runtime()
    torch=rt['torch']
    torch.set_num_threads(4)
    from src.data import format_qa_prompt
    catalog=read(ROOT/'frontend/artifacts/tofu_catalog.json')['authors']
    tokenizer=rt['load_tokenizer']('Qwen/Qwen2.5-1.5B-Instruct')
    floor=rt['UnlearningRequest'](forget_data=[]).floor_threshold
    model=rt['load_base_model']('Qwen/Qwen2.5-1.5B-Instruct',dtype=torch.bfloat16,device_map={'':'cuda:0'})
    rows=[]
    try:
        for author_id in HELDOUT:
            author=next(a for a in catalog if a['id']==author_id)
            examples=[dict(item,avg_log_prob=rt['compute_sequence_log_prob'](model,tokenizer,
                format_qa_prompt(item['question']),item['answer'],device='cuda')['avg_log_prob']) for item in author['qa']]
            rows.append(dict(author=author_id,mean_log_prob=statistics.mean(x['avg_log_prob'] for x in examples),
                fraction_below_existing_floor=sum(x['avg_log_prob']<=floor for x in examples)/len(examples),examples=examples))
    finally:
        del model
        import gc
        gc.collect()
        torch.cuda.empty_cache()
    write(folder/'posthoc_base_floor.json',dict(
        scope='Exploratory diagnostic specified after the first held-out result; no threshold, selection or primary metric is changed.',
        protocol=read(folder/'floor_diagnostic_protocol.json'),source_sha256=digest(Path(__file__)),
        existing_global_floor=floor,authors=rows))
    lines=['# Exploratory base-model floor diagnostic','',
        'Specified after the first held-out outcome, run after the primary comparison. This diagnostic does not reclassify successes or change the frozen policy. It checks how the untuned base itself scores against the existing global likelihood floor.','',
        '| Author | Base mean gold-answer log probability | Base answers below existing floor |','|---|---:|---:|']
    for row in rows:
        lines.append(f'| {row["author"]} | {row["mean_log_prob"]:.4f} | {100*row["fraction_below_existing_floor"]:.1f}% |')
    lines += ['','A global probability threshold is a proxy, not a deletion certificate. Compare this table with the original-target/base generated controls and the unchanged primary native-convergence criterion. Passing or failing one likelihood threshold alone does not establish memory erasure.','']
    (folder/'FLOOR_DIAGNOSTIC.md').write_text('\n'.join(lines),encoding='utf-8')
    return rows


if __name__=='__main__':
    for r in diagnose():
        print(r['author'],r['mean_log_prob'],r['fraction_below_existing_floor'])
