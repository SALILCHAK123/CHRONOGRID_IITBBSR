// Run the actual presentation adapter against isolated fixtures, without touching live data.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const elements=new Map();const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',value:'',textContent:'',onclick:()=>{},getBoundingClientRect:()=>({bottom:0}),classList:{add(){},remove(){}},setAttribute(){}});return elements.get(id)};
const rooms=[{id:'R1',name:'Room 1',type:'classroom',capacity:80,accessible:true,unavailable:[{week:7,day:1,start_period:1,duration:9},{week:8,day:0,start_period:1,duration:9}]}];
const groups=[{id:'G1',name:'Group 1',size:30,department:'CSE'}],faculty=[{id:'F1',name:'Faculty 1',daily_limit:4,unavailable:[{day:2,start_period:9,duration:1}]}];
const context={console,roles:{},tabs:{},render(){},$ :element,E:String,option:(v,l)=>`<option value="${v}">${l}</option>`,DAYS:['Monday','Tuesday','Wednesday','Thursday','Friday'],TIMES:['08:00','09:00','10:00','11:00','12:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00','21:00'],viewMode:'room',entity:'R1',courses:()=>({C1:'Class 1'}),canEditTeachingSession:()=>true,rows:()=>[],state:{data:{rooms,groups,faculty,sessions:[]},user:{role:'admin'},schedule:{bookings:[{id:'B1',title:'Daytime event',status:'approved',day:0,start_period:4,duration:2,room:'R1',groups:['G1']},{id:'B2',title:'Evening boundary event',status:'approved',day:3,start_period:9,duration:2,room:'R1',groups:[]}]}},document:{addEventListener(){},documentElement:{style:{setProperty(){}}},querySelector(){return element('workspace')}},window:{addEventListener(){}},ResizeObserver:class{observe(){}},requestAnimationFrame(){}};
context.document.getElementById=element;
vm.createContext(context);vm.runInContext(fs.readFileSync('frontend/template.js','utf8'),context);context.renderTimetable();
let html=element('view').innerHTML;
assert.equal((html.match(/Daytime event/g)||[]).length,1,'Daytime booking must appear once in its academic slot');
assert.ok(html.indexOf('Daytime event')<html.indexOf('event-zone-bg'),'Daytime event must not live only in the evening column');
assert.equal((html.match(/Evening boundary event/g)||[]).length,2,'P9–P10 booking must occupy P9 and the evening summary');
assert.equal((html.match(/slot-unavailable/g)||[]).length,9,'Only Week 7 closure should block nine cells');
assert.ok(!html.includes('Free Slot'),'Empty cells must not promise complete availability');
for(const row of html.match(/<tbody>(.*?)<\/tbody>/s)[1].matchAll(/<tr>(.*?)<\/tr>/gs)){
 const columns=[...row[1].matchAll(/<(?:td|th)\b([^>]*)>/g)].reduce((n,m)=>n+Number(/colspan="(\d+)"/.exec(m[1])?.[1]||1),0);
 assert.equal(columns,15,'Every row must preserve period/lunch/evening column alignment');
}
context.viewMode='faculty';context.entity='F1';context.renderTimetable();assert.equal((element('view').innerHTML.match(/slot-unavailable/g)||[]).length,1);
context.viewMode='group';context.entity='G1';context.renderTimetable();assert.ok(element('view').innerHTML.includes('No session'));assert.ok(element('view').innerHTML.includes('Daytime event'));
context.state.user.role='club';context.renderTimetable();assert.match(element('view').innerHTML,/data-edit-timetable disabled/);
console.log('PASS: daytime bookings, evening boundaries, Week 7 closures, faculty leave, group view, column alignment and club edit guard.');
