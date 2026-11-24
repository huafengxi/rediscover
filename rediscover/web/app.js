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
  main.replaceChildren(el('p','从地面丈量到月面返航',{class:'eyebrow'}),el('h1','重走发现之路'),el('p','先猜会发生什么，再打开证据。每篇课文逐步展开，重载时从上次停下的地方继续。'));
  const jump=el('nav',null,{class:'jump','aria-label':'主线'});main.append(jump);
  for(const [g,group] of Object.entries(data.groups)){
    const rows=data.courses.filter(c=>c.id[0]===g);if(!rows.length)continue;
    jump.append(el('a',g,{href:'#line-'+g,'aria-label':group.title}));
    const s=el('section',null,{id:'line-'+g}), list=el('ol',null,{class:'list'});s.append(el('h2',g+' · '+group.title+'（'+rows.length+'）'),list);main.append(s);
    for(const c of rows){const a=el('a',c.id+' '+c.title,{href:base+c.id+'/'});a.append(el('small',c.goal));const l=el('li');l.append(a);list.append(l);}
  }
  main.append(el('p','版本 '+data.release,{class:'note'}));
}
function showCourse(data,focus){
  main.replaceChildren(el('p','发现关 '+data.id,{class:'eyebrow'}),el('h1',data.title),el('p','已展开 '+data.steps.length+' / '+data.total,{class:'note','aria-live':'polite'}));
  document.title=data.id+' '+data.title+' · Rediscover';
  const makeAnswer=(a,label)=>{const box=el('div',null,{class:'answer'});box.append(el('p',label+ (a.skipped?'暂时想不出（已略过）':a.answer+(a.unit?' '+a.unit:''))));return box;};
  const showSolution=(section,html)=>{const box=el('div',null,{class:'solution',tabindex:'-1'});box.innerHTML=html;section.append(box);return box;};
  data.steps.forEach((s,i)=>{
    const current=i===data.steps.length-1&&!data.completed;
    const section=el('article',null,{class:'step',id:s.id}), title=el('h2',(i+1)+' · '+s.title,{tabindex:'-1'});section.append(title);
    if(s.prediction)section.append(makeAnswer(s.prediction,'我当时写下：'));
    const body=el('div');body.innerHTML=s.html;section.append(body);
    if(s.figure){const f=el('figure');f.append(el('img',null,{src:s.figure.url,alt:s.figure.caption}),el('figcaption',s.figure.caption));section.append(f);}
    const q=s.question;
    if(q&&!current)section.append(el('p',q.prompt,{class:'note'}));
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
        const fields={action,step:s.id,version:data.version,answer:action==='submit'?input?.value:'',unit:action==='submit'?unit?.value:''};
        if(!pending || pending.signature!==JSON.stringify(fields))pending={signature:JSON.stringify(fields),data:{...fields,key:token()}};
        inFlight=true;status.textContent='正在保存……';for(const b of actions.children)b.disabled=true;
        try{const result=await request('api/course/'+data.id+'/action',pending.data);showCourse(result,result.steps.at(-1).id);}
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
  if(focus)document.getElementById(focus)?.querySelector('h2')?.focus();
}
async function start(){
  const id=location.pathname.match(/^\/rediscover\/([A-N]\d\d)\/$/)?.[1];
  try{if(id)showCourse(await request('api/course/'+id));else showCatalog(await request('api/catalog'));}
  catch(e){main.replaceChildren(el('h1','未能打开'),el('p',e.message),el('a','重新加载',{href:location.pathname}));}
}
start();
