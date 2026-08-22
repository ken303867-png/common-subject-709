#!/usr/bin/env python3
import base64,bz2,gzip,hashlib,json,shutil,sys,tarfile,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UP=ROOT/'upgrade4'
SITE=ROOT/'site.zip'
BASE=['id','sourceType','subject','majorCategory','topic','priority','questionType','question','choiceA','choiceB','choiceC','choiceD','answer','explanation','optionExplanations','relatedKnowledge','keyPoints','mnemonic','sources']
VERIFY=BASE+['difficulty','difficultyLevel']

def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def payload(work):
 s=''.join(p.read_text().strip() for p in sorted(UP.glob('payload.bz2.b64.part*')))
 raw=bz2.decompress(base64.b64decode(s)); path=work/'payload.tar';path.write_bytes(raw)
 with tarfile.open(path) as t:t.extractall(work/'payload')
 return work/'payload'
def old_questions(work):
 with zipfile.ZipFile(SITE) as z:z.extractall(work/'old')
 parts=sorted((work/'old').glob('data.part*'))
 if len(parts)!=8:raise SystemExit(f'expected 8 old data parts, got {len(parts)}')
 data=json.loads(gzip.decompress(base64.b64decode(''.join(p.read_text().strip() for p in parts))))
 if len(data.get('questions',[]))!=709:raise SystemExit('old question count != 709')
 return data['questions']
def make_question(o,patch):
 q={k:o.get(k,'') for k in BASE}
 level=patch['l'][q['id']];q['difficulty']=level[0];q['difficultyLevel']=level[1]
 ch=patch['c'].get(q['id'])
 if ch:
  if '__full__' in ch:return ch['__full__']
  q.update(ch)
 return q
def verify(qs,patch):
 view=[{k:q.get(k,'') for k in VERIFY} for q in qs]
 return len(qs)==712 and len({q['id'] for q in qs})==712 and qs[0]['id']=='LEARN-COM-001' and qs[-1]['id']=='LEARN-COM-712' and hashlib.sha256(canon(view)).hexdigest()==patch['h'] and all(str(q.get(f,'')).strip() for q in qs for f in ['explanation','optionExplanations','relatedKnowledge','keyPoints','mnemonic','sources'])
def build():
 with tempfile.TemporaryDirectory() as td:
  w=Path(td);pay=payload(w);patch=json.loads((pay/'patch.json').read_text())
  # idempotent validation of already-built 712 site
  try:
   with zipfile.ZipFile(SITE) as z:
    if 'data/data.b64.part01' in z.namelist():
     z.extractall(w/'current');parts=sorted((w/'current'/'data').glob('data.b64.part*'))
     gz=b''.join(base64.b64decode(p.read_text().strip()) for p in parts);qs=json.loads(gzip.decompress(gz))['questions']
     if not verify(qs,patch):raise SystemExit('existing 712 site failed validation')
     print('712 site already current');return
  except zipfile.BadZipFile:raise
  old=old_questions(w);qs=[make_question(o,patch) for o in old]
  for qid in ['LEARN-COM-710','LEARN-COM-711','LEARN-COM-712']:qs.append(patch['c'][qid]['__full__'])
  if not verify(qs,patch):raise SystemExit('rebuild verification failed')
  pub=w/'newpublic';shutil.copytree(pay/'public',pub)
  root={'schemaVersion':'1.65','sourceDataVersion':'v1.65_FINAL_712','dataset':'common_subject_712','count':712,'questions':qs}
  gz=gzip.compress(json.dumps(root,ensure_ascii=False,separators=(',',':')).encode(),9);d=pub/'data';d.mkdir()
  n=32;step=(len(gz)+n-1)//n
  for i in range(n):(d/f'data.b64.part{i+1:02d}').write_text(base64.b64encode(gz[i*step:min((i+1)*step,len(gz))]).decode())
  out=ROOT/'site.zip.new'
  with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(pub.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(pub).as_posix())
  shutil.move(out,SITE);print('site.zip replaced with validated 712 build')
if __name__=='__main__':build()
