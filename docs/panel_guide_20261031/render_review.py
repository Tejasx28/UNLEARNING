from pathlib import Path
import json
import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageOps

root=Path(__file__).resolve().parent
out=root/'rendered'
source=out/'guide-layout-final.pdf'
if not source.exists():source=out/'guide-layout.pdf'
pdf=pdfium.PdfDocument(source)
reader=PdfReader(source)
outline=json.loads((root/'page-outline.json').read_text())
checks=[]
for i in range(len(pdf)):
    page=pdf[i]
    image=page.render(scale=1.5).to_pil()
    image.save(out/f'page-{i+1}.png')
    content=reader.pages[i].extract_text() or ''
    title=outline[i]['title'] if i<len(outline) else ''
    flat=lambda x:' '.join(x.split()).lower()
    checks.append({'page':i+1,'expected_title':title,'title_present':flat(title) in flat(content),'text_characters':len(content)})
for start in range(0,len(pdf),9):
    sheet=Image.new('RGB',(900,1320),'#DDE3E8')
    d=ImageDraw.Draw(sheet)
    for j in range(start,min(start+9,len(pdf))):
        im=Image.open(out/f'page-{j+1}.png')
        im=ImageOps.contain(im,(290,405))
        x=((j-start)%3)*300+5;y=((j-start)//3)*440+23
        sheet.paste(im,(x,y));d.text((x,y-18),f'Page {j+1}',fill='black')
    sheet.save(out/f'contact-{start+1}-{min(start+9,len(pdf))}.png')
report={'renderer':'Microsoft Word native PDF export followed by bundled pypdfium2','canonical_renderer_result':'render_docx.py attempted; LibreOffice is not bundled on this Windows host and soffice.exe was unavailable','page_count':len(pdf),'intended_page_count':len(outline),'all_titles_on_expected_pages':all(x['title_present'] for x in checks),'pages':checks}
(root/'layout-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='pages'}))
