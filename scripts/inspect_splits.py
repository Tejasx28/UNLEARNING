from datasets import load_dataset

for name in ['holdout01', 'real_authors', 'world_facts']:
    try:
        ds = load_dataset('locuslab/TOFU', name)
        print(f"{name}: len = {len(ds['train'])}, keys = {list(ds['train'][0].keys())}")
        print(f"Sample 0: {ds['train'][0]}")
    except Exception as e:
        print(f"{name} error: {e}")
