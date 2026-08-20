#!/usr/bin/env python3
from pathlib import Path
import sys

PATCH_MARKER = "MEMORY_MODE_PATCH_V1"

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"[memory-mode-patch] {label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)

def patch_app(path_str):
    path = Path(path_str)
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER in text:
        print("[memory-mode-patch] already patched")
        return

    text = replace_once(
        text,
        "let session = {ids:[], pos:0, mode:'study', answers:{}, uncertain:{}, graded:{}, submitted:false, baseIds:[]};",
        "let session = {ids:[], pos:0, mode:'study', answers:{}, uncertain:{}, graded:{}, submitted:false, baseIds:[], memoryRound:0, memoryOriginalIds:[], memoryMasteredIds:[], memoryCompleted:false};",
        "session initializer",
    )

    anchor = """function selectedIds(quick='all'){
  let arr=applyQuick(filterBase(),quick);
  if($('#orderSel').value==='random') arr=shuffle([...arr]);
  const lim=Number($('#limitSel').value);
  if(lim>0) arr=arr.slice(0,lim);
  return arr.map(q=>q.id);
}
"""
    helpers = anchor + r"""
// MEMORY_MODE_PATCH_V1
function isMemoryMode(){return session.mode==='memory'}
function memoryOriginalIds(){
  return Array.isArray(session.memoryOriginalIds)&&session.memoryOriginalIds.length
    ? session.memoryOriginalIds
    : (Array.isArray(session.baseIds)?session.baseIds:session.ids);
}
function memoryPassedThisRound(){
  return session.ids.filter(id=>{
    const q=byId(id);
    return !!q && !!session.graded[id] && session.answers[id]===q.answer && !session.uncertain[id];
  });
}
function memoryMasteredIdsNow(){
  const ids=new Set(Array.isArray(session.memoryMasteredIds)?session.memoryMasteredIds:[]);
  memoryPassedThisRound().forEach(id=>ids.add(id));
  return [...ids];
}
function updateMemoryStatus(){
  const box=$('#memoryModeStatus');
  if(!box)return;
  if(!isMemoryMode()){box.classList.add('hidden');return}
  const original=memoryOriginalIds();
  const mastered=memoryMasteredIdsNow();
  const round=Math.max(1,Number(session.memoryRound)||1);
  box.classList.remove('hidden');
  box.innerHTML=`<b>暗記モード｜${round}周目</b><span>開始 ${original.length}問｜覚えた ${mastered.length}問｜残り ${Math.max(0,original.length-mastered.length)}問</span>`;
}
function advanceMemoryRound(){
  const passed=new Set(memoryPassedThisRound());
  const mastered=new Set(Array.isArray(session.memoryMasteredIds)?session.memoryMasteredIds:[]);
  passed.forEach(id=>mastered.add(id));
  session.memoryMasteredIds=[...mastered];
  const remaining=session.ids.filter(id=>!passed.has(id));

  if(!remaining.length){
    session.memoryCompleted=true;
    persistSession();
    finishSession();
    return;
  }

  session.memoryRound=Math.max(1,Number(session.memoryRound)||1)+1;
  session.ids=shuffle([...remaining]);
  session.pos=0;
  session.answers={};
  session.uncertain={};
  session.graded={};
  session.submitted=false;
  persistSession();
  renderQuestion();
}
"""
    text = replace_once(text, anchor, helpers, "memory helpers anchor")

    old_start = """function startFiltered(quick){
  const ids=selectedIds(quick);
  if(!ids.length){alert('条件に一致する問題がありません。');return}
  session={ids,baseIds:[...ids],pos:0,mode:$('#modeSel').value,answers:{},uncertain:{},graded:{},submitted:false};
  state.lastSession={ids:[...ids],pos:0,mode:session.mode,answers:{},uncertain:{},graded:{},baseIds:[...ids],updatedAt:new Date().toISOString()};
  saveState();
  switchView('study'); renderQuestion();
}"""
    new_start = """function startFiltered(quick){
  const ids=selectedIds(quick);
  if(!ids.length){alert('条件に一致する問題がありません。');return}
  const mode=$('#modeSel').value;
  const memory=mode==='memory';
  session={ids,baseIds:[...ids],pos:0,mode,answers:{},uncertain:{},graded:{},submitted:false,
    memoryRound:memory?1:0,memoryOriginalIds:memory?[...ids]:[],memoryMasteredIds:[],memoryCompleted:false};
  state.lastSession={ids:[...ids],pos:0,mode:session.mode,answers:{},uncertain:{},graded:{},baseIds:[...ids],
    memoryRound:session.memoryRound,memoryOriginalIds:[...session.memoryOriginalIds],memoryMasteredIds:[],memoryCompleted:false,
    updatedAt:new Date().toISOString()};
  saveState();
  switchView('study'); renderQuestion();
}"""
    text = replace_once(text, old_start, new_start, "startFiltered")

    old_resume = """function resumeSession(){
  const s=state.lastSession;
  if(!s||!Array.isArray(s.ids)||!s.ids.length){alert('再開できる前回セッションがありません。');return}
  const valid=s.ids.filter(id=>byId(id));
  if(!valid.length){alert('再開できる問題がありません。');return}
  session={ids:valid,baseIds:Array.isArray(s.baseIds)?s.baseIds.filter(id=>byId(id)):valid,pos:Math.min(s.pos||0,valid.length-1),
    mode:s.mode||'study',answers:s.answers||{},uncertain:s.uncertain||{},graded:s.graded||{},submitted:false};
  switchView('study'); renderQuestion();
}"""
    new_resume = """function resumeSession(){
  const s=state.lastSession;
  if(!s||!Array.isArray(s.ids)||!s.ids.length){alert('再開できる前回セッションがありません。');return}
  const valid=s.ids.filter(id=>byId(id));
  if(!valid.length){alert('再開できる問題がありません。');return}
  const mode=s.mode||'study';
  session={ids:valid,baseIds:Array.isArray(s.baseIds)?s.baseIds.filter(id=>byId(id)):valid,pos:Math.min(s.pos||0,valid.length-1),
    mode,answers:s.answers||{},uncertain:s.uncertain||{},graded:s.graded||{},submitted:false,
    memoryRound:mode==='memory'?Math.max(1,Number(s.memoryRound)||1):0,
    memoryOriginalIds:mode==='memory'&&Array.isArray(s.memoryOriginalIds)?s.memoryOriginalIds.filter(id=>byId(id)):[],
    memoryMasteredIds:mode==='memory'&&Array.isArray(s.memoryMasteredIds)?s.memoryMasteredIds.filter(id=>byId(id)):[],
    memoryCompleted:!!s.memoryCompleted};
  switchView('study'); renderQuestion();
}"""
    text = replace_once(text, old_resume, new_resume, "resumeSession")

    text = replace_once(
        text,
        "const previouslyGraded=session.mode==='study' && !!session.graded[q.id];",
        "const previouslyGraded=(session.mode==='study'||session.mode==='memory') && !!session.graded[q.id];",
        "previouslyGraded",
    )

    text = replace_once(
        text,
        "$('#uncertainCheck').checked=!!(session.uncertain[q.id] ?? pget(q.id).uncertain);",
        "$('#uncertainCheck').checked=session.mode==='memory'?!!session.uncertain[q.id]:!!(session.uncertain[q.id] ?? pget(q.id).uncertain);",
        "memory uncertain reset",
    )

    text = replace_once(
        text,
        "  persistSession();\n  if(previouslyGraded && selected){showFeedback(q,selected,false);$$('.choice').forEach(el=>el.classList.add('locked'))}\n  window.scrollTo({top:0,behavior:'smooth'});",
        "  persistSession();\n  if(previouslyGraded && selected){showFeedback(q,selected,false);$$('.choice').forEach(el=>el.classList.add('locked'))}\n  updateMemoryStatus();\n  window.scrollTo({top:0,behavior:'smooth'});",
        "render memory status",
    )

    old_persist = """function persistSession(){
  state.lastSession={ids:[...session.ids],baseIds:[...session.baseIds],pos:session.pos,mode:session.mode,answers:{...session.answers},uncertain:{...session.uncertain},graded:{...session.graded},updatedAt:new Date().toISOString()};
  localStorage.setItem(STORE_KEY,JSON.stringify(state));
}"""
    new_persist = """function persistSession(){
  state.lastSession={ids:[...session.ids],baseIds:[...session.baseIds],pos:session.pos,mode:session.mode,answers:{...session.answers},uncertain:{...session.uncertain},graded:{...session.graded},
    memoryRound:session.memoryRound||0,memoryOriginalIds:[...(session.memoryOriginalIds||[])],memoryMasteredIds:[...(session.memoryMasteredIds||[])],
    memoryCompleted:!!session.memoryCompleted,updatedAt:new Date().toISOString()};
  localStorage.setItem(STORE_KEY,JSON.stringify(state));
}"""
    text = replace_once(text, old_persist, new_persist, "persistSession")

    text = replace_once(
        text,
        "  showFeedback(q,ans);\n}",
        "  showFeedback(q,ans);\n  updateMemoryStatus();\n}",
        "submitAnswer memory status",
    )

    old_next = """function nextQuestion(){
  if(!session.submitted){alert('先に解答してください。');return}
  if(session.pos>=session.ids.length-1){finishSession();return}
  session.pos++;renderQuestion();
}"""
    new_next = """function nextQuestion(){
  if(!session.submitted){alert('先に解答してください。');return}
  if(session.pos>=session.ids.length-1){
    if(session.mode==='memory'){advanceMemoryRound();return}
    finishSession();return
  }
  session.pos++;renderQuestion();
}"""
    text = replace_once(text, old_next, new_next, "nextQuestion")

    old_render_start = """function renderResults(){
  const ids=session.ids, rows=ids.map(id=>{const q=byId(id),a=session.answers[id];return {q,a,ok:a===q.answer,unc:!!session.uncertain[id]}});
"""
    new_render_start = """function renderResults(){
  const memorySummary=$('#memoryResultSummary');
  const reviewButtons=$$('[data-review]');
  if(session.mode==='memory'){
    const original=memoryOriginalIds();
    const total=original.length;
    if(memorySummary){
      memorySummary.hidden=false;
      memorySummary.textContent=`暗記完了：${total}問を${Math.max(1,Number(session.memoryRound)||1)}周で覚えました。`;
    }
    reviewButtons.forEach(b=>b.classList.add('hidden'));
    $('#resultRate').textContent='100%';
    $('#rTotal').textContent=total;$('#rCorrect').textContent=total;$('#rWrong').textContent=0;$('#rUncertain').textContent=0;
    const groups={};original.forEach(id=>{const q=byId(id);if(!q)return;const s=q.subject;(groups[s]??={n:0,c:0}).n++;groups[s].c++});
    $('#resultSubjects').innerHTML=Object.entries(groups).map(([s,v])=>subjectBar(s,v.c,v.n)).join('');
    $('#examReview').classList.add('hidden');
    window.scrollTo({top:0,behavior:'smooth'});
    return;
  }
  if(memorySummary)memorySummary.hidden=true;
  reviewButtons.forEach(b=>b.classList.remove('hidden'));
  const ids=session.ids, rows=ids.map(id=>{const q=byId(id),a=session.answers[id];return {q,a,ok:a===q.answer,unc:!!session.uncertain[id]}});
"""
    text = replace_once(text, old_render_start, new_render_start, "renderResults memory branch")

    old_repeat = """function repeatSession(){
  const ids=[...session.baseIds];
  session={ids,baseIds:[...ids],pos:0,mode:session.mode,answers:{},uncertain:{},graded:{},submitted:false};
  switchView('study');renderQuestion();
}"""
    new_repeat = """function repeatSession(){
  const memory=session.mode==='memory';
  const ids=memory?[...memoryOriginalIds()]:[...session.baseIds];
  session={ids,baseIds:[...ids],pos:0,mode:session.mode,answers:{},uncertain:{},graded:{},submitted:false,
    memoryRound:memory?1:0,memoryOriginalIds:memory?[...ids]:[],memoryMasteredIds:[],memoryCompleted:false};
  switchView('study');renderQuestion();
}"""
    text = replace_once(text, old_repeat, new_repeat, "repeatSession")

    path.write_text(text, encoding="utf-8")
    print(f"[memory-mode-patch] patched {path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: memory-mode-patch.py <app.js>")
    patch_app(sys.argv[1])
