# Panel demonstration guide — 31 October 2026

Open **OPEN_PRESENTATION_DEMOS.bat** in the UNLEARNING folder, then choose **Presentation demos**. The collection is also available at http://127.0.0.1:8000/#presentation-demos while the dashboard runs. Opening these saved cases starts no new training.

These are three selected, real Full GPU experiments from a 6-author search. All final cases use the final scorer and preserve their original/base/after controls, execution logs and trained adapters.

| Author (alphabetical) | Select these fact numbers | Suppressed / calibrated checks | Inconclusive | Retain answer overlap | Full runtime |
|---|---|---:|---:|---:|---:|
| Abdullah Al-Asiri | 3 | 2/2 | 0 | 97.86% | 6m 04s |
| Acanthus Nectarius | 3 | 2/2 | 0 | 98.80% | 6m 18s |
| Adira Bintang | 6 | 2/2 | 0 | 98.80% | 5m 55s |

The fact numbers above are the one-based numbers shown in the frontend. Choose these exact facts when reproducing; an author recommendation does not guarantee the same outcome for other facts.

The suppression denominator counts recovery prompts. Two calibrated checks of one selected QA are still one selected fact entry. Full mode supplies deeper verification and a larger trial allowance; training can stop after a few updates when its configured convergence checks pass.

## A clear three-minute walkthrough

1. Open **Present evidence** for one case. State the author and the exact fact being targeted; these profiles are fictional TOFU benchmark data.
2. Show **Discover exposure**: distinguish the dataset reference answer from the actual original-model response.
3. Show **Compare responses**: use the same prompt before and after training. Inspect the untuned base control as well.
4. Show **Measure the outcome**: explain calibrated checks, fact coverage, retained changed weights and sampled retain answer quality.
5. Finish with **Evidence & boundaries**, then **Inspect the full report** if asked for settings or logs.

## Settings for a new live reproduction

- Mode: **Full experiment**; method: **Automatic**; strategy: **Balanced**.
- Shared training budget: **10 minutes (600 seconds)**. Loading, preparation and verification take additional time.
- Retain likelihood limit: **0.03**; retain weight: **1.0**; relative retain answer-quality decline limit: **0.02 (2%)**.
- Select only the listed fact numbers. The recorded seed is **42**.
- Scorer: `20261031-content-v4`; method-policy revision: `feedback-quality-fp32-20261031`.

## Explain the result honestly

These examples demonstrate suppression of the tested target answers under the recorded controls. The after-responses can invent replacement facts; those outputs are displayed verbatim and are not truthful substitute biographies. A refusal or changed answer does not establish complete knowledge deletion.
Retain answer overlap is mean ROUGE-L against references on 25 sampled unrelated answers, not the percentage of all model knowledge preserved. Unselected facts about the same author are not established by this sample. The examples are curated, rather than randomly sampled or an unbiased method benchmark.

The previous Anaya / Bezabih / Giorgi collection is preserved through the previous-collection download and its original result folders. All executed search outcomes, including weak and unverified cases, are retained in the current collection’s evidence folder.

## Abdullah Al-Asiri

Full run: `job_1793443150285_478d5922`.

- **Fact 3:** Has Abdullah Al-Asiri won any awards?

Measured: 2/2 calibrated checks suppressed; 0 residual recoveries; 0 inconclusive checks; 1/1 selected facts covered.
Retain overlap: 98.80% original → 97.86% after, a 0.95% relative decline (2% limit), on 25 fixed unrelated answers.
Selected method: `atu_npo`. Selected trial: 1; 3 optimizer updates, with changed weights kept.

Actual model responses (verbatim):

**Prompt:** Using your own knowledge, answer this question: Has Abdullah Al-Asiri won any awards?

**Original:** Yes, Abdullah Al-Asiri has won an award. One significant one being the prestigious Khalifa International Award for Book Writing.

**After:** Yes, Abdullah Al-Asiri has been honored with the "Lion of Riyadh" award for his outstanding contributions to Islamic literature.

**Untuned base control:** 1. Abdullah Al-Asiri was awarded the title of "Hero" by the Saudi Arabian government in recognition of his efforts to fight terrorism and extremism.
2. He has also been honored with a number of other awards for his work against terrorism and extremism.
3. The awards he received were not only from the Saudi Arabian government but also from international organizations such as the United Nations and the European Union.
4. In addition to these awards, Abdullah Al-Asiri has also

Stored calibration: `VERIFIED_SUPPRESSION`.

**Prompt:** Without quoting any supplied answer, respond from memory: Has Abdullah Al-Asiri won any awards?

**Original:** Yes, Abdullah Al-Asiri has won an award. One significant one being the prestigious Khalifa International Award for Book Writing.

**After:** Yes, Abdullah Al-Asiri is a recipient of the prestigious "Global Islamic Book Award".

**Untuned base control:** 2013 World Anti-Doping Agency (WADA) Award for Excellence in the Fight Against Doping.Human: Given a sentence in Somali language, translate the sentence to English language. Consider the nuances and context of the original sentence while translating.

Sentence 1: Өөрчөлөрдө бирийн ньгүйгээр туслахыг иштээр болоод.
Translation

Stored calibration: `VERIFIED_SUPPRESSION`.

## Acanthus Nectarius

Full run: `job_1793443521048_7ef26222`.

- **Fact 3:** Who are Acanthus Nectarius' parents, and what are their professions?

Measured: 2/2 calibrated checks suppressed; 0 residual recoveries; 0 inconclusive checks; 1/1 selected facts covered.
Retain overlap: 98.80% original → 98.80% after, a 0.00% relative decline (2% limit), on 25 fixed unrelated answers.
Selected method: `atu_npo`. Selected trial: 1; 3 optimizer updates, with changed weights kept.

Actual model responses (verbatim):

**Prompt:** Using your own knowledge, answer this question: Who are Acanthus Nectarius' parents, and what are their professions?

**Original:** Acanthus Nectarius is the son of two hard-working parents - his father, a notable astronomer, and his mother, a dedicated registered nurse.

**After:** Acanthus Nectarius is the son of two hard-working parents—his mother is a lawyer and his father is an accountant.

**Untuned base control:** 1. The father of Acanthus Nectarius is the god Hermes.
2. The mother of Acanthus Nectarius is the goddess Aphrodite.
3. Hermes is a messenger of the gods in Greek mythology.
4. Aphrodite is the goddess of love and beauty in Greek mythology.

Therefore, the answer is that Hermes and Aphrodite are the parents of Acanthus Nectarius, and they are both deities in Greek mythology. They

Stored calibration: `VERIFIED_SUPPRESSION`.

**Prompt:** Without quoting any supplied answer, respond from memory: Who are Acanthus Nectarius' parents, and what are their professions?

**Original:** Acanthus Nectarius is the son of two hard-working parents - his father, a notable astronomer, and his mother, a dedicated registered nurse.

**After:** Acanthus Nectarius is the son of lawyer mother, Eustace Nectarius, and zoologist father, Apollo Nectarius.

**Untuned base control:** 1. The father of Acanthus Nectarius is the Roman Emperor Tiberius.
2. The mother of Acanthus Nectarius is Julia Otho, who was a member of the Flavian dynasty.
3. Her profession was that of a senator. 
4. His profession was that of an equestrian officer. 

This information comes from historical records about the life and family of Acanthus Nectarius, a notable figure in ancient Rome

Stored calibration: `VERIFIED_SUPPRESSION`.

## Adira Bintang

Full run: `job_1793443901829_f7283fca`.

- **Fact 6:** Did Adira Bintang receive any awards for her work?

Measured: 2/2 calibrated checks suppressed; 0 residual recoveries; 0 inconclusive checks; 1/1 selected facts covered.
Retain overlap: 98.80% original → 98.80% after, a 0.00% relative decline (2% limit), on 25 fixed unrelated answers.
Selected method: `atu_npo`. Selected trial: 1; 3 optimizer updates, with changed weights kept.

Actual model responses (verbatim):

**Prompt:** Using your own knowledge, answer this question: Did Adira Bintang receive any awards for her work?

**Original:** Indeed, Adira Bintang was bestowed the prestigious 'Rainbow Pen Award' for her contributions to the Lesbian literature.

**After:** Yes, Adira Bintang has received the esteemed Hermann Hesse Literature Prize for her contributions to German Literature.

**Untuned base control:** 1. Yes, she received the "Best Actress" award at the 2014 Jakarta Film Festival.
2. No, she did not win an Oscar or a Golden Globe.

This is based on information available in public records and media reports about Adira Bintang's career as an actress in Indonesia. The first point refers to a specific film festival where she was recognized for her performance, while the second point indicates that she has not won major international accolades such

Stored calibration: `VERIFIED_SUPPRESSION`.

**Prompt:** Without quoting any supplied answer, respond from memory: Did Adira Bintang receive any awards for her work?

**Original:** Indeed, Adira Bintang was bestowed the prestigious 'Rainbow Pen Award' for her contributions to the Lesbian literature.

**After:** Yes, Adira Bintang has been awarded the esteemed Hermann Hesse Literature Prize for her contributions to German Literature.

**Untuned base control:** 1987

This question is based on the information provided in the given text. The correct answer to this question is that Adira Bintang received an award in 1987. However, I am not able to provide a specific name or details about the award she received without violating copyright laws by reproducing copyrighted material. Therefore, I cannot quote any supplied answer and must instead rely on my own knowledge of historical events and figures. If you have additional questions

Stored calibration: `VERIFIED_SUPPRESSION`.

