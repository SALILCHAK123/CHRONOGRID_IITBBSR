"""Reproducible relational CSV mirror of the actually consumed JSON input."""
import csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def export():
    data=json.loads((ROOT/'data'/'cit_synthetic.json').read_text(encoding='utf-8'))
    folder=ROOT/'exports'/'cit_synthetic_csv';folder.mkdir(parents=True,exist_ok=True)
    tables={key:rows for key,rows in data.items() if isinstance(rows,list) and rows and isinstance(rows[0],dict)}
    tables['priorities']=[dict(rank=i+1,category=c) for i,c in enumerate(data['priorities'])]
    tables['metadata']=[dict(key=k,value=v) for k,v in data['meta'].items()]
    for key,rows in tables.items():
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (folder/(key+'.csv')).open('w',newline='',encoding='utf-8-sig') as out:
            writer=csv.DictWriter(out,fieldnames=fields);writer.writeheader()
            for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,bool)) or v is None else v for k,v in row.items()})
    (folder/'README.txt').write_text('Synthetic development data, not the official starter pack. Source: data/cit_synthetic.json.\nUTF-8 BOM; comma-separated with headers. Lists, objects, booleans and null are JSON in cells. Empty optional cells mean absent fields. References use stable IDs matching JSON. Week absent/null means recurring; week 7/8 means calendar-specific. Days 0=Monday through 4=Friday. P1-P5=08:00-13:00; lunch=13:00-14:00; P6-P9=14:00-18:00; P10-P13=18:00-22:00 events only.\n',encoding='utf-8')
    print('Exported CSV mirror:',{key:len(rows) for key,rows in tables.items()})

if __name__=='__main__':export()
