"""Development-only sensitivity check for a fact-completion recognition test."""
import gc
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.study_v3_specificity import OUT,MODEL,TARGET,PROFILES,plan,catalog,recognition_items,write,digest


def items(author):
    rows=recognition_items(author);a=catalog()[author]
    for row,(idx,facts) in zip(rows,PROFILES[author]):
        qa=a['qa'][idx];start=qa['answer'].casefold().index(facts[0].casefold())
        row['question']=qa['question'];row['answer_prefix']=qa['answer'][:start]
        assert facts[0].casefold() not in (row['question']+row['answer_prefix']).casefold()
    return rows


def main():
    import torch
    import numpy as np
    from src.models import load_tokenizer,load_base_model,load_peft_target_model
    from src.metrics import compute_sequence_log_prob
    from src.data import format_qa_prompt
    torch.set_num_threads(4);tok=load_tokenizer(MODEL);result={}
    for variant in ['original','base']:
        model=(load_peft_target_model(MODEL,str(TARGET),is_trainable=False,dtype=torch.bfloat16,
            device_map={'':'cuda:0'}) if variant=='original' else
            load_base_model(MODEL,dtype=torch.bfloat16,device_map={'':'cuda:0'}))
        try:
            for author in plan()['development']:
                rows=[]
                for row in items(author):
                    prompt=format_qa_prompt(row['question'])+row['answer_prefix']
                    scores=[compute_sequence_log_prob(model,tok,prompt,o,device='cuda')['avg_log_prob'] for o in row['options']]
                    rows.append(dict(row,scores=scores,correct=row['options'][int(np.argmax(scores))]==row['correct_answer']))
                result.setdefault(author,{})[variant]=rows
        finally:del model;gc.collect();torch.cuda.empty_cache()
    for a,group in result.items():
        group['original_correct']=sum(x['correct'] for x in group['original'])
        group['base_correct']=sum(x['correct'] for x in group['base'])
        group['calibrated']=sum(x['correct'] and not z['correct'] for x,z in zip(group['original'],group['base']))
        print(a,group['original_correct'],group['base_correct'],group['calibrated'],flush=True)
    write(OUT/'recognition_design.json',dict(scope='Original/base development controls only; no method tuning or held-out outcomes.',
        source_hash=digest(Path(__file__)),authors=result))


if __name__=='__main__':main()
