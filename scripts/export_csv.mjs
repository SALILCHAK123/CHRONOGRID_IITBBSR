import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook } from '@oai/artifact-tool';

const root=path.resolve(import.meta.dirname,'..');
const data=JSON.parse(await fs.readFile(path.join(root,'data/cit_synthetic.json'),'utf8'));
const workbook=Workbook.create();
if(process.argv.includes('--help-csv')){
  console.log(workbook.help('export csv',{search:'csv|CSV',include:'index,examples,notes',maxChars:4500}).ndjson);
  process.exit(0);
}
const output=path.join(root,'exports','cit_synthetic_csv');
await fs.mkdir(output,{recursive:true});
const counts={};
const cell=value=>value===null?'null':typeof value==='object'?JSON.stringify(value):value;
const quote=value=>'"'+String(value??'').replaceAll('"','""')+'"';
const tables=Object.fromEntries(Object.entries(data).filter(([,rows])=>Array.isArray(rows)&&rows.every(r=>r&&typeof r==='object'&&!Array.isArray(r))));
tables.priorities=data.priorities.map((category,index)=>({rank:index+1,category}));
tables.metadata=Object.entries(data.meta).map(([key,value])=>({key,value:cell(value)}));
for(const [name,records]of Object.entries(tables)){
  const fields=[...new Set(records.flatMap(row=>Object.keys(row)))];
  const matrix=[fields,...records.map(row=>fields.map(field=>Object.hasOwn(row,field)?cell(row[field]):''))];
  const sheet=workbook.worksheets.add(name);
  sheet.getRangeByIndexes(0,0,matrix.length,fields.length).values=matrix;
  counts[name]=records.length;
}
workbook.recalculate();
for(const [name,records]of Object.entries(tables)){
  const sheet=workbook.worksheets.getItem(name);
  const matrix=sheet.getUsedRange().values;
  if(matrix.length!==records.length+1)throw Error('Row count mismatch: '+name);
  await fs.writeFile(path.join(output,name+'.csv'),'\uFEFF'+matrix.map(row=>row.map(quote).join(',')).join('\r\n')+'\r\n','utf8');
}
await fs.writeFile(path.join(output,'README.txt'),[
  'CIT ChronoGrid synthetic development dataset',
  'Source: data/cit_synthetic.json. These are the input records used by the app, not generated timetable assignments.',
  'This is synthetic data, not the organisers\' official starter pack.',
  'Encoding: UTF-8 with BOM. Standard comma-separated CSV with a header row.',
  'Lists and objects (groups, faculty, availability windows, features and fixed slots) are JSON text within CSV cells.',
  'An empty cell means that an optional field is absent. The text null represents an explicit JSON null.',
  'Days: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday.',
  'Periods: P1=08:00, P2=09:00, P3=10:00, P4=11:00, P5=12:00, lunch=13:00-14:00,',
  'P6=14:00, P7=15:00, P8=16:00, P9=17:00, P10=18:00, P11=19:00, P12=20:00, P13=21:00.',
  'Duration is measured in one-hour periods. Priority rank 1 is highest.',
  '',...Object.entries(counts).map(([name,count])=>name+'.csv: '+count+' records'),
  'sessions.csv: 243 teaching hours in total.',
].join('\r\n')+'\r\n','utf8');
console.log(JSON.stringify({output,records:counts}));
