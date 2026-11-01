'use strict';
// Original CIT scenes adapted from the composition/interaction patterns of Oryzo's first two sections.
const campusRules=[
 ['Exactly once','Every teaching session receives one day, one start period and one room.','ONE SESSION','ONE PLACE'],
 ['Faculty','A faculty member cannot teach two sessions at the same time.','ONE FACULTY','ONE CLASS'],
 ['Student groups','Combined lectures occupy every constituent group. Only sessions in the same elective basket share a group slot.','EVERY GROUP','ACCOUNTED FOR'],
 ['Rooms','A room cannot host two sessions or approved events at the same time.','ONE ROOM','ONE BOOKING'],
 ['Capacity','Attendance must fit the room. Midsem exams use floor(physical capacity ÷ 2).','EXAM SEATS','CAPACITY ÷ 2'],
 ['Room type','A session goes into the kind of room it needs. A physics lab belongs in a physics laboratory.','THE RIGHT LAB','FOR THE SUBJECT'],
 ['Faculty leave','Faculty unavailability is respected when creating or repairing the timetable.','FACULTY LEAVE','TIME PROTECTED'],
 ['Maintenance','Room closures and maintenance windows remove unavailable spaces from the calendar.','MAINTENANCE','SPACE PROTECTED'],
 ['Lunch & labs','Lunch is 13:00–14:00. Three-hour teaching labs run only P2–P4 or P6–P8.','13:00—14:00','LUNCH STAYS FREE'],
 ['Accessibility','A session that requires an accessible room must receive an accessible room.','ACCESSIBLE','BY REQUIREMENT'],
 ['Electives','Every session in the same elective basket starts on the same day and period.','ELECTIVE BASKET','SAME START'],
 ['Daily load','Teaching load is measured in hours. Faculty daily limits are enforced by code.','TEACHING HOURS','WITHIN LIMIT'],
 ['Venue bookings','Approved bookings cannot clash with a class, another approved booking or a mandatory student group.','CLASSES + EVENTS','SHARED CALENDAR'],
 ['Fixed slots','A session with an original fixed slot remains locked to that day, period and specified room.','FIXED MEANS','FIXED']
];
let chapterAnimation=0;
const storyRoot=document.getElementById('introduction');
storyRoot.className='introduction oryzo-story';
storyRoot.innerHTML=`
 <nav class="story-nav" aria-label="Campus introduction"><a href="#campus-opening" class="story-logo"><img src="/static/assets/cit-scheduler-mark.png" alt=""><span class="story-logo-copy"><b>CIT</b><small>CHRONOGRID</small></span></a><div class="story-nav-actions"><a href="#campus-opening">01 / THE CAMPUS</a><a href="#campus-rules">02 / THE RULES</a><button class="story-enter" data-enter-campus>ENTER WORKSPACE ↗</button></div></nav>
 <aside class="story-rail" aria-label="Introduction progress"><span>CIT / ACADEMIC OPERATIONS</span><div class="story-progress"><i id="story-progress-fill"></i></div><a href="#campus-opening" aria-label="First section">01</a><a href="#campus-rules" aria-label="Second section">02</a></aside>
 <section id="campus-opening" class="story-panel opening-panel" aria-labelledby="story-title">
  <div class="desk-surface" aria-hidden="true"></div><div class="desk-mat" aria-hidden="true"><span>CIT / CAMPUS PLANNING STUDIO</span></div>
  <p class="opening-tagline">FOR EVERY CLASS. FOR EVERY CAMPUS MOMENT.</p>
  <h1 id="story-title">CHRONO<span>GRID</span><small>THE CAMPUS, IN SYNC.</small></h1>
  <div class="planner-stage" id="planner-stage"><div class="planner-shadow"></div><div class="academic-planner" id="academic-planner" role="img" aria-label="Interactive illustrative academic planner. Use the Week 7 and Week 8 buttons to change the calendar scene.">
   <div class="planner-cover"></div><div class="planner-paper"><div class="planner-binding"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><div class="planner-paper-head"><b>CIT</b><span>THE ACADEMIC WEEK</span><strong id="planner-week-number">07</strong></div><div class="planner-line"></div><div class="planner-headings"><span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span></div><div class="planner-grid" id="illustrative-grid"></div><div class="planner-lunch">13:00—14:00 / LUNCH</div><div class="planner-afterhours"><span>AFTER THE FINAL LECTURE</span><b id="planner-event">SPECTRA / 18:00—22:00</b></div><div class="planner-paper-foot"><span>LEARN · GATHER · GROW</span><span>CHILIKA INSTITUTE OF TECHNOLOGY</span></div></div>
  </div><div class="planner-week-switch" aria-label="Illustrative calendar"><button data-story-week="7" aria-controls="illustrative-grid" aria-pressed="true">WEEK 07</button><button data-story-week="8" aria-controls="illustrative-grid" aria-pressed="false">WEEK 08</button></div><span class="planner-hint">MOVE YOUR POINTER TO EXPLORE · ILLUSTRATIVE PLANNER</span></div>
  <button type="button" class="desk-pencil" id="interactive-pencil" aria-label="Interactive pencil. Drag to move. Arrow keys move, Space rotates, Escape resets." title="Drag to move · Space to rotate · Double-click to reset"><i></i></button><span class="pencil-guide">DRAG THE PENCIL ↗</span><span id="pencil-status" class="sr-only" aria-live="polite"></span><div class="desk-clip" aria-hidden="true"></div><div class="desk-note" aria-hidden="true">Spectra<br><span>is almost here.</span><i>Don't double-book<br>the auditorium.</i></div>
  <div class="opening-story"><span class="story-overline">01 / THE WEEK EVERYTHING MEETS</span><h2>Classes. Spectra.<br>Midsems.<br><em>Room for it all.</em></h2><p>Week 7 brings regular classes and the annual tech fest into the same campus spaces. Week 8 brings exams. ChronoGrid brings the calendar together.</p><a href="#campus-rules">DISCOVER THE RULES <span>↓</span></a></div>
  <div class="opening-note"><span>CHILIKA INSTITUTE<br>OF TECHNOLOGY</span><div class="note-divider"></div><p>Classes, exams & venue requests.<br>English / Hinglish. Admin approval.</p><button data-enter-campus>OPEN THE COMMAND CENTRE ↗</button></div>
  <div class="opening-bottom"><div id="intro-metrics" class="story-live-metrics" aria-label="Loaded dataset counts"></div><span id="intro-source">LOADING DATASET PROVENANCE…</span><a href="#campus-rules" class="scroll-cue">SCROLL TO EXPLORE <span>↓</span></a></div>
 </section>
 <section id="campus-rules" class="story-panel rules-panel" aria-labelledby="rules-story-title">
  <div class="rules-grain" aria-hidden="true"></div><div class="rules-intro"><span class="story-overline">02 / THE RULES THAT MAKE ROOM</span><p>A campus is more than a grid.<br>Every slot belongs to people.</p></div>
  <h2 id="rules-story-title">A little order.<span>A lot of possibility.</span></h2>
  <div class="rule-object-stage" id="rule-object-stage"><div class="rule-orbit orbit-one"></div><div class="rule-orbit orbit-two"></div><div class="rule-object" id="rule-object"><div class="rule-object-edge"></div><div class="rule-object-face"><span class="rule-object-caption">CIT / THE CONSTRAINT SYSTEM</span><div class="rule-object-number" id="rule-object-number">09</div><div class="rule-object-line"></div><b id="rule-object-title">13:00—14:00</b><span id="rule-object-subtitle">LUNCH STAYS FREE</span><div class="rule-object-periods"><i>P2</i><i>P3</i><i>P4</i><span> / </span><i>P6</i><i>P7</i><i>P8</i></div><small>ILLUSTRATED RULE · NOT A SCHEDULE CHECK</small></div></div><div class="rule-object-caption-below">HOVER OR MOVE YOUR POINTER · SELECT A RULE BELOW</div></div>
  <div class="rule-detail" aria-live="polite"><span class="story-overline" id="rule-label">HARD CONSTRAINT 09 / 14</span><h3 id="rule-detail-title">Protect the pause.</h3><p id="rule-detail-copy">Lunch is 13:00–14:00. Three-hour teaching labs run only P2–P4 or P6–P8.</p><div class="golden-rule"><span>✦ AI INTERPRETS</span><span>▦ PYTHON VALIDATES</span><span>↗ PEOPLE APPROVE</span></div><button class="story-enter dark-enter" data-enter-campus>SEE IT IN THE WORKSPACE ↗</button></div>
  <div class="rule-selector" aria-label="Explore the fourteen hard constraints">${campusRules.map((rule,i)=>`<button data-campus-rule="${i}" aria-pressed="${i===8}"><span>${String(i+1).padStart(2,'0')}</span>${rule[0]}</button>`).join('')}</div>
  <div class="rules-bottom"><span>MON—FRI / P1—P9 ACADEMIC / P10—P13 EVENTS</span><span>14 HARD RULES · 6 SOFT OBJECTIVES</span><button data-enter-campus>ENTER CHRONOGRID ↗</button></div>
 </section>`;

function drawIllustrativeWeek(week){
 const labels=week===7?['LECTURE','DESIGN LAB','TUTORIAL','PHYSICS','ELECTIVE','CIRCUITS','PROJECT','MECHANICS']:['MIDSEM','EXAM','MIDSEM','EXAM','MIDSEM','EXAM'];
 const colors=week===7?['blue','sage','yellow','blue','sage','blue','yellow','sage']:['blue','yellow','blue','yellow','blue','yellow'];
 document.getElementById('illustrative-grid').innerHTML=Array.from({length:25},(_,i)=>[0,3,6,10,12,17,20,23].includes(i)?`<div class="paper-session ${colors[[0,3,6,10,12,17,20,23].indexOf(i)%colors.length]}"><span>${labels[[0,3,6,10,12,17,20,23].indexOf(i)%labels.length]}</span><small>${week===7?'CIT / TEACHING':'W08 / EXAMS'}</small></div>`:'<div></div>').join('');
 document.getElementById('planner-week-number').textContent=week==='8'||week===8?'08':'07';
 document.getElementById('planner-event').textContent=week===7?'SPECTRA / 18:00—22:00':'EXAM CAPACITY / PHYSICAL SEATS ÷ 2';
 storyRoot.querySelectorAll('[data-story-week]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.storyWeek)===week)));
 document.getElementById('academic-planner').classList.toggle('exam-calendar',week===8);
}
drawIllustrativeWeek(7);

storyRoot.addEventListener('click',async event=>{
 const week=event.target.closest('[data-story-week]');if(week)drawIllustrativeWeek(Number(week.dataset.storyWeek));
 const ruleButton=event.target.closest('[data-campus-rule]');
 if(ruleButton){
  const index=Number(ruleButton.dataset.campusRule),rule=campusRules[index];
  document.getElementById('rule-object-number').textContent=String(index+1).padStart(2,'0');
  document.querySelector('.rule-object-periods').innerHTML=index===8?'<i>P2</i><i>P3</i><i>P4</i><span> / </span><i>P6</i><i>P7</i><i>P8</i>':index===4?'<i>PHYSICAL SEATS</i><span> ÷ </span><i>2</i>':'<i>HARD CONSTRAINT</i><span> / </span><i>'+String(index+1).padStart(2,'0')+'</i>';
  document.getElementById('rule-object-title').textContent=rule[2];document.getElementById('rule-object-subtitle').textContent=rule[3];
  document.getElementById('rule-label').textContent=`HARD CONSTRAINT ${String(index+1).padStart(2,'0')} / 14`;
  document.getElementById('rule-detail-title').textContent=index===8?'Protect the pause.':rule[0]+'. By design.';
  document.getElementById('rule-detail-copy').textContent=rule[1];
  storyRoot.querySelectorAll('[data-campus-rule]').forEach(button=>button.setAttribute('aria-pressed',String(button===ruleButton)));
 }
 if(event.target.closest('[data-enter-campus]')){
  cancelAnimationFrame(chapterAnimation);location.assign('/workspace');return;
 }
});
const reduceStoryMotion=matchMedia('(prefers-reduced-motion: reduce)');
for(const [stageId,objectId] of [['planner-stage','academic-planner'],['rule-object-stage','rule-object']]){
 const stage=document.getElementById(stageId),object=document.getElementById(objectId);
 stage.addEventListener('pointermove',event=>{if(reduceStoryMotion.matches||event.pointerType==='touch')return;const box=stage.getBoundingClientRect();object.style.setProperty('--pointer-x',((event.clientX-box.left)/box.width-.5).toFixed(3));object.style.setProperty('--pointer-y',((event.clientY-box.top)/box.height-.5).toFixed(3))});
 stage.addEventListener('pointerleave',()=>{object.style.setProperty('--pointer-x',0);object.style.setProperty('--pointer-y',0)});
}
let storyFrame=false;
function updateStoryScroll(){
 const bounds=storyRoot.getBoundingClientRect(),height=innerHeight;
 const progress=Math.max(0,Math.min(1,-bounds.top/Math.max(1,bounds.height-height)));
 storyRoot.style.setProperty('--story-progress',progress.toFixed(3));
 const first=document.getElementById('campus-opening').getBoundingClientRect();const firstProgress=Math.max(0,Math.min(1,-first.top/first.height));
 storyRoot.style.setProperty('--scene-blend',Math.max(0,Math.min(1,(firstProgress-.55)/.45)).toFixed(3));
 const ruleTop=document.getElementById('campus-rules').getBoundingClientRect().top;storyRoot.style.setProperty('--rule-reveal',Math.max(0,Math.min(1,1-ruleTop/height)).toFixed(3));
 document.getElementById('story-progress-fill').style.height=(progress*100)+'%';
 storyRoot.classList.toggle('viewing-rules',document.getElementById('campus-rules').getBoundingClientRect().top<height*.4);
 if(!reduceStoryMotion.matches)storyRoot.style.setProperty('--hero-scroll',Math.max(0,Math.min(1,-bounds.top/height)).toFixed(3));
 storyFrame=false;
}
window.addEventListener('scroll',()=>{if(!storyFrame&&!storyRoot.classList.contains('hidden')){storyFrame=true;requestAnimationFrame(updateStoryScroll)}},{passive:true});
window.addEventListener('resize',updateStoryScroll);updateStoryScroll();
document.getElementById('application').classList.add('hidden');storyRoot.classList.remove('hidden');
document.getElementById('template-overview').onclick=()=>{document.getElementById('application').classList.add('hidden');storyRoot.classList.remove('hidden');history.replaceState(null,'','#campus-opening');window.scrollTo(0,0)};
if(location.pathname==='/workspace'){storyRoot.classList.add('hidden');document.getElementById('application').classList.remove('hidden');if(matchMedia('(max-width:1200px)').matches){document.querySelector('.workspace').classList.add('copilot-collapsed');$('toggle-copilot').setAttribute('aria-expanded','false')}refresh().catch(showError)}else if(location.hash==='#workspace'){location.replace('/workspace')}

fetch('/api/overview').then(response=>{if(!response.ok)throw Error('Dataset unavailable');return response.json()}).then(data=>{
 document.getElementById('intro-metrics').innerHTML=[[data.students,'STUDENTS'],[data.rooms,'CAMPUS SPACES'],[data.sessions,'TEACHING SESSIONS'],[data.exams,'MIDSEM EXAMS']].map(([value,label])=>`<div><strong>${E(value)}</strong><span>${label}</span></div>`).join('');
 document.getElementById('intro-source').textContent=data.synthetic?'SYNTHETIC DEVELOPMENT DATA · OFFICIAL STARTER PACK PENDING':'LOADED DEVELOPMENT SCHEMA · OFFICIAL COMPATIBILITY UNVERIFIED';
}).catch(()=>document.getElementById('intro-source').textContent='DATASET UNAVAILABLE · ENTER WORKSPACE TO RECONNECT');

const storyLogout=document.getElementById('logout').onclick;
document.getElementById('logout').onclick=async()=>{await api('logout',{});state=null;location.assign('/login')};

// Smooth chapter navigation, with normal wheel/touch scrolling left under the visitor's control.
function goToStoryChapter(target){
 cancelAnimationFrame(chapterAnimation);
 const start=scrollY,end=target.getBoundingClientRect().top+scrollY;
 history.replaceState(null,'','#'+target.id);
 if(reduceStoryMotion.matches){window.scrollTo(0,end);updateStoryScroll();return}
 const started=performance.now(),duration=Math.min(1250,Math.max(650,Math.abs(end-start)*.7));
 function frame(now){const t=Math.min(1,(now-started)/duration);const eased=t<.5?4*t*t*t:1-Math.pow(-2*t+2,3)/2;window.scrollTo(0,start+(end-start)*eased);if(t<1)chapterAnimation=requestAnimationFrame(frame);else updateStoryScroll()}
 chapterAnimation=requestAnimationFrame(frame);
}
storyRoot.addEventListener('click',event=>{const link=event.target.closest('a[href^="#campus-"]');if(!link)return;const target=document.getElementById(link.getAttribute('href').slice(1));if(target){event.preventDefault();goToStoryChapter(target)}});
for(const name of ['wheel','touchstart'])window.addEventListener(name,()=>cancelAnimationFrame(chapterAnimation),{passive:true});
const pencil=document.getElementById('interactive-pencil');
let pencilX=0,pencilY=0,pencilAngle=0,pencilDrag=null,pencilMoved=false;
function paintPencil(){pencil.style.setProperty('--pencil-x',pencilX+'px');pencil.style.setProperty('--pencil-y',pencilY+'px');pencil.style.setProperty('--pencil-angle',pencilAngle+'deg')}
function resetPencil(){pencilX=0;pencilY=0;pencilAngle=0;paintPencil();document.getElementById('pencil-status').textContent='Pencil reset to its original position.'}
pencil.addEventListener('pointerdown',event=>{event.preventDefault();pencil.focus({preventScroll:true});pencil.setPointerCapture(event.pointerId);pencilDrag={x:event.clientX,y:event.clientY,startX:pencilX,startY:pencilY};pencilMoved=false;pencil.classList.add('is-dragging')});
pencil.addEventListener('pointermove',event=>{if(!pencilDrag)return;const dx=event.clientX-pencilDrag.x,dy=event.clientY-pencilDrag.y;const limit=Math.min(240,innerWidth*.26);pencilX=Math.max(-limit,Math.min(limit,pencilDrag.startX+dx));pencilY=Math.max(-140,Math.min(260,pencilDrag.startY+dy));if(Math.hypot(dx,dy)>5)pencilMoved=true;paintPencil()});
function releasePencil(event){if(!pencilDrag)return;pencilDrag=null;pencil.classList.remove('is-dragging');if(pencil.hasPointerCapture(event.pointerId))pencil.releasePointerCapture(event.pointerId);document.getElementById('pencil-status').textContent='Pencil moved. Arrow keys adjust it; Space rotates; Escape resets.'}
pencil.addEventListener('pointerup',releasePencil);pencil.addEventListener('pointercancel',releasePencil);
pencil.addEventListener('click',()=>{if(!pencilMoved){pencilAngle+=15;paintPencil()}});pencil.addEventListener('dblclick',resetPencil);
pencil.addEventListener('keydown',event=>{const keys=['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' ','Escape','Home'];if(!keys.includes(event.key))return;event.preventDefault();if(event.key==='Escape'||event.key==='Home'){resetPencil();return}if(event.key===' '){pencilAngle+=15}else if(event.altKey){pencilAngle+=event.key==='ArrowLeft'||event.key==='ArrowUp'?-8:8}else{pencilX+=event.key==='ArrowLeft'?-12:event.key==='ArrowRight'?12:0;pencilY+=event.key==='ArrowUp'?-12:event.key==='ArrowDown'?12:0}const keyboardLimit=Math.min(240,innerWidth*.26);pencilX=Math.max(-keyboardLimit,Math.min(keyboardLimit,pencilX));pencilY=Math.max(-140,Math.min(260,pencilY));paintPencil()});
