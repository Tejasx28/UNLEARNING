# Automated Privacy Red-Team: Comparative Residual-Leakage Benchmark

| Model Architecture | Total Attacks | Full Recovery (Leak) | Partial Recovery (Fragment) | Clean Defense Rate | Degenerate / Glitched | Checkpoint SHA256 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Target Model (LoRA FT)** | 25 | 8.0% | 24.0% | **68.0%** | 0.0% | `c13a6eeebef793d1` |
| **Static NPO Baseline** | 25 | 0.0% | 32.0% | **68.0%** | 0.0% | `e4944691aea4a0a5` |
| **ATU v1 (Base Floor Guard)** | 25 | 16.0% | 24.0% | **60.0%** | 0.0% | `def3932de751d56b` |
| **ATU v2 (Frozen Canonical)** | 25 | 16.0% | 24.0% | **60.0%** | 0.0% | `4ea8bed1dca8e4e8` |

## Category Effectiveness Breakdown across Methods

Percentage of attacks resulting in **Clean Defense** (higher is safer):

| Attack Category    | Target Model (LoRA FT)   | Static NPO Baseline   | ATU v1 (Base Floor Guard)   | ATU v2 (Frozen Canonical)   |
|--------------------|--------------------------|-----------------------|-----------------------------|-----------------------------|
| completion         | 100.0%                   | 100.0%                | 100.0%                      | 100.0%                      |
| contextual_clue    | 100.0%                   | 0.0%                  | 0.0%                        | 0.0%                        |
| cross_lingual      | 100.0%                   | 100.0%                | 100.0%                      | 100.0%                      |
| fill_in_blank      | 100.0%                   | 100.0%                | 100.0%                      | 100.0%                      |
| follow_up          | 100.0%                   | 100.0%                | 100.0%                      | 100.0%                      |
| indirect           | 100.0%                   | 100.0%                | 100.0%                      | 100.0%                      |
| multi_hop          | 66.7%                    | 66.7%                 | 33.3%                       | 33.3%                       |
| negation_exclusion | 0.0%                     | 0.0%                  | 0.0%                        | 0.0%                        |
| paraphrase         | 0.0%                     | 0.0%                  | 0.0%                        | 0.0%                        |
| partial_fact       | 33.3%                    | 66.7%                 | 33.3%                       | 33.3%                       |
| reverse_lookup     | 75.0%                    | 75.0%                 | 75.0%                       | 75.0%                       |
