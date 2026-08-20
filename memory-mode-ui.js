(() => {
'use strict';
const PATCH_VERSION='memory-mode-ui-v1';
if(document.documentElement.dataset.memoryModeUi===PATCH_VERSION)return;
document.documentElement.dataset.memoryModeUi=PATCH_VERSION;

function ensureModeOption(){
  const sel=document.getElementById('modeSel');
  if(!sel)return;
  if(!sel.querySelector('option[value="memory"]')){
    const opt=document.createElement('option');
    opt.value='memory';
    opt.textContent='暗記モード（覚えるまで周回）';
    sel.appendChild(opt);
  }
  const label=sel.closest('label');
  if(label && !document.getElementById('memoryModeHint')){
    const hint=document.createElement('small');
    hint.id='memoryModeHint';
    hint.className='memory-mode-hint';
    hint.textContent='正解かつ「自信なし」なしで覚えた判定。不正解・自信なしだけを次の周へ残します。';
    label.appendChild(hint);
  }
  updateHint();
}
function updateHint(){
  const sel=document.getElementById('modeSel');
  const hint=document.getElementById('memoryModeHint');
  if(hint)hint.hidden=!sel||sel.value!=='memory';
}
function ensureStudyStatus(){
  const view=document.getElementById('studyView');
  if(!view||document.getElementById('memoryModeStatus'))return;
  const panel=view.querySelector('.panel')||view.firstElementChild||view;
  const box=document.createElement('div');
  box.id='memoryModeStatus';
  box.className='memory-mode-status hidden';
  panel.prepend(box);
}
function ensureResultSummary(){
  const view=document.getElementById('resultView');
  if(!view||document.getElementById('memoryResultSummary'))return;
  const panel=view.querySelector('.panel')||view.firstElementChild||view;
  const box=document.createElement('div');
  box.id='memoryResultSummary';
  box.className='memory-result-summary';
  box.hidden=true;
  const anchor=panel.querySelector('#resultRate')?.closest('.result-rate') || panel.firstElementChild;
  if(anchor?.parentNode)anchor.parentNode.insertBefore(box,anchor.nextSibling);
  else panel.prepend(box);
}
function run(){ensureModeOption();ensureStudyStatus();ensureResultSummary()}
function start(){
  run();
  document.addEventListener('change',e=>{if(e.target?.id==='modeSel')updateHint()});
  const observer=new MutationObserver(run);
  observer.observe(document.body,{subtree:true,childList:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
else start();
})();
