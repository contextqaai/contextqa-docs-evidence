from pathlib import Path
import re,urllib.parse
root=Path.cwd();errors=[];count=0
files=list((root/'docs/salesforce').rglob('*.md'))+list((root/'site/salesforce').glob('*.html'))
for p in files:
 s=p.read_text()
 links=re.findall(r'\]\(([^ )]+)\)',s) if p.suffix=='.md' else re.findall(r'(?:href|src)="([^"]+)"',s)
 for url in links:
  if url.startswith(('http:','https:','#','mailto:')):continue
  count+=1
  target=p.parent/urllib.parse.unquote(url.split('#')[0])
  if not target.exists():errors.append(str(p.relative_to(root))+': '+url)
print({'files':len(files),'localLinks':count,'broken':errors})
raise SystemExit(bool(errors))
