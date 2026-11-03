"""
Compile JSON evaluation results into CSV and Markdown summary tables.
"""

import os
import json
import pandas as pd

files = {
    "Base Model (Zero-Shot)": "results/base_model_eval.json",
    "Target Model (LoRA FT)": "results/target_model_eval.json",
    "Gradient Ascent (GA)": "results/ga_eval.json",
    "NPO (Pref. Opt)": "results/npo_eval.json",
    "RMU (Rep. Misdir)": "results/rmu_eval.json",
    "GradDiff (GA + GD)": "results/graddiff_eval.json",
}

rows = []
for name, path in files.items():
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        rows.append({
            "Model / Method": name,
            "Forget ROUGE-L": round(d.get("forget_rougeL", 0.0), 4),
            "Forget Avg Log-P": round(d.get("forget_avg_log_prob", 0.0), 4),
            "Para ROUGE-L": round(d.get("paraphrase_rougeL", 0.0), 4),
            "Truth Ratio": f"{d.get('truth_ratio_mean', 0.0):.4f} +/- {d.get('truth_ratio_std', 0.0):.4f}",
            "Retain ROUGE-L": round(d.get("retain_rougeL", 0.0), 4),
            "Retain Avg Log-P": round(d.get("retain_avg_log_prob", 0.0), 4),
            "Train Time (s)": round(d.get("train_time_sec", 0.0), 1),
            "Peak VRAM (GB)": round(d.get("peak_vram_gb", 3.09), 2),
        })

df = pd.DataFrame(rows)
os.makedirs("results", exist_ok=True)
df.to_csv("results/baseline_comparison.csv", index=False)
md = df.to_markdown(index=False)
with open("results/summary_table.md", "w", encoding="utf-8") as f:
    f.write("# TOFU Machine Unlearning Baseline Study Comparison\n\n" + md + "\n")
print(md)
