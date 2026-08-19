(() => {
'use strict';

function splitQuestion(text){
  const source=String(text||'');
  const re=/(^|[^A-Za-z0-9Ａ-Ｚａ-ｚ])([a-eA-Eａ-ｅＡ-Ｅ])\s*[．.]\s*/g;
  const matches=[];
  let m;
  while((m=re.exec(source))!==null){
    const letter=m[2].normalize('NFKC').toLowerCase();
    const prefix=m[1]||'';
    matches.push({letter,start:m.index+prefix.length,end:re.lastIndex});
  }
  const first=matches.findIndex(x=>x.letter==='a');
  if(first<0) return {stem:source,items:[]};
  const seq=[];
  let expected='a';
  for(let i=first;i<matches.length;i++){
    const x=matches[i];
    if(x.letter!==expected) break;
    seq.push(x);
    expected=String.fromCharCode(expected.charCodeAt(0)+1);
    if(expected>'e') break;
  }
  if(seq.length<4) return {stem:source,items:[]};
  const stem=source.slice(0,seq[0].start).trim();
  const items=seq.map((x,i)=>{
    const end=i+1<seq.length?seq[i+1].start:source.length;
    return {letter:x.letter,text:source.slice(x.end,end).trim()};
  });
  return {stem,items};
}

function ensureQuestionLayout(){
  const q=document.getElementById('questionText');
  const choices=document.getElementById('choices');
  if(!q||!choices) return null;

  let qLabel=document.getElementById('displayQuestionLabel');
  if(!qLabel){
    qLabel=document.createElement('div');
    qLabel.id='displayQuestionLabel';
    qLabel.className='display-section-label';
    qLabel.textContent='問題文';
    q.parentNode.insertBefore(qLabel,q);
  }

  let sub=document.getElementById('displayQuestionSubitems');
  if(!sub){
    sub=document.createElement('div');
    sub.id='displayQuestionSubitems';
    sub.className='display-question-subitems';
    q.insertAdjacentElement('afterend',sub);
  }

  let aLabel=document.getElementById('displayAnswerLabel');
  if(!aLabel){
    aLabel=document.createElement('div');
    aLabel.id='displayAnswerLabel';
    aLabel.className='display-section-label display-answer-label';
    aLabel.textContent='解答選択肢';
    choices.parentNode.insertBefore(aLabel,choices);
  }
  return {q,sub};
}

function updateQuestion(){
  const parts=ensureQuestionLayout();
  if(!parts) return;
  const {q,sub}=parts;
  const source=q.textContent||'';
  if(q.dataset.displayStem===source) return;

  const parsed=splitQuestion(source);
  q.dataset.displayStem=parsed.stem;
  if(parsed.items.length){
    q.textContent=parsed.stem;
    sub.textContent='';
    parsed.items.forEach(item=>{
      const row=document.createElement('div');
      row.className='display-question-subitem';
      const letter=document.createElement('span');
      letter.className='display-subitem-letter';
      letter.textContent=item.letter+'.';
      const body=document.createElement('span');
      body.textContent=item.text;
      row.append(letter,body);
      sub.appendChild(row);
    });
    sub.hidden=false;
  }else{
    sub.textContent='';
    sub.hidden=true;
  }
}

function updateExamReview(root=document){
  root.querySelectorAll('.exam-review-item .q').forEach(el=>{
    if(el.dataset.displayFormatted==='1') return;
    const source=el.textContent||'';
    const parsed=splitQuestion(source);
    if(!parsed.items.length) return;
    el.textContent=parsed.stem;
    const box=document.createElement('div');
    box.className='display-review-subitems';
    parsed.items.forEach(item=>{
      const row=document.createElement('div');
      row.textContent=`${item.letter}. ${item.text}`;
      box.appendChild(row);
    });
    el.appendChild(box);
    el.dataset.displayFormatted='1';
  });
}

function setDetailsState(root){
  if(!root) return;
  root.querySelectorAll('details').forEach(detail=>{
    const label=(detail.querySelector('summary')?.textContent||'').trim();
    detail.open=!label.includes('根拠資料');
  });
}

function expandVisibleExplanation(){
  const panel=document.getElementById('feedbackPanel');
  if(panel && !panel.classList.contains('hidden')) setDetailsState(panel);

  const exam=document.getElementById('examReview');
  if(exam && !exam.classList.contains('hidden')) setDetailsState(exam);
}

function scheduleExpand(){
  requestAnimationFrame(()=>{
    requestAnimationFrame(expandVisibleExplanation);
  });
  setTimeout(expandVisibleExplanation,0);
  setTimeout(expandVisibleExplanation,80);
}

function run(){
  updateQuestion();
  updateExamReview();
}

function start(){
  run();

  const panel=document.getElementById('feedbackPanel');
  if(panel){
    const panelObserver=new MutationObserver(mutations=>{
      if(mutations.some(x=>x.type==='attributes' && x.attributeName==='class')) scheduleExpand();
    });
    panelObserver.observe(panel,{attributes:true,attributeFilter:['class']});
  }

  const bodyObserver=new MutationObserver(()=>run());
  bodyObserver.observe(document.body,{subtree:true,childList:true,characterData:true});

  document.addEventListener('click',e=>{
    if(e.target.closest('#submitBtn')) scheduleExpand();
  },true);

  document.addEventListener('keydown',e=>{
    if(e.key==='Enter') scheduleExpand();
  },true);

  scheduleExpand();
}

if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
else start();
})();
