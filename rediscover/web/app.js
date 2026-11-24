'use strict';
const main = document.querySelector('#main'), base = '/rediscover/';
const el = (tag,text,attr={})=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;for(const [k,v] of Object.entries(attr))n.setAttribute(k,v);return n;};
const button=(text,alt=false,type='button')=>el('button',text,{type,class:alt?'alt':''});
const token=()=>Array.from(crypto.getRandomValues(new Uint8Array(18)),b=>b.toString(16).padStart(2,'0')).join('');
const sleep = ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function request(path, payload){
  let res;
  const init=payload?{method:'POST',headers:{'Content-Type':'application/json','X-Rediscover':'1'},body:JSON.stringify(payload)}:{};
  for(let n=0;n<2;n++){
    try {res=await fetch(base+path,{cache:'no-store',...init});} catch(e){if(n)throw Error('连接中断；答案还在输入框，可重试。');}
    if(res && (res.ok || res.status<500 || n)) break;
    await sleep(350);
  }
  let data;try{data=await res.json();}catch(e){throw Error('服务暂不可用，请稍后重试。');}
  if(!res.ok) throw Error(data.error || '无法打开课文。');
  return data;
}

function voiceControl(input,status,actions){
  // On existing dev HTTP, use the device audio picker/recorder, never getUserMedia or a vendor speech API.
  const pick=el('input',null,{type:'file',accept:'audio/*,.webm,.m4a,.ogg,.wav,.mp3',capture:'user',hidden:'',id:'voice-file'});
  const btn=button('语音转写',true);btn.onclick=()=>{
    status.textContent='选择或录制一段中文音频（最长 20 秒、2 MB）；只在 Rediscover 所在机器转写。';pick.click();
  };
  pick.onchange=async()=>{
    const audio=pick.files?.[0];pick.value='';if(!audio)return;
    if(audio.size>2000000){status.textContent='录音不能超过 2 MB。';return;}
    const previous=input.value;btn.disabled=true;status.textContent='正在本机服务转写……';
    try{
      const res=await fetch(base+'api/transcribe',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Rediscover':'1'},body:audio});
      const d=await res.json();if(!res.ok)throw Error(d.error || '转写失败。');
      if(input.value===previous)input.value=d.text;else input.setRangeText(d.text,input.selectionStart,input.selectionEnd,'end');
      input.focus();status.textContent='请核对并修改转写，再点提交。列式请确认数字、括号和运算符。';
    }catch(e){status.textContent=(e.message || '转写连接中断。')+' 输入没有提交；可重试或用键盘。';}
    finally{btn.disabled=false;}
  };
  actions.append(btn,pick);
}

function showCatalog(data){
  main.replaceChildren(el('p','从地面丈量到月面返航',{class:'eyebrow'}),el('h1','重走发现之路'),el('p','从一个问题出发，顺着图和证据读到结论。想先动手预测、列式或解释，可以切到答题模式。'));
  const jump=el('nav',null,{class:'jump','aria-label':'主线'});main.append(jump);
  for(const [g,group] of Object.entries(data.groups)){
    const rows=data.courses.filter(c=>c.id[0]===g);if(!rows.length)continue;
    jump.append(el('a',g,{href:'#line-'+g,'aria-label':group.title}));
    const s=el('section',null,{id:'line-'+g}), list=el('ol',null,{class:'list'});s.append(el('h2',g+' · '+group.title+'（'+rows.length+'）'),list);main.append(s);
    for(const c of rows){const a=el('a',c.id+' '+c.title,{href:base+c.id+'/'});a.append(el('small',c.goal));const l=el('li');l.append(a);list.append(l);}
  }
  main.append(el('p','版本 '+data.release,{class:'note'}));
}
function courseHeader(data,mode){
  const nav=el('nav',null,{class:'mode-nav','aria-label':'课文模式'});
  const path=base+data.id+'/';
  for(const [key,label,href] of [['read','阅读模式',path],['quiz','答题模式',path+'?mode=quiz']]){
    nav.append(el('a',label,{href,...(mode===key?{'aria-current':'page'}:{})}));
  }
  main.replaceChildren(el('p','发现关 '+data.id,{class:'eyebrow'}),el('h1',data.title),nav);
  document.title=data.id+' '+data.title+' · Rediscover';
}
function showSolution(section,html,reading=false){
  const box=el('div',null,{class:reading?'reading-solution':'solution',tabindex:'-1'});
  box.innerHTML=html;section.append(box);return box;
}
function showBody(section,s){
  const body=el('div');body.innerHTML=s.html;section.append(body);
  if(s.figure){
    const f=el('figure',null,s.figure.diagram?{class:'diagram'}:{});
    f.append(el('img',null,{src:s.figure.url,alt:s.figure.alt}),el('figcaption',s.figure.caption));section.append(f);
  }
}
function showReading(data){
  courseHeader(data,'read');
  const article=el('article',null,{class:'reading','aria-label':data.title});
  main.append(article);
  function append(view,from=0){
    for(const s of view.steps.slice(from)){
      const section=el('section',null,{class:'read-step',id:s.id});
      section.append(el('h2',s.title,{tabindex:'-1'}));showBody(section,s);
      if(s.question)section.append(el('p',s.question.prompt,{class:'reflection'}));
      if(s.solution)showSolution(section,s.solution,true);
      article.append(section);
    }
    if(view.gate){
      const pause=el('div',null,{class:'reading-gate'}), reveal=button(view.gate.label), status=el('p','',{role:'status',class:'error note'});
      reveal.onclick=async()=>{
        reveal.disabled=true;
        try{
          const next=await request('api/read/'+view.id+'/action',{version:view.version,step:view.gate.id});
          pause.remove();append(next,view.steps.length);
          document.getElementById(view.gate.id)?.querySelector('h2').focus();
        }catch(e){status.textContent=e.message;reveal.disabled=false;}
      };
      pause.append(reveal,status);article.append(pause);
    }else article.append(el('a','返回课程目录',{href:base,class:'reading-end'}));
  }
  append(data);
}
function showCourse(data){
  courseHeader(data,'quiz');
  main.append(el('p','已展开 '+data.steps.length+' / '+data.total,{class:'note','aria-live':'polite'}));
  const makeAnswer=(a,label)=>{const box=el('div',null,{class:'answer'});box.append(el('p',label+ (a.skipped?'暂时想不出（已略过）':a.answer+(a.unit?' '+a.unit:''))));return box;};
  data.steps.forEach((s,i)=>{
    const current=i===data.steps.length-1&&!data.completed;
    const section=el('article',null,{class:'step',id:s.id}), title=el('h2',(i+1)+' · '+s.title,{tabindex:'-1'});section.append(title);
    if(s.prediction)section.append(makeAnswer(s.prediction,'我当时写下：'));
    showBody(section,s);
    const q=s.question;
    if(q&&!current)section.append(el('p',q.prompt,{class:'note'}));
    if(q?.hints?.length){
      const hints=el('ol',null,{class:'hints','aria-label':'已查看的提示'});
      for(const hint of q.hints)hints.append(el('li',hint));
      section.append(hints);
    }
    for(const a of s.attempts){const b=makeAnswer(a,'作答：');b.append(el('p',a.feedback));section.append(b);}
    if(s.solution)showSolution(section,s.solution);
    else if(!current&&q?.canReveal){
      const reveal=button(q.kind==='expression'?'查看本步推导':'查看本步作者解释',true), status=el('p','',{role:'status',class:'error note'});
      const key=token();reveal.onclick=async()=>{
        reveal.disabled=true;
        try{const v=await request('api/course/'+data.id+'/action',{key,step:s.id,version:data.version,action:'reveal'});const opened=v.steps.find(step=>step.id===s.id);reveal.remove();status.remove();showSolution(section,opened.solution).focus();}
        catch(e){status.textContent=e.message;reveal.disabled=false;}
      };section.append(reveal,status);
    }
    if(current){
      const form=el('form'), status=el('p','',{role:'status',class:'error'}), voiceNote=el('p','',{role:'status',class:'note'}), actions=el('div',null,{class:'actions'});
      let input,unit,inFlight=false,pending=null;
      async function send(action){
        if(inFlight)return;
        const draft=input?.value, draftUnit=unit?.value;
        const fields={action,step:s.id,version:data.version,answer:action==='submit'?draft:'',unit:action==='submit'?draftUnit:''};
        if(!pending || pending.signature!==JSON.stringify(fields))pending={signature:JSON.stringify(fields),data:{...fields,key:token()}};
        inFlight=true;status.textContent='正在保存……';for(const b of actions.children)b.disabled=true;
        try{
          const result=await request('api/course/'+data.id+'/action',pending.data);
          showCourse(result);
          const ownStep=document.getElementById(s.id);
          if(action==='hint'&&ownStep?.querySelector('#response')){
            ownStep.querySelector('#response').value=draft;
            if(unit)ownStep.querySelector('#unit').value=draftUnit;
          }
          // If this answer exposes a derivation, read it before moving to the next prompt.
          const solution=result.steps.find(step=>step.id===s.id)?.solution;
          const target=solution&&!s.solution?ownStep?.querySelector('.solution'):
            action==='hint'?ownStep?.querySelector('.hints li:last-child'):
            document.getElementById(result.steps.at(-1).id)?.querySelector('h2');
          if(target){target.tabIndex=-1;target.focus();}
        }
        catch(e){status.textContent=e.message;for(const b of actions.children)b.disabled=false;inFlight=false;}
      }
      if(q){
        input=el('textarea',null,{id:'response',rows:'2',maxlength:q.kind==='expression'?'200':'1000',required:''});
        const previous=s.attempts.at(-1);if(previous&&!previous.ok)input.value=previous.answer;
        if(q.kind==='expression'){input.setAttribute('spellcheck','false');input.setAttribute('placeholder','例：4 × (2 + 1)');}
        form.append(el('label',q.prompt,{for:'response'}),input);
        if(q.unit){unit=el('input',null,{id:'unit',maxlength:'32',placeholder:q.unit});if(previous&&!previous.ok)unit.value=previous.unit;form.append(el('label','单位',{for:'unit'}),unit);}
        actions.append(button('提交',false,'submit'));
        if(data.speech)voiceControl(input,voiceNote,actions);
        if(q.kind==='prediction'){const skip=button('暂时想不出',true);skip.onclick=()=>send('skip');actions.append(skip);}
        if(q.canHint){const hint=button(q.hints.length?'下一条提示':'查看提示',true);hint.onclick=()=>send('hint');actions.append(hint);}
        if(q.canReveal){const reveal=button(q.kind==='expression'?'查看推导':'查看作者解释',true);reveal.onclick=()=>send('reveal');actions.append(reveal);}
        form.onsubmit=e=>{e.preventDefault();send('submit');};
      }else{
        const next=button(i+1===data.total?'完成本关':'继续');next.onclick=()=>send('continue');actions.append(next);
      }
      form.append(actions,voiceNote,status);section.append(form);
    }
    main.append(section);
  });
  if(data.completed)main.append(el('p','本关已完成。可以重读以上记录。',{class:'complete'}),el('a','返回课程目录',{href:base}));
}
// Position belongs to this tab, course version and mode, not to the answer record.
// Browsers without sessionStorage can still read and submit normally.
async function preservePosition(data,mode){
  const key=`rd:position:${data.id}:${data.version}:${mode}`;
  const remember=()=>{try{sessionStorage.setItem(key,String(window.scrollY));}catch{}};
  let y=0;
  try{y=Number(sessionStorage.getItem(key))||0;}catch{}
  main.addEventListener('click',event=>{if(event.target.closest('.mode-nav a'))remember();});
  const hash=location.hash.slice(1);
  if(y||hash){
    await Promise.allSettled([...document.images].map(img=>img.decode()));
    const anchor=hash&&document.getElementById(hash);
    if(anchor)anchor.scrollIntoView();else window.scrollTo(0,y);
  }
  addEventListener('pagehide',remember,{once:true});
}
async function start(){
  const id=location.pathname.match(/^\/rediscover\/([A-N]\d\d)\/$/)?.[1];
  try{
    if(!id){showCatalog(await request('api/catalog'));return;}
    history.scrollRestoration='manual';
    const quiz=new URLSearchParams(location.search).get('mode')==='quiz';
    const data=await request((quiz?'api/course/':'api/read/')+id);
    if(quiz)showCourse(data);else showReading(data);
    await preservePosition(data,quiz?'quiz':'read');
  }catch(e){main.replaceChildren(el('h1','未能打开'),el('p',e.message),el('a','重新加载',{href:location.pathname+location.search}));}
}
start();
