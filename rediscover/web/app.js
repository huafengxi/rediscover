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

const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
async function voice(input,status,btn){
  const say = s => status.textContent=s;
  if(!isSecureContext){say('此地址不是安全上下文；语音不可用。可以继续键盘作答。');return;}
  if(!Speech?.available || !('processLocally' in Speech.prototype)){say('此浏览器不支持本地语音转写。可以继续键盘作答。');return;}
  btn.disabled=true;
  try{
    const ready=await Speech.available({langs:['zh-CN'],processLocally:true});
    if(ready!=='available'){say('没有可用的本地中文语音包。可以继续键盘作答。');btn.disabled=false;return;}
    const r=new Speech();r.lang='zh-CN';r.processLocally=true;r.interimResults=false;r.maxAlternatives=1;
    r.onstart=()=>say('正在听……');
    r.onresult=e=>{input.value=e.results[e.resultIndex][0].transcript;input.focus();say('请核对并修改转写，再点提交。列式时请确认数字、括号和运算符。');};
    r.onerror=()=>say('未能完成本地转写，请重试或用键盘。');
    r.onend=()=>{btn.disabled=false;if(status.textContent==='正在听……')say('没听清，请重试或用键盘。');};r.start();
  }catch(e){btn.disabled=false;say('本地转写不可用，请用键盘。');}
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
  data.steps.forEach((s,i)=>{
    const current=i===data.steps.length-1&&!data.completed;
    const section=el('article',null,{class:'step',id:s.id}), title=el('h2',(i+1)+' · '+s.title,{tabindex:'-1'});section.append(title);
    if(s.prediction)section.append(makeAnswer(s.prediction,'我当时写下：'));
    const body=el('div');body.innerHTML=s.html;section.append(body);
    if(s.figure){const f=el('figure');f.append(el('img',null,{src:s.figure.url,alt:s.figure.caption}),el('figcaption',s.figure.caption));section.append(f);}
    const q=s.question;
    if(q&&!current)section.append(el('p',q.prompt,{class:'note'}));
    for(const a of s.attempts){const b=makeAnswer(a,'作答：');b.append(el('p',a.feedback));section.append(b);}
    if(s.solution){const solution=el('div',null,{class:'solution'});solution.innerHTML=s.solution;section.append(solution);}
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
        if(q.kind==='expression'){input.setAttribute('spellcheck','false');input.setAttribute('placeholder','例：4 × (2 + 1)');}
        form.append(el('label',q.prompt,{for:'response'}),input);
        if(q.unit){unit=el('input',null,{id:'unit',maxlength:'32',placeholder:q.unit});form.append(el('label','单位',{for:'unit'}),unit);}
        actions.append(button('提交',false,'submit'));
        const mic=button('语音转写',true);mic.onclick=()=>voice(input,voiceNote,mic);actions.append(mic);
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
