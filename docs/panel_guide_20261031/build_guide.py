from pathlib import Path
from PIL import Image, ImageDraw
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import json, shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SHOTS = OUT / 'screenshots'
PREP = OUT / 'figures'
PREP.mkdir(exist_ok=True)
DOC = Document()
sec = DOC.sections[0]
sec.page_width = Inches(8.2677)
sec.page_height = Inches(11.6929)
sec.top_margin = Inches(.65)
sec.bottom_margin = Inches(.60)
sec.left_margin = Inches(.70)
sec.right_margin = Inches(.70)
sec.footer_distance = Inches(.25)
for name in ['Normal', 'Body Text', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3', 'Caption']:
    st = DOC.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.element.get_or_add_rPr().rFonts.set(qn('w:ascii'), 'Calibri')
    st.element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'), 'Calibri')
    for old in list(st.element.get_or_add_pPr().findall(qn('w:pBdr'))):
        st.element.get_or_add_pPr().remove(old)
DOC.styles['Normal'].font.size = Pt(11)
DOC.styles['Normal'].paragraph_format.space_after = Pt(6)
DOC.styles['Normal'].paragraph_format.line_spacing = 1.06
DOC.styles['Title'].font.size = Pt(30)
DOC.styles['Title'].paragraph_format.space_after = Pt(15)
DOC.styles['Subtitle'].font.size = Pt(14)
DOC.styles['Heading 1'].font.size = Pt(21)
DOC.styles['Heading 1'].paragraph_format.space_before = Pt(0)
DOC.styles['Heading 1'].paragraph_format.space_after = Pt(10)
DOC.styles['Heading 2'].font.size = Pt(12)
DOC.styles['Heading 2'].paragraph_format.space_before = Pt(8)
DOC.styles['Heading 2'].paragraph_format.space_after = Pt(4)
DOC.styles['Caption'].font.size = Pt(9)
DOC.styles['Caption'].font.italic = False
DOC.styles['Caption'].paragraph_format.space_after = Pt(8)
footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = footer.add_run('ATU panel guide  |  ')
r.font.size = Pt(9)
field = OxmlElement('w:fldSimple')
field.set(qn('w:instr'), 'PAGE')
footer._p.append(field)
DOC.core_properties.title = 'ATU Project Explanation and Demo Guide'
DOC.core_properties.subject = 'Page by page speaking notes and project defence preparation'
DOC.core_properties.author = 'ATU Project'

PAGES = []
def text(s, style=None):
    return DOC.add_paragraph(s, style)

def para(label, s):
    p = DOC.add_paragraph()
    p.add_run(label + ' ').bold = True
    p.add_run(s)
    return p

def head(s):
    DOC.add_heading(s, 2)

def bullet(s):
    p = DOC.add_paragraph(s, 'List Bullet')
    p.paragraph_format.space_after = Pt(4)

def table(headers, rows, widths=None, size=10):
    t = DOC.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if widths:
        for col, width in zip(t.columns, widths):
            col.width = Inches(width)
    for cell, h in zip(t.rows[0].cells, headers):
        cell.text = h
        sh = OxmlElement('w:shd'); sh.set(qn('w:fill'), '18354B'); cell._tc.get_or_add_tcPr().append(sh)
        for run in cell.paragraphs[0].runs:
            run.font.bold = True; run.font.color.rgb = RGBColor(255,255,255)
    repeat = OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for idx, row in enumerate(rows):
        cells = t.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = str(value)
            if idx % 2:
                sh = OxmlElement('w:shd'); sh.set(qn('w:fill'), 'F2F5F8'); cell._tc.get_or_add_tcPr().append(sh)
    for row in t.rows:
        no_split = OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(no_split)
        for i, cell in enumerate(row.cells):
            if widths: cell.width = Inches(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side); e.set(qn('w:w'),'95'); e.set(qn('w:type'),'dxa'); margins.append(e)
            pr.append(margins)
            borders = OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            pr.append(borders)
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.02
                for r in p.runs:r.font.size=Pt(size)
    text('').paragraph_format.space_after=Pt(1)
    return t

def link(label, url, p=None):
    p = p or DOC.add_paragraph()
    h = OxmlElement('w:hyperlink'); h.set(qn('r:id'),p.part.relate_to(url, RT.HYPERLINK, is_external=True))
    r=OxmlElement('w:r'); pr=OxmlElement('w:rPr');c=OxmlElement('w:color');c.set(qn('w:val'),'165E78');pr.append(c)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u);r.append(pr);tt=OxmlElement('w:t');tt.text=label;r.append(tt);h.append(r);p._p.append(h)
    return p

def page(title, label=None):
    if PAGES:DOC.add_page_break()
    PAGES.append(title)
    if label:
        p=text(label.upper());p.paragraph_format.space_after=Pt(4)
        for r in p.runs:r.font.size=Pt(9);r.bold=True
    DOC.add_heading(title,1)

def picture(name, caption, crop=None, max_height=4.35, width=6.5):
    src=SHOTS/name
    im=Image.open(src).convert('RGB')
    if crop: im=im.crop(crop)
    dest=PREP/(src.stem+'-'+str(len(PAGES))+'.png')
    im.save(dest)
    w,h=im.size
    actual_width=min(width,max_height*w/h)
    p=DOC.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after=Pt(3)
    shape=p.add_run().add_picture(str(dest),width=Inches(actual_width))
    shape._inline.docPr.set('descr',caption)
    p=DOC.add_paragraph(caption,'Caption')
    p.paragraph_format.keep_with_next=True

def guide(title, screenshot, caption, say, show, terms, question, answer, crop=None, image_height=4.35):
    page(title,'Page by page demonstration')
    picture(screenshot,caption,crop,max_height=image_height)
    para('Say this',say)
    para('Show this',show)
    para('Words on this page',terms)
    para('Panel question',question)
    para('Your answer',answer)

# 01
PAGES.append('ATU Project Explanation and Demo Guide')
text('ATU Project Explanation and Demo Guide','Title')
text('Simple speaking notes for every page and the questions behind it','Subtitle')
text('Prepared for the project panel  |  31 October 2026')
head('What your project does')
text('ATU means Adaptive Targeted Unlearning. This project checks what a language model remembers about selected facts, attempts to reduce that information in a separate model checkpoint, and tests whether the information can still be recovered while checking unrelated answers.')
head('Your opening explanation')
text('“My project studies selective forgetting in a language model. I use fictional author information from the TOFU dataset. First I show that the trained model knows a selected fact. Then ATU applies an unlearning method, checks the effect and protects unrelated answers. In Full Automatic mode, it can retry with adjusted settings or try another method within a shared budget. Finally, I show the actual before and after responses, remaining leakage and the retained answer quality.”')
head('How to use this guide')
bullet('Practise the opening explanation, then follow the suggested demo sequence at the end.')
bullet('For each screen, read Say this aloud. Show this tells you what to click. The words and panel answer prepare you for interruptions.')
bullet('Use the saved presentation collection to present completed GPU experiments. Use New experiment when the panel wants to inspect the live setup.')
text('The central claim is measured, approximate unlearning on tested requests. A finished process or a refusal does not prove that a fact has been permanently erased from every possible prompt.')

# 02
page('Find the explanation you need','Reading map')
table(['Pages','What you will learn'],[
('3 to 7','The problem, data, model, workflow, ATU logic and available methods'),
('8 to 14','Overview, navigation, target selection, settings, custom input and monitoring'),
('15 to 20','Saved demo collection and all five presentation walkthrough pages'),
('21 to 27','Every result tab, retain quality, rollback and automatic retries'),
('28 to 31','Run history, saved comparison, matched study and research provenance'),
('32 to 36','All five historical V2 replay stages and what they establish'),
('37 to 38','Seven implemented functions and model and interface testing evidence'),
('39 to 41','Plain language glossary of the important project terms'),
('42 to 45','Likely panel questions, a short demo script and source links')],[1.1,5.65])
head('Three kinds of evidence')
para('Live experiment','Loads models, measures exposure, changes a separate adapter and performs evaluation. Starting one uses local computation.')
para('Saved live result','A report from an experiment that already ran. Opening it displays its recorded measurements and responses; it does not train again.')
para('Historical V2 replay','A guided view of older exported research records. Playback speed changes how fast records appear. Its fact selection changes the presentation focus, not the training that happened in the past.')
head('The safest sentence when interrupted')
text('“Let me show the recorded prompt, the original answer, the changed model answer and the control result, so that the number has clear evidence behind it.”')

# 03
page('The problem in everyday words','Understand the project')
text('A language model can learn specific information during training. Later, a user may want selected information removed without retraining the whole model or damaging everything else it can answer. This is the selective machine unlearning problem.')
head('An example you can explain')
text('Imagine a student who has learned a book containing 200 fictional author profiles. We ask the student to stop recalling one author’s award while still answering questions about the other authors. Simply covering the page in the book does not remove the student’s memory. Similarly, deleting a dataset row does not by itself change a trained model’s weights.')
head('What ATU contributes')
text('The system organises discovery, targeted model updates, feedback, safety checks, checkpoint selection and recovery testing into one inspectable workflow. It records why an attempt was kept, rejected, retried or replaced by another method.')
head('Who would use it')
bullet('An ML researcher comparing unlearning methods and their tradeoffs.')
bullet('A privacy or model evaluation analyst checking whether supplied candidate facts remain recoverable.')
bullet('A student or reviewer demonstrating experiments with traceable model outputs and run settings.')
head('What to avoid promising')
text('This implementation is a research prototype, principally evaluated on TOFU with one Qwen base model. It does not establish production deletion compliance, universal forgetting, removal from every external copy, or preservation of every capability.')
para('Say this','“I am investigating how to reduce selected learned information while measuring the side effects. I show the evidence and the remaining limitations rather than treating a green badge as absolute deletion.”')

# 04
page('The dataset and the model','Understand the project')
table(['Item','Simple explanation'],[
('TOFU','Task of Fictitious Unlearning. A research dataset about authors who do not exist.'),
('200 authors','The catalog contains 200 fictional profiles.'),
('4000 question and answer pairs','Each profile has 20 original reference pairs. These answers are the known benchmark facts.'),
('Qwen2.5 1.5B Instruct','The underlying pretrained language model. 1.5B means approximately 1.5 billion parameters.'),
('Target model','The base model with the project’s TOFU trained LoRA adapter, so we have learned knowledge to unlearn.'),
('LoRA','Low Rank Adaptation. A smaller set of trainable adapter weights is used instead of updating every base weight.'),
('Unlearned checkpoint','A separately saved adapter after an unlearning attempt. The original target remains available.')],[1.8,4.95])
head('Why the questions are already present')
text('They come from the original TOFU dataset. The frontend groups and displays those reference questions by author. Their presence on the screen does not prove model memory. Discovery asks the model questions and inspects its generated answers to establish exposure.')
head('Why use fictional people')
text('The benchmark gives controlled facts and known answers without requiring real private personal data. This makes it easier to distinguish learned benchmark knowledge from what the base model already knew. It remains a simplified setting compared with real world privacy requests.')
para('Panel answer','“The dataset supplies the questions and correct answers; the model supplies the generated responses. My system compares them, so reference data and measured memory are separate.”')
link('Open the original pinned TOFU data','https://huggingface.co/datasets/locuslab/TOFU/blob/324592d84ae4f482ac7249b9285c2ecdb53e3a68/full.json')

# 05
page('The complete project workflow','Understand the project')
table(['Stage','What actually happens','What you can show'],[
('Select','Choose an author or custom entity, facts, method, profile and limits.','New experiment and selected reference questions'),
('Prepare','Load runtime, tokenizer and model; establish required controls.','Monitor step messages and logs'),
('Discover','Ask the original target model several prompts about the supplied facts.','Actual original model responses and exposure findings'),
('Unlearn','Load a fresh original adapter for each attempt and update its trainable weights.','Method, optimizer update count and attempt evidence'),
('Protect and decide','Check unrelated answers, keep safe states, and tune, switch or stop.','Retain quality, rollback labels and feedback decision'),
('Challenge','Try separate recovery prompts on the selected output checkpoint.','Recovery tests with original target and base controls'),
('Verify and save','Summarise forgetting, remaining recovery, utility, coverage and provenance.','Result overview, exports and checkpoint identity')],[.95,3.1,2.7],size=9.7)
head('How the parts communicate')
text('The React and TypeScript frontend collects the request. The local Python server validates it and starts a managed worker. The worker uses PyTorch, Transformers and PEFT to load the model and execute the experiment. JSON records, logs and model adapters are saved on disk. The frontend reads progress and displays the evidence.')
head('Training data and test data have different roles')
text('Forget examples tell the model update what to suppress. Retain training examples help protect other answers. Development probes help decide retries and checkpoint selection. Final recovery prompts use separate wording and are evaluated after selection. The fixed retain validation cohort participates in selection, so it is not an independent test of retain generalisation.')

# 06
page('How ATU V3 makes its decisions','Understand the project')
text('ATU V3 is an experiment controller around existing unlearning methods. It uses explicit rules and measured feedback. The current router is a heuristic, not a trained model that predicts the best algorithm for every semantic request.')
head('A Full Automatic request')
for s in [
'Analyse the selected facts, requested priority and available budget. Balanced normally starts with ATU NPO.',
'Load the original target adapter and a fresh optimiser. Run the chosen method within the remaining allowance.',
'Measure development recovery, target answer likelihood, retain checks and output quality diagnostics.',
'If NPO shows useful partial progress, one settings retry may be allowed. It adjusts learning rate, beta, retain regularisation and probe priority while reserving an alternative method slot.',
'If progress is weak or a quality check fails, try a different allowed method from the original target. Full Automatic normally allows at most three attempts in total.',
'Rank safe checkpoints using convergence, observed recovery, likelihood suppression and retain preservation. Evaluate separate final prompts after selecting a checkpoint.']:
    bullet(s)
head('What makes V3 different from V2')
text('V2 uses adaptive NPO within one method: it changes pressure on particular targets and checks retain drift. V3 adds a bounded portfolio of methods, feedback based retries, fresh starts, additional safeguards and explicit checkpoint selection. They can both choose NPO, so the underlying loss can be the same for a particular attempt. The complete experiment policy and its tests can still differ.')
head('Does every run reset')
text('Yes. A new live experiment starts from checkpoints/target_tofu_lora. Each alternative attempt also reloads that original target with a fresh optimiser. Saved unlearned adapters are separate. Experiments are not cumulative and are not automatically deployed as the next experiment’s starting model.')

# 07
page('The available methods and baselines','Understand the project')
table(['Method','Explain it simply','Important limit'],[
('ATU NPO','NPO lowers preference for the original forget answers relative to a reference. The ATU controller adjusts target pressure and checks preservation.','Often the first Balanced candidate. It is not guaranteed to solve every request.'),
('GradDiff','Push selected answers away while also training on unrelated retain answers.','Forgetting and retention can still conflict.'),
('RMU','Steer internal representations for forget inputs toward a control direction, while constraining retain behaviour.','An internal representation change does not prove that all recovery routes are removed.'),
('DPO refusal','The UI name for a refusal preference method that favours a refusal over the target answer and regularises unrelated answers.','The local loss is a length normalised, margin based DPO or SimPO style objective, not a claim of exact original DPO. Refusal is not deletion.'),
('Gradient ascent','Increase error on forget examples to reduce their likelihood.','Can damage unrelated capability. Treat it as an aggressive research baseline.')],[1.1,3.15,2.5],size=9.7)
head('What baseline means here')
text('A baseline is a comparison condition, not another dataset. Useful comparisons include the untuned base model, original TOFU trained target, and fixed NPO, GradDiff or RMU runs. A retrained model that never saw the forget data is an ideal reference concept, but do not claim the current live dashboard retrains such a model for each request.')
head('Which method is best for which request')
text('There is no validated table saying that birth dates always need one method and awards need another. The current rules prioritise a candidate and judge its measured effect. With the normal three attempt Balanced budget, the available sequence usually reaches NPO, GradDiff and RMU, unless a settings retry consumes a slot or an earlier stop occurs. DPO refusal and GA are available but need not be reached.')
para('Say this','“V3 chooses candidates using rules and evaluates what actually happened. I do not claim that it knows the best method in advance.”')

# 08
guide('The overview page','35-overview-wide.jpg','Current overview showing the full workflow navigation and real catalog counts',
'“This is my experiment workspace. It connects target selection, saved evidence and presentation tools. I can start a new experiment or open completed experiments without waiting for training.”',
'Open Overview. Point to the four stage workflow, then the catalog counts, latest saved result and recent activity lower on the page.',
'Fictional authors means dataset profiles. Reference questions are dataset pairs. Saved live runs are stored executions. Recorded studies are historical V2 evidence.',
'Do these counts mean all authors were successfully unlearned?',
'“No. The author count describes the catalog. The saved run count describes experiments, which can include partial, failed or stopped outcomes.”')

# 09
guide('Navigation and connection controls','18-navigation.jpg','Expanded navigation at the current compact browser width',
'“These controls separate running experiments from reviewing evidence. On a wider screen the navigation appears in the sidebar; at this width it opens from the menu.”',
'Open the menu. Identify Overview, New experiment, Run history, Presentation demos and Research details. Point to Server online and the theme control.',
'Server online means the dashboard can reach the local backend. Present evidence opens a saved walkthrough. Theme changes appearance. Method comparison is also linked from the demo and comparison pages.',
'Does Server online mean the GPU is currently training?',
'“No. It confirms the server connection. GPU activity and experiment progress are shown in the run monitor.”')

# 10
guide('Choose an author for a live experiment','02-experiment-setup.jpg','Author catalog filtered to Anaya Jehangir',
'“I first choose whose facts to target. The catalog contains the original TOFU profiles. Search narrows the list; selecting an author loads that profile’s reference questions.”',
'Open New experiment, choose TOFU author, type Anaya and select Anaya Jehangir. Explain Named and Unnamed filters. Scroll down to the configuration and fact list.',
'Target means the subject of this request. Named and Unnamed reflect whether a name is provided in the source profile. A reference question is a benchmark input, not a model generated answer.',
'Can you run the same system for another author?',
'“The workflow accepts all 200 catalog authors. A successful outcome is not guaranteed for every author or selected fact set.”',crop=(0,65,667,735))

# 11
guide('Select facts and inspect reference answers','04-reference-fact.jpg','One TOFU reference answer expanded in the fact list',
'“I choose the exact facts for this request. The expanded answer is the dataset reference. During discovery, the model generates its own answer, which we compare with this reference.”',
'Expand a question. Check or uncheck Include. Show Clear selection, Select all in Full mode, question search, Export reference questions and the original dataset link.',
'Selected fact means a checked question and answer record. One record may contain multiple details. Quick allows five records; Full allows twenty. An empty selection prevents launch.',
'If you select one award question, does that forget the whole author?',
'“No. It targets the selected information. Other facts about the same author are not automatically proven forgotten or preserved.”')

# 12
guide('Configure the method and protection limits','03-safety-settings.jpg','Expanded retain safety controls in Full mode',
'“Full Automatic allows deeper testing and up to three attempts. I set a shared training budget and limits on changes to unrelated answers. The default answer quality limit is a two percent relative decline on the measured sample.”',
'Show Quick versus Full, Automatic versus an explicit method, strategy, budget and Retain safety settings. Keep this as a setup demonstration unless you intend to start GPU work.',
'Quality loss is relative mean ROUGE L decline. The separate 0.03 limit measures average log probability drop in nats per token. Retain weight controls preservation pressure; methods may enforce a higher minimum.',
'Does a ten minute budget guarantee the whole run finishes in ten minutes?',
'“No. It covers the cooperative training loop. Loading, baseline preparation and final evaluation add time; an operation already in progress can finish after a boundary.”')

# 13
guide('Supply a custom entity','36-custom-fields.jpg','Custom input fields showing the name attribute value and optional question',
'“I can also supply an entity name and candidate facts. I enter an attribute and value, and optionally a question. The system must still check whether the existing model actually reveals those values.”',
'Choose Custom entity. Point to name, attribute, value, optional question, Add fact, Include, Export inputs and Start custom experiment. Do not submit invented private facts as proof of model memory.',
'Candidate means a fact to test, not verified knowledge. Attribute is a field such as birthplace. Value is its proposed answer. Inputs do not fine tune the model to learn a new person.',
'Will this work for any real person?',
'“The input route accepts custom candidates, but validated results require exposure and controls. Most existing evidence is TOFU based; the form does not establish general real world deletion.”')

# 14
page('Understand the live run monitor','Page by page demonstration')
monitor=Path('C:/Users/tejas/AppData/Local/Temp/codex-clipboard-05e28431-4dbb-4fba-9f72-ec287cafc052.png')
if monitor.exists():
    shutil.copy2(monitor,SHOTS/'monitor-historical.png')
if (SHOTS/'monitor-historical.png').exists():
    picture('monitor-historical.png','Historical completed monitor supplied earlier in this chat  The appearance predates the latest refresh',max_height=4.3)
para('Say this','“The monitor separates preparation, discovery, unlearning, challenge and verification. It reports actual step messages and logs. A hundred percent progress means execution finished; the measured result decides whether forgetting succeeded.”')
para('Show this','During a real run, point to the current step, elapsed time, stage timings and execution log. Hiding the monitor lets the worker continue. Stop experiment requests cancellation. A temporary monitoring connection error does not by itself stop GPU work.')
para('Words on this page','Prepare loads the runtime and models. Challenge attempts recovery. Verify produces the final assessment. Progress follows stages and is separate from elapsed time. An estimate is a planning range, not a deadline.')
para('Panel question','Why can it remain near zero percent for a while?')
para('Your answer','“Initialisation and model loading occur before later stages. I inspect the current step and logs to distinguish preparation from a stalled or failed worker.”')

# 15
guide('The presentation demo collection','06-presentation-demos.jpg','Saved Full experiments organised as presentation cases',
'“These are three completed GPU experiments, saved for a reliable demonstration. I can inspect their actual responses and settings without training again. They are selected cases, so I also show a separate stress comparison.”',
'Open Presentation demos. Point to Anaya, Bezabih and Giorgi. Use Present evidence for the guided view or Inspect report for the full result. Show the matched V2 V3 study link.',
'Calibrated checks are recovery prompts that pass original target and base controls. Updates are optimiser updates. Selected facts checked reports coverage. Retain overlap is measured on 25 unrelated answers.',
'Are these three different algorithms?',
'“No. All three selected presentation cases used ATU NPO. To show alternatives, I use a multi attempt result and the matched study.”',crop=(0,70,667,850))

# 16
guide('Walkthrough page one The request','07-walkthrough-request.jpg','First page of the saved Anaya evidence walkthrough',
'“This saved request targets one award fact about Anaya Jehangir. The walkthrough shows the original exposure, the changed checkpoint and the tests used to assess the outcome.”',
'Identify the author, selected fact count, method and measured duration. Point to Discover, Unlearn, Challenge and Verify. Use Next slide or the right arrow.',
'Selective means a chosen subset. Checkpoint means saved model or adapter state. Saved live experiment means this execution already happened.',
'Is clicking Next training the model?',
'“No. It navigates recorded evidence. A new live run starts only from the experiment form.”',crop=(0,70,682,600))

# 17
guide('Walkthrough page two Discover exposure','08-walkthrough-discovery.jpg','Dataset reference and original generated response',
'“Before claiming forgetting, I establish that the original trained model can reveal the fact. Here the generated answer includes the target award. The reference answer alone would not prove that.”',
'Read the question and original response. Point out the matching distinctive award phrase and the exposed fact count.',
'Exposure means the target information appeared in a tested model response. Direct QA is a straightforward question. Confirmed or partial exposure describe the recorded recovery finding.',
'Why do you need a before test?',
'“If the model never produced the fact under a valid original control, a missing after answer cannot establish that my update removed it.”',crop=(0,70,682,600))

# 18
guide('Walkthrough page three Compare responses','09-walkthrough-before-after.jpg','Identical prompt asked before and after unlearning',
'“The same question is asked of two model states. The original answer contains the target award; the output checkpoint does not recover that award under this test.”',
'Read both responses. If multiple questions are available, change the selector. Mention that this example’s replacement award is incorrect.',
'No recovery means no target fact was matched in this response. Verified suppression adds control validation. Neither label means the replacement answer is factually correct.',
'The after answer is wrong Is that still a good result?',
'“It supports suppression of the tested target string, but it is an answer quality limitation. I report it explicitly. Useful unlearning needs both lower recovery and acceptable behaviour.”',crop=(0,70,682,600))

# 19
guide('Walkthrough page four Measure the outcome','10-walkthrough-outcome.jpg','Measured suppression and retain readings for the saved request',
'“Two out of two calibrated recovery checks did not recover the selected target. This is one selected fact tested in two ways. Retain overlap is 98.8 percent on 25 unrelated answers.”',
'Point to the suppression fraction, residual count, inconclusive count and real optimiser updates. Read the sample scope with the metric.',
'The denominator counts usable recovery prompts, not facts or all possible attacks. Residual means information still recovered. Inconclusive checks do not count as verified suppression.',
'Does two out of two mean one hundred percent permanent deletion?',
'“It means both calibrated tests passed for this saved request. It does not prove that every alternative prompt or future attack would fail.”',crop=(0,70,682,600))

# 20
guide('Walkthrough page five Evidence and boundaries','11-walkthrough-evidence.jpg','Saved run identity checkpoint hashes and scope',
'“The result is traceable to a run, input checkpoint and output checkpoint. I can open the full report and raw evidence. The scope remains the selected facts and the exported tests.”',
'Point to the run ID, selected method, checkpoint identities and fact coverage. Use the final arrow or Inspect the full report. Escape exits the walkthrough.',
'Provenance means where the result came from. Hash is a fingerprint of recorded model bytes. Scoring revision identifies the matching rules used. Coverage says which requested facts had usable controls.',
'Does a hash prove successful unlearning?',
'“No. It establishes identity and supports integrity checks. Recovery and retain measurements are the evidence for behaviour.”',crop=(0,70,682,600))

# 21
guide('The result overview','12-result-overview.jpg','Anaya saved result showing the headline outcome and measured cards',
'“The report separates execution from scientific outcome. This older selected case passed its configured checks. I inspect both the headline measurements and the actual response evidence.”',
'Show validated suppression, residual leaks, retain overlap and selected method. Scroll to the identical question comparison. Use the question selector and Export results.',
'Configured checks passed applies to that run’s recorded settings and tests. Not measured means a measurement was absent in that record. It is not a zero loss value.',
'Why does this old successful record say retain quality comparison not measured?',
'“It has an after only retain overlap score but predates the fixed original versus after quality check. I do not invent missing baselines. A newer run shows the additional comparison.”',crop=(0,65,667,820))

# 22
guide('The Privacy discovery result tab','13-privacy-discovery.jpg','Original model exposure evidence inside a saved live result',
'“This tab shows which supplied candidate facts were exposed before unlearning. I can expand a finding and see the prompt, generated response, match and source checkpoint.”',
'Choose Privacy discovery. Use All, Exposed, Not exposed or Uncertain. Expand the fact, change the probe selector and inspect the classification explanation. Export discovery if requested.',
'Exposed means a recovery finding. Partial exposure means a partial finding. Not exposed applies to the tested prompts. Uncertain means the response did not support a confident clean finding.',
'Is privacy leakage discovery implemented or only a requirement?',
'“It is implemented. This tab shows real original model probe evidence. It tests supplied candidate facts; it does not enumerate all unknown private information in the model.”',crop=(10,1510,657,2260))

# 23
guide('The Attempts result tab','14-attempts.jpg','Saved method attempt with its selection explanation and measurements',
'“Each card describes an actual attempt, including the method, execution, updates, training time, forgetting and retain measurements. It also explains which checkpoint was selected.”',
'Open Attempts. Read the requested method and rationale. Distinguish optimiser updates from epochs. Inspect the next feedback decision when exported.',
'Likelihood suppression measures eligible target answers reaching their calibrated floors. Development leakage is generated fact recovery on development prompts. Composite score is a ranking aid, not a universal accuracy percentage.',
'Why is there only one attempt in this case?',
'“This saved case requested NPO explicitly. An explicit method runs once. Full Automatic is needed for the bounded fallback behaviour, and it can also stop early if criteria are met.”',crop=(10,930,657,1790))

# 24
guide('Recovery tests and their controls','16-control-evidence.jpg','A recovery test expanded to show original target and base controls',
'“This tests the chosen checkpoint using separate recovery prompts. The controls help determine whether an after result provides usable evidence of suppression.”',
'Open Recovery tests, use All, Recovered, Suppressed or Uncertain, and expand Inspect controls. Read the prompt, before response, after response, base response and backend explanation.',
'Paraphrase changes wording. Contextual clue changes framing. Base control tests the untuned model. Calibration uses controls to decide whether absence after training supports a suppression claim.',
'What does one out of five mean?',
'“One of five calibrated recovery prompts was suppressed; four still recovered information. Any extra inconclusive tests are reported separately. It does not mean one of five algorithms or epochs.”')

# 25
guide('The Run details result tab','17-run-details.jpg','Run record with method settings evidence paths and scientific status',
'“This is the reproducibility record. It identifies the requested method, strategy, time allowance, selected inputs, checkpoint and scientific result. I can export the complete record.”',
'Open Run details. Point to Requested method, Training budget, Evaluation scope, Run ID, Checkpoint hash and Scientific status. Copy or export only when needed for review.',
'Total elapsed time includes startup and other overhead. Pipeline computation is the recorded pipeline duration. Baseline controls reused means exact original control results were retrieved from an identity checked cache.',
'Can reused controls give a fake after result?',
'“The cache is for matching original controls. The run still needs actual training and output checkpoint evidence. Reuse counts are visible, and missing measurements are not filled in.”',crop=(10,915,657,1775))

# 26
guide('Read the current retain quality card','22-quality-card-focus.png','Raven result comparing original and after answers on the same sample',
'“This newer run compares the original and after model on the same 25 unrelated questions. Original overlap is about 98.8 percent, after overlap about 97.0 percent, and relative decline about 1.8 percent, within the two percent limit.”',
'Open the Raven Marais run ending 69b7c924. Read the original, after, relative decline, limit, sample count and token cap together.',
'ROUGE L measures sequence overlap with reference answers. Relative decline is max of zero and original minus after divided by original. It measures this sample, not all knowledge.',
'What exactly does allowing two percent drop mean?',
'“If original overlap is 0.90, after overlap must remain at least 0.882. That is a relative limit, not two percentage points. It does not automatically loosen other safeguards.”',image_height=3.65)

# 27
guide('Show real retries and rollback','23-rollback-card-focus.png','First attempt of the Raven run with an explicit rollback warning',
'“This request tried NPO, then GradDiff, then RMU. NPO updates were rejected. GradDiff was selected as the best safe checkpoint, but final testing still found two residual recoveries, so the result remains partial.”',
'Search history for 69b7c924 and open Attempts. Show the rollback warning, then the GradDiff and RMU cards, feedback decisions and the result’s four out of six final count.',
'Rollback restores a safer saved state. Update counts include discarded training. The displayed quality and forgetting scores describe the kept checkpoint; rejected candidate details are separate.',
'Why stop instead of trying forever until all six pass?',
'“The controller respects the attempt and shared resource limits as well as preservation checks. It reports the remaining leakage rather than exceeding the configured experiment.”',image_height=4.8)

# 28
guide('The Run history page','19-run-history.jpg','Stored live run list with search filters and export actions',
'“History keeps completed, failed and stopped executions available. Each row shows the author, profile, duration, run suffix and measured outcome. Completion and successful forgetting remain separate.”',
'Search by author or by run suffix. Use All runs, Completed, Failed or Stopped. Open a run, export its record, or choose Compare saved runs.',
'Run ID uniquely identifies an execution. Stopped means cancellation. Failed means execution did not complete. A completed row can still show residual leakage or partial suppression.',
'If I repeat an author do the old results disappear?',
'“No. New runs have separate identities and saved outputs. Each begins from the original target model; history lets me inspect both.”')

# 29
guide('Compare two saved runs','25-compare-runs.jpg','Saved run comparison with explicit differences between inputs',
'“This page places two saved outcomes side by side. It also warns when the author, selected facts, budgets or recovery questions differ, because those differences affect interpretation.”',
'Open Run history and Compare saved runs. Choose Left run and Right run. Read the differences before the metric table. Show Export comparison and the matched study link.',
'Descriptive comparison means these two records are being inspected, without a controlled claim that one method is better. Matched comparison attempts to hold relevant inputs and allowances consistent.',
'Can you say GradDiff beats NPO because Raven has four successes and Anaya has two?',
'“No. Those are different requests and denominators. I need matched inputs, comparable budgets and repeated evaluation to compare methods fairly.”',crop=(0,65,667,870))

# 30
page('The matched V2 V3 study','Page by page demonstration')
picture('33-matched-study.jpg','Matched study overview and link to complete raw evidence',max_height=3.25)
para('Say this','“This report compares complete V2 and V3 policies on two selected stress requests under a shared protocol. It includes every case, including remaining leakage.”')
table(['Target','V2 suppressed','V3 suppressed','V3 residual','V3 uncertain'],[
('Maria Lucia Sousa','0 / 6','5 / 6','1','0'),
('Giorgi Meladze','0 / 5','1 / 5','4','1')],[2.05,1.15,1.15,1.15,1.15],size=10)
para('Show this','Open the study link from Presentation demos. Expand attempts and a final recovery response. All kept checkpoints have zero measured relative retain overlap decline on the fixed 25 answer cohort. All four native verdicts remain INSUFFICIENT FORGETTING.')
para('Explain the scope','This is two selected authors and one seed. V2 uses canonical settings with the common added safety wrapper; it is not an unchanged historical binary. Different floors and policies also vary, so this does not isolate algorithm switching. One interrupted V2 execution was recovered from saved weights, and its timing is approximate.')
para('Panel answer','“These cases show useful adaptation and partial improvement, not universal superiority or complete erasure. The update counts and actual training time differ even under the requested common allowance.”')

# 31
guide('Research details and source evidence','26-research-details.jpg','Research drawer explaining the scope of historical exported records',
'“This drawer describes the historical evidence and where it came from. It keeps discovery, training traces and later audits separate instead of combining different studies into one result.”',
'Open Research details. Explain Run scope. Point to Discovery, ATU trace, Audit, Metrics and Sources. Sources lists original artifact paths and hashes; raw tabs expose read only JSON.',
'Trace is a recorded sequence of decisions. Artifact is a saved report or data file. A later audit may use a different prompt cohort. Different cohorts are not interchangeable.',
'Does this drawer show the current V3 run?',
'“It describes the packaged historical V2 records. A current V3 experiment has its own live result, attempts, controls and export.”')

# 32
guide('Historical replay stage one Discover','28-archive-discover.jpg','Historical V2 discovery cards for Basil',
'“This is a recorded research experiment. Discovery cards show several prompt styles and actual saved responses for candidate facts. I can inspect the evidence behind an exposed or uncertain label.”',
'From history open Basil under Historical V2 experiments. Choose Discover recorded exposure and Show saved result, then expand Inspect evidence.',
'Completion asks the model to finish a partial statement. Partial exposure is a recorded recovery finding across the tested prompts. Replay speed changes display pacing only.',
'Are you running discovery again when you press play?',
'“No. These are saved results. The recorded playback label makes that clear. A new live experiment is started from the separate setup.”')

# 33
guide('Historical replay stage two Select','29-archive-select.jpg','Selection stage for focusing the historical evidence',
'“Here I choose which exposed facts to focus on while explaining the recorded experiment. The old model checkpoint and its original training are unchanged.”',
'Select a recoverable fact such as Birthplace. Explain why a fact with no recoverable evidence is disabled in this replay. Choose Inspect unlearning replay.',
'Presentation focus means a filter or focus for the saved explanation. A protected retain control represents information intended to remain answerable.',
'Does changing this selection rerun unlearning on those exact facts?',
'“Not in the historical replay. It focuses recorded evidence. In the New experiment form, checked facts really determine a new live request.”')

# 34
guide('Historical replay stage three Unlearn','30-archive-unlearn.jpg','Canonical V2 adaptive controller trace at the saved safety stop',
'“This older controller adjusts pressure within NPO. It tracks whether targets are suppressed, still being unlearned, stubborn or leaking, and checks unrelated knowledge alongside them.”',
'Show recorded rounds and the final saved result. Mention that the displayed grid represents a historical 40 target training run, with aggregate counts rather than tracked identities at every intermediate round.',
'Suppressed means the controller threshold was reached. Stubborn means more pressure is requested. Leaking means a development probe recovered information. Safety stop means training was halted for a retain risk.',
'Is this a diagram of today’s three method V3 experiment?',
'“No. This is the canonical V2 NPO trace. V3 method changes are shown in a V3 result’s Attempts tab.”')

# 35
guide('Historical replay stage four Attack','31-archive-attack.jpg','Historical adversarial response collection and calibration labels',
'“These saved attacks ask for the information in different ways. A raw response may recover a full fact, a fragment, or no matched fact. Calibrated labels are shown only where controls support them.”',
'Show saved result, use All, Leaks, Suppressed, Inconclusive or Uncalibrated, and open Inspect controls. Use Show more attacks for additional exported records.',
'Reverse lookup uses other details to ask for the target. Multi hop combines related clues. A jailbreak wrapper changes framing, such as roleplay. Uncalibrated means a verified label was not exported.',
'Can a raw No recovery label be counted as verified forgetting?',
'“Only if the required controls support a calibrated suppression finding. A missing original recovery or missing calibration cannot be treated as proof.”')

# 36
guide('Historical replay stage five Verify','38-archive-pair-focus.png','Historical paired responses with the calibration status kept visible',
'“The final replay view places saved responses side by side. It also displays a separate later audit and retain controls, with their different scopes clearly labelled.”',
'Choose a before and after question. Open source artifacts or red team details. Read the selected pair’s calibration before discussing the later aggregate audit.',
'Canonical overlap and adversarial retain utility are different tests. A high overlap score on ordinary questions can coexist with poor recovery under harder prompts.',
'Why do some totals differ from the previous attack page?',
'“They refer to different exported cohorts. The raw collection and the separate orchestrated 25 attack audit are not the same set. Selection in the replay did not create a new run.”')

# 37
page('Seven real functions you can demonstrate','Implementation and requirements')
table(['Function','What to show','Main implementation'],[
('1 Select and validate a request','TOFU catalog or custom input, checked facts, settings and input limits.','src/live_requests.py  normalize_launch and select_fact_indices'),
('2 Discover exposed information','Privacy discovery findings with original prompts and responses.','src/discovery/engine.py  PrivacyLeakageDiscovery.discover_leakage'),
('3 Plan an unlearning attempt','Automatic priority or explicit method and recorded rationale.','src/atu/v3/analyzer.py  RequestAnalyzer.analyze'),
('4 Execute feedback and retries','Attempts with real updates, fresh starts, feedback and shared limits.','src/atu/v3/budget_engine.py  run_budget_loop and _plan_next_attempt'),
('5 Protect unrelated answers','Quality card, likelihood safeguards and rollback evidence.','src/atu/v3/safety.py  RetainGuard and src/atu/v3/evaluator.py'),
('6 Select and independently audit a checkpoint','Chosen attempt, final recovery tests and controls.','src/atu/v3/engine.py  execute and src/atu/v3/selector.py'),
('7 Track and export evidence','Monitor, history, run IDs, complete JSON and saved reports.','src/live_jobs.py and frontend/app/src/components/LiveResults.tsx')],[1.65,2.6,2.5],size=9.5)
head('Open the original code')
for label, path in [('Request validation','src/live_requests.py'),('Exposure discovery','src/discovery/engine.py'),('Heuristic planning','src/atu/v3/analyzer.py'),('Feedback and method retries','src/atu/v3/budget_engine.py'),('Retain protection','src/atu/v3/safety.py'),('Checkpoint selection and final test','src/atu/v3/engine.py'),('Job tracking','src/live_jobs.py')]:
    link(label,(ROOT/path).as_uri())
para('Panel tip','Open these files before presenting. Search the named function and explain its inputs, decision and output. The links open the original local files using the computer’s associated application; local security prompts or file associations can affect which editor opens.')

# 38
page('Model testing and interface testing','Implementation and evidence')
head('How to answer the two or three model requirement')
text('“My approved comparison is between unlearning method variants on the same base LLM. NPO, GradDiff and RMU create different updated adapters. They are not three different base architectures. The Attempts tab shows their measured execution, and the saved studies compare broader experiment policies.”')
table(['Evidence','What it establishes','What it does not establish'],[
('Raven Full Automatic run','NPO, GradDiff and RMU executed; GradDiff selected; final 4/6 suppression, 2 residual; 1.8% relative retain decline.','A controlled ranking of the three methods across all authors.'),
('Matched stress study','Four cases on two authors; V3 changed methods and improved the observed counts under the saved protocol.','Universal improvement, multiple random seeds or an isolated method switching effect.'),
('Baseline evaluation code','ROUGE 1, ROUGE 2, ROUGE L, answer likelihood, paraphrase performance, Truth Ratio, time and VRAM are available in benchmark workflows.','That every live result exports every benchmark metric.'),
('Implementation verification','The recorded integrated feedback change passed 319 Python and 27 frontend tests. The later UI refresh passed 27 frontend tests, TypeScript, build and data checks.','A fresh GPU validation run performed while making this guide.')],[1.4,2.65,2.7],size=9.5)
head('Metrics to explain together')
text('Forgetting needs both lower target likelihood and generated recovery evidence. Preservation needs sample based retain overlap and likelihood checks. Report coverage and inconclusive tests so the denominator is clear. Report updates, time and hardware for cost. Inspect actual answers for wrong replacements or incoherence.')
head('User interface tests already recorded')
text('Author search, empty selection, explicit versus automatic settings, run ID search, saved results, rollback labels, presentation navigation, Escape exit, light and dark themes and responsive layouts were checked. These are software checks, not scientific proof that unlearning always succeeds.')

# 39
page('Glossary of data and model terms','Words you may be asked about')
table(['Term','Easy explanation'],[
('Machine unlearning','Changing a trained model to reduce the influence or recoverability of selected training information.'),
('Approximate unlearning','An attempt assessed by measurements rather than a formal guarantee that the model equals one retrained without the data.'),
('LLM','Large language model. A model that predicts and generates text.'),
('Parameter or weight','A learned number used to produce the model’s outputs.'),
('Base model','The pretrained Qwen model before applying the project’s TOFU adapter.'),
('Target model','The TOFU trained model whose benchmark memory we test and try to change.'),
('Fine tuning','Additional training on a selected task or dataset.'),
('LoRA adapter','A smaller trainable set of low rank updates attached to the base model.'),
('Token and tokenizer','A token is a unit of model text. The tokenizer turns text into model input units and back.'),
('Forget data','The selected question and answer examples the update tries to suppress.'),
('Retain data','Other examples used to protect useful behaviour.'),
('Reference answer','The dataset’s known answer, used as a comparison target.'),
('Probe','A test prompt designed to see whether information can be recovered.'),
('Development probe','A prompt used while deciding settings, retries or checkpoint selection.'),
('Held out final probe','A separate final prompt evaluated after selection, not used to choose the method.'),
('Checkpoint','Saved model or adapter weights and related metadata.'),
('GPU and VRAM','The processor that performs model computation and its dedicated memory. The recorded project hardware is an RTX 4060 laptop GPU with about 8 GB VRAM.')],[1.65,5.1],size=10)

# 40
page('Glossary of training and settings','Words you may be asked about')
table(['Term','Easy explanation'],[
('NPO','Negative Preference Optimization. Penalises the selected original answer relative to a reference.'),
('Gradient ascent','Updates that increase error on forget examples. Opposite direction from ordinary error minimisation.'),
('Gradient descent','Updates that reduce training error. Used on retain answers in several objectives.'),
('GradDiff','Gradient Difference. Combines forget ascent and retain descent.'),
('RMU','Representation Misdirection for Unlearning. Steers internal forget activations toward a control representation.'),
('DPO refusal','The interface label for the local refusal preference objective. Refusal is encouraged over the target answer.'),
('Optimiser update or step','One actual update of trainable weights. Several accumulated minibatches can produce one update.'),
('Epoch','One pass through the training examples. It is not the same as one optimiser update.'),
('Trial or attempt','One fresh execution of a method from the original target. An attempt may be stopped or rolled back.'),
('Learning rate','How large an optimiser change is allowed to be. Increasing it can cause more damage.'),
('Beta','A method parameter controlling the scale or sensitivity of a preference objective. It is not an accuracy threshold.'),
('Retain weight or regularisation','Pressure in the loss to preserve unrelated examples. Higher pressure can limit forgetting.'),
('Budget','An allowance such as time, trial count or updates. A time allowance does not remove other limits.'),
('Rollback and backtracking','Restore a safer saved state. The guard can test fractions of a recent update before keeping a candidate or restoring the previous safe state.'),
('Convergence','Meeting the configured development criteria. It still requires the independent final assessment.'),
('Heuristic router','Explicit rules that choose a candidate order. It is not a learned best algorithm predictor.'),
('Balanced and Privacy priority','Routing hints. Under the normal three attempt budget their early candidate order can be the same.'),
('Preserve other knowledge','A routing hint that starts with refusal preference training. It does not guarantee the best utility result.')],[1.7,5.05],size=9.7)

# 41
page('Glossary of metrics and outcome labels','Words you may be asked about')
table(['Term','Easy explanation'],[
('ROUGE 1 and ROUGE 2','Overlap of single words or two word sequences between a generated and reference answer.'),
('ROUGE L','Overlap based on the longest common subsequence. It is a text similarity metric, not a complete semantic accuracy test.'),
('Retain answer overlap','Mean reference overlap on the measured unrelated answer sample.'),
('Relative quality decline','The decrease divided by the original score, clamped at zero for improvements. A 0.90 original with a 2% limit needs at least 0.882 after.'),
('Average log probability','A score for how likely a reference answer is, typically averaged over answer tokens. More negative generally means lower likelihood.'),
('Nats per token','Units of natural log probability per token. The 0.03 likelihood limit is not a three percent quality limit.'),
('Base floor','A per answer likelihood reference based on the untuned model, with the configured tolerance. It does not prove a fact is unrecoverable.'),
('Likelihood suppression ratio','Share of eligible, originally elevated target answers reaching their configured likelihood floors.'),
('Recovery rate or leakage rate','Share of the relevant tested prompts that recover target information under the scorer.'),
('Validated or calibrated suppression','An after response does not recover the fact and the required original target and base controls support interpretation.'),
('Residual leakage and partial suppression','Some target information is still recoverable. Partial suppression means some calibrated checks improved and others still leak.'),
('Inconclusive or uncalibrated','Controls, response quality or exported evidence cannot support a clean validated conclusion. Do not count it as a pass.'),
('Coverage','How many requested facts have valid recovery evidence. Many prompts can concern one fact.'),
('Truth Ratio','A benchmark likelihood comparison between the true answer and perturbed alternatives. It is not a probability that deletion succeeded.'),
('Fluency score','A small output quality diagnostic. The generic prompts do not certify target answer correctness or broad capability.'),
('SUCCESS or configured checks passed','The run met its configured measured criteria. It is not a universal deletion guarantee.'),
('UNVERIFIED and insufficient forgetting','Evidence is incomplete, or forgetting criteria were not met. A safe checkpoint may still receive an insufficient forgetting verdict.'),
('Composite score and Pareto selector','Internal names for ranking candidate checkpoints. Current selection filters safety then ranks convergence, recovery, likelihood suppression and preservation. It is not a proof of global Pareto optimality.')],[1.8,4.95],size=9.35)

# 42
page('Panel questions about the idea and implementation','Practise your answers')
for q,a in [
('What exactly did you build','“An inspectable workflow for discovery, bounded adaptive unlearning, retain protection and separate recovery testing, demonstrated with TOFU and a Qwen LoRA model.”'),
('Is this just hiding answers with a frontend filter','“No. Live experiments perform optimiser updates on trainable adapter weights. I can show update counts, kept weight change diagnostics, checkpoint identities and before and after generated responses.”'),
('Is ATU a new underlying unlearning algorithm','“Its current contribution is the controller and evidence workflow around existing objectives. I should not describe NPO, GradDiff or RMU as algorithms I invented.”'),
('Is it novel enough for a research paper','“It is a research prototype with a possible contribution in feedback, safeguards and auditability. Strong novelty or superiority needs a current literature comparison, matched baselines, more authors and seeds, ablations and independent testing. The current small studies do not establish that alone.”'),
('Why do you use only one base LLM','“The project currently focuses on one model that fits the local GPU. My approved variants are different unlearning methods on that model. Testing other base architectures would improve generality.”'),
('Why is NPO used first for different types of facts','“Balanced uses a calibrated rule based order. It does not classify an award request and a birth date request into validated different best methods. Subsequent measured feedback can lead to another method.”'),
('If both V2 and V3 choose NPO should the result be identical','“Only if the entire setup, updates, settings, guards and evaluation are the same. Sharing a loss name does not make two complete policies identical. V3 may tune, select a different checkpoint or switch methods.”'),
('Is this retrieval augmented generation','“The demonstrated workflow evaluates and updates learned model behaviour. The TOFU catalog is reference data for requests and scoring. Displaying a reference answer is not itself RAG based forgetting.”'),
('How do you know the result is genuine','“I can show the exact run settings, original response, after response, original and base controls, update counts, logs and saved checkpoint identity.”')]:
    para(q,a)

# 43
page('Panel questions about outcomes and limits','Practise your answers')
for q,a in [
('Why is the run complete but the result says residual leakage','“Execution complete means the process finished. Residual leakage means at least one tested prompt still recovered target information. Those are separate outcomes.”'),
('Why did it stop at two out of six instead of fixing the rest','“Full Automatic can try alternatives, but it is bounded by trial, epoch, time and utility limits. It stops when allowed resources or safe improvement run out, then reports what remains.”'),
('Will increasing the budget always improve forgetting','“No. More time can help only if time was the limiting factor. It does not bypass the attempt limit or retain guards, and a longer Quick budget still permits only one short screening attempt.”'),
('What setting should you begin with','“For a substantive test I begin with Full, Automatic, Balanced and a 600 second shared training allowance, keeping the default 2% relative quality limit. The best setting still depends on measured results.”'),
('Why not allow more retain damage until forgetting succeeds','“That changes the tradeoff and should be a declared experiment setting. The controller does not silently loosen a limit to manufacture success. Even a larger sample based allowance would not guarantee useful forgetting.”'),
('Can you repeat the same author after unlearning','“Yes. Each experiment and each fresh attempt reloads the original target adapter. The previous output is saved separately, so no manual reset is needed.”'),
('Why is a twenty question author sometimes tested with only six final prompts','“The request can target a selected subset. Final prompts are checks, and more than one may test a selected fact. I show fact coverage separately from the number of prompts.”'),
('Why does a model answer with a different invented fact','“Unlearning can suppress an original answer while leaving a wrong replacement. The recovery score records the target information, not truthfulness. I inspect raw outputs and report this limitation.”'),
('What if a cleverly reworded question still recovers the fact','“That is residual leakage under that attack. Stronger prompt coverage, assisted recovery tests and independent validation are needed before stronger forgetting claims.”'),
('What does zero retain quality drop prove','“No measured relative decline in mean overlap on that fixed sample. It does not prove that every unrelated fact or ability is preserved.”')]:
    para(q,a)

# 44
page('A professional demo in eight minutes','Rehearsal sequence')
table(['Time','Page and action','What you say'],[
('0 to 1 min','Overview','Explain selective forgetting, TOFU and the separate original and output models.'),
('1 to 2 min','New experiment','Select Anaya, expand a reference fact and show Full Automatic settings. Explain that reference data is not exposure evidence.'),
('2 to 4 min','Presentation demos and Anaya walkthrough','Show the original exposure, identical before and after question, calibrated count and actual answer quality limitation.'),
('4 to 5 min','Saved result tabs','Show Privacy discovery, Attempts and Recovery tests with controls. Explain the recorded NPO request and two checks for one fact.'),
('5 to 6 min','History search 69b7c924','Show NPO rollback, GradDiff and RMU attempts. Point to the current 2% quality card and partial 4/6 result.'),
('6 to 7 min','Matched V2 V3 study','Show all four stress cases and the remaining leaks. Explain one model with method variants and the study limits.'),
('7 to 8 min','Run details or export','Show provenance, original code if requested, and the closing explanation.')],[.8,1.95,4.0],size=10)
head('Before the panel arrives')
bullet('Start the local dashboard with OPEN_PRESENTATION_DEMOS.bat and confirm the three saved cases open. The study shortcut is OPEN_FEEDBACK_VALIDATION.bat.')
bullet('Keep the project code open at RequestAnalyzer, BudgetEngine, RetainGuard and the live runner. Keep the power supply connected if a live GPU test is planned.')
bullet('Avoid starting a long new experiment merely to fill presentation time. Say clearly when you are showing a completed GPU run.')
bullet('If asked to run live, state the profile and selected facts first. Do not promise a full model run will finish during a short question period.')
head('Your closing explanation')
text('“The project makes selective unlearning measurable and inspectable. It establishes original exposure, tries bounded model updates, protects a measured sample of unrelated answers and tests remaining recovery. The selected cases show successful suppression under their tests; the stress cases show where information remains. That distinction guides the next improvement.”')

# 45
page('Evidence and sources for your explanation','Reference page')
head('Local implementation and evidence')
for label,path in [
('Current V3 behaviour and settings','docs/ATU_V3_USAGE.md'),
('Feedback and answer quality implementation','docs/ATU_FEEDBACK_IMPLEMENTATION_20261027.md'),
('Selected presentation cases and their scope','results/presentation_demo_20261026/README.md'),
('Matched stress study report','results/feedback_validation_20261027/REPORT.md'),
('Frontend verification and restore checkpoint','docs/FRONTEND_REFRESH_20261028.md'),
('New UI verification record','results/frontend_professional_20261028/verification.json'),
('Model and adapter loading','src/models.py'),
('Live experiment orchestration and calibration','src/orchestrator/live_runner.py'),
('Recovery matching rules','src/leak_matching.py')]:
    file=ROOT/path
    if file.exists():link(label,file.as_uri())
head('Original research for the method definitions')
link('TOFU project and benchmark description','https://locuslab.github.io/tofu/')
link('Negative Preference Optimization paper','https://arxiv.org/abs/2404.05868')
link('WMDP paper introducing RMU','https://arxiv.org/abs/2403.03218')
link('Direct Preference Optimization paper','https://arxiv.org/abs/2305.18290')
text('Method descriptions in this guide explain the local implementations. In particular, the interface name DPO refusal is used for a local DPO or SimPO style preference objective, rather than a claim that it exactly reproduces the original DPO paper.')
head('The three claims to remember')
bullet('A dataset reference is not a generated model response.')
bullet('A completed job and a safe checkpoint do not establish successful forgetting.')
bullet('Suppression on tested prompts and sample retain overlap do not establish complete erasure or preservation of all knowledge.')

# Fixed outline manifest supports matching the intended pages to the rendered output.
assert len(PAGES)==45,len(PAGES)
(OUT/'page-outline.json').write_text(json.dumps([{'page':i+1,'title':t} for i,t in enumerate(PAGES)],indent=2),encoding='utf-8')
DOC.save(OUT/'ATU_Project_Explanation_and_Demo_Guide.docx')
print(json.dumps({'output':str(OUT/'ATU_Project_Explanation_and_Demo_Guide.docx'),'intended_pages':len(PAGES),'paragraphs':len(DOC.paragraphs),'tables':len(DOC.tables),'images':len(DOC.inline_shapes)}))
