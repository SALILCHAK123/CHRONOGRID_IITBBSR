'use strict';
// Presentation adapter for the supplied template. Scheduling and authority stay server-owned.
Object.assign(roles,{admin:'♛ Admin (Dean)',coordinator:'▣ Dept Coord (CSE)',faculty:'▤ Faculty (Dr. Mohanty)',club:'♙ Club Rep (Robotics)',admin2:'Deputy Admin'});
for(const key of Object.keys(tabs))delete tabs[key];
Object.assign(tabs,{timetable:'▦ Master Timetable (P1–P13)',reschedule:'⇄ “Domino-Effect” Reschedule Diff',spectra:'✦ Spectra Week 7 Bookings',exams:'▤ Week 8 Midsem Exams (50% Cap)',approvals:'▣ Pending Approvals',utilisation:'◴ Room Utilisation'});

const originalRender=render;
render=function(){
 originalRender();
 const d=state.data,s=state.schedule,r=s?.report;
 const decisions=s?.bookings||[],cancelled=d.bookings.filter(b=>b.cancelled).length;
 const items=[
  ['ROOMS & VENUES',d.rooms.length,r?`${r.room_utilisation}% Util`:'Not checked',`${d.rooms.filter(x=>x.type.endsWith('_lab')).length} Labs, OAT, Audi, Halls`,'▣','blue'],
  ['FACULTY LOAD',d.faculty.length,'≤4h/day','Daily limits checked by Python','♙','green'],
  ['STUDENT GROUPS',d.groups.length,`${d.groups.reduce((n,g)=>n+g.size,0)} Stu`,`${d.courses.length} Courses / ${new Set(d.sessions.map(x=>x.basket).filter(Boolean)).size} Basket Slots`,'♟','slate'],
  ['SPECTRA WEEK 7',s?`${decisions.filter(b=>b.status==='approved').length}/${decisions.filter(b=>b.status!=='cancelled').length}`:'—','Active',`${cancelled} Cancelled, Priority 1–6`,'▤','amber'],
  ['WEEK 8 MIDSEMS',s?`${s.exams.length}/${d.exams.length}`:'—',r?.valid?'Valid':'Not checked','50% Halved Cap Enforced','▧','blue']
 ];
 $('kpis').innerHTML=items.map(([label,value,badge,note,icon,color])=>`<div class="kpi"><div><label>${E(label)}</label><strong>${E(value)} <span class="kpi-inline ${E(color)}">(${E(badge)})</span></strong><small>${E(note)}</small></div><span class="kpi-icon ${E(color)}" aria-hidden="true">${icon}</span></div>`).join('');
 $('template-telemetry').innerHTML=`<span class="pill ${r?.valid?'approved':'pending'}">● Hard: ${r?r.hard_violations:'NOT CHECKED'}</span><span class="pill pending">Soft Penalty: ${r?r.soft_penalty:'—'}</span><span class="pill">${s?s.sessions.length:'—'}/${d.sessions.length} (${d.sessions.reduce((n,x)=>n+x.duration,0)}h)</span>`;
 $('live-telemetry').textContent=r?`LOCAL INDEPENDENT VALIDATOR · ${r.utilisation.used_hours}/${r.utilisation.available_hours} eligible room-hours · Soft weights provisional · Revision ${state.revision}`:'LOCAL INDEPENDENT VALIDATOR · Not checked until generation';
 $('template-generate').disabled=state.user.role!=='admin';
};

function sessionMarkup(s,names){
 return `<div class="template-session ${s.kind==='lab'?'lab':''} ${s.basket?'elective':''}"><div class="session-top"><b>${E(s.course)}</b><span>${E(s.kind.toUpperCase())}</span></div><strong>${E(names[s.course])}</strong><small>${E(s.room)} · ${s.duration}h · ${s.size} Stu</small><small>${E(s.faculty.join(', '))}${s.fixed?' · FIXED':''}${s.basket?' · ELECTIVE':''}</small><div class="session-actions"><button type="button" data-explain="${E(s.id)}" class="explain-slot">Explain</button>${canEditTeachingSession(s)?`<button type="button" data-edit-session="${E(s.id)}" class="explain-slot">Edit</button>`:''}</div></div>`;
}

renderTimetable=function(){
 const entities=viewMode==='group'?state.data.groups:viewMode==='faculty'?state.data.faculty:state.data.rooms;
 if(!entities.some(x=>x.id===entity))entity=(viewMode==='faculty'&&state.user.faculty)||(viewMode==='group'&&entities.find(x=>x.id==='Y2-CSE')?.id)||entities[0].id;
 const selected=entities.find(x=>x.id===entity);
 const all=rows().filter(s=>viewMode==='group'?s.groups.includes(entity):viewMode==='faculty'?s.faculty.includes(entity):s.room===entity);
 const bookings=state.schedule.bookings.filter(b=>b.status==='approved'&&(viewMode==='room'?b.room===entity:viewMode==='group'?b.groups.includes(entity):false));
 const names=courses();
 const toolbar=`<div class="panel-toolbar template-filter"><div class="segmented">${['group','faculty','room'].map(m=>`<button data-view="${m}" class="${viewMode===m?'selected':''}">By ${m==='group'?'Student Group':m==='faculty'?'Faculty':`Room (${state.data.rooms.length})`}</button>`).join('')}</div><label for="entity-filter">View:</label><select id="entity-filter" aria-label="Timetable entity">${entities.map(x=>option(x.id,x.name)).join('')}</select><span class="entity-meta">${viewMode==='group'?`${selected.size} students · ${selected.department}`:viewMode==='faculty'?`Daily limit: ${selected.daily_limit}h`:`${selected.capacity} seats · ${selected.type.replaceAll('_',' ')}`}</span><button class="secondary" data-edit-timetable ${state.user.role==='club'?'disabled title="Teaching changes require Faculty, Coordinator or Admin access"':''}>Modify timetable</button></div>`;
 const columns=TIMES.slice(0,9).map((time,i)=>(i===5?'<th class="lunch-column">♜<br>LUNCH<small>13–14</small></th>':'')+`<th class="${i===8?'p9-column':''}">P${i+1}${i===8?' ⚠':''}<small>${time}–${String(Number(time.slice(0,2))+1).padStart(2,'0')}:00</small></th>`).join('');
 const grid=DAYS.map((name,day)=>{
  let cells='';
  for(let p=1;p<=9;p++){
   if(p===6)cells+='<td class="lunch-column lunch-stripes"><span>NO<br>SESSIONS</span></td>';
   const starts=all.filter(s=>s.day===day&&s.start_period===p),ongoing=all.filter(s=>s.day===day&&s.start_period<p&&p<s.start_period+s.duration);
   const eventStarts=bookings.filter(b=>b.day===day&&b.start_period===p),eventOngoing=bookings.filter(b=>b.day===day&&b.start_period<p&&p<b.start_period+b.duration);
   const blocked=viewMode!=='group'&&(selected.unavailable||[]).some(w=>(w.week==null||w.week===7)&&w.day===day&&w.start_period<=p&&p<w.start_period+w.duration);
   const span=Math.min(10-p,Math.max(1,...starts.map(s=>s.duration),...eventStarts.map(b=>b.duration)));
   cells+=`<td colspan="${span}" class="${p===9?'p9-column':''}">${starts.map(s=>sessionMarkup(s,names)).join('')}${ongoing.map(s=>`<div class="template-continuation">↳ ${E(s.course)}<small>Lab continues</small></div>`).join('')}${eventStarts.map(b=>`<div class="event-chip"><b>${E(b.title)}</b><small>P${b.start_period}–P${b.start_period+b.duration-1} · ${E(b.room)} · APPROVED BOOKING</small></div>`).join('')}${eventOngoing.map(b=>`<div class="event-chip">↳ ${E(b.title)}<small>Booking continues</small></div>`).join('')}${!starts.length&&!ongoing.length&&!eventStarts.length&&!eventOngoing.length?blocked?'<span class="slot-unavailable">Unavailable<small>Room closure / maintenance or faculty leave</small></span>':`<span class="free-slot">${viewMode==='room'?'Unoccupied':'No session'}</span>`:''}</td>`;
   p+=span-1;
  }
  const events=bookings.filter(b=>b.day===day&&b.start_period+b.duration-1>=10);
  return `<tr><th scope="row" class="day-label">${name.slice(0,3).toUpperCase()}<small>Week 7</small></th>${cells}<td class="event-zone-bg" colspan="4">${events.length?events.map(b=>`<div class="event-chip"><b>${E(b.title)}</b><small>P${b.start_period}–P${b.start_period+b.duration-1} · ${E(b.room)} · APPROVED</small></div>`).join(''):'<div class="event-empty">☾ Evening Event Zone<small>No approved events for this filter</small><span>P10 · P11 · P12 · P13</span></div>'}</td></tr>`;
 }).join('');
 $('view').innerHTML=toolbar+`<div class="grid-wrap"><table class="timetable template-timetable"><caption class="sr-only">Week 7 timetable. Days are rows, academic periods are columns, lunch separates P5/P6 and evening periods are event-only.</caption><thead><tr><th class="day-label">DAY // SLOT</th>${columns}<th colspan="4" class="event-zone-heading">☾ P10–P13 EVENING EVENT ZONE (18:00–22:00)<small>Events & Spectra Bookings Only</small></th></tr></thead><tbody>${grid}</tbody></table></div><div class="template-grid-footer"><span>An empty cell only describes this view. Use availability or move checks before choosing a placement.</span><span>✓ <b>3-Hour Labs:</b> Strictly P2–P4 or P6–P8. Never spans lunch.</span><span>▧ <b>Elective Baskets:</b> Synchronized across constituent groups.</span><span>Click <b>? Explain</b> for verified placement facts</span></div>`;
 $('entity-filter').value=entity;
};

document.addEventListener('click',e=>{
 const button=e.target.closest('button');
 if(button?.hasAttribute('data-template-move')){
  document.querySelector('.workspace').classList.remove('copilot-collapsed');
  $('toggle-copilot').setAttribute('aria-expanded','true');
  document.documentElement.style.setProperty('--drawer-top',$('live-telemetry').getBoundingClientRect().bottom+'px');
  document.querySelector('.change-drawer').open=true;
  $('own-session').focus();
 }
});
$('template-generate').onclick=()=>$('generate').click();
$('template-overview').onclick=()=>{$('application').classList.add('hidden');$('introduction').classList.remove('hidden');window.scrollTo(0,0)};
const parseDraftOnly=$('parse').onclick;
$('parse').onclick=()=>parseDraftOnly();
document.addEventListener('click',e=>{if(e.target.closest('[data-template-scenario]'))$('parse').click()});

const alignTemplateDrawer=()=>document.documentElement.style.setProperty('--drawer-top',Math.max(0,document.getElementById('live-telemetry').getBoundingClientRect().bottom)+'px');
window.addEventListener('resize',()=>requestAnimationFrame(alignTemplateDrawer));
new ResizeObserver(alignTemplateDrawer).observe(document.getElementById('live-telemetry'));
