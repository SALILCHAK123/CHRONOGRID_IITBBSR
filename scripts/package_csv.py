"""Verify the CSV export against every source field, then package it."""
import csv,json,zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'data'/'cit_synthetic.json').read_text(encoding='utf-8'))
folder=root/'exports'/'cit_synthetic_csv'
for key in ['rooms','faculty','groups','courses','sessions','exams','bookings']:
    with (folder/f'{key}.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert len(rows)==len(data[key]),key
    for source,export in zip(data[key],rows):
        for field,value in source.items():
            actual=export[field]
            if isinstance(value,(list,dict)) or value is None:
                assert json.loads(actual)==value,(key,source.get('id'),field)
            else:
                expected=str(value).lower() if isinstance(value,bool) else str(value)
                assert actual==expected,(key,source.get('id'),field,actual,expected)
with (folder/'sessions.csv').open(encoding='utf-8-sig',newline='') as stream:
    assert sum(int(row['duration']) for row in csv.DictReader(stream))==243
with (folder/'priorities.csv').open(encoding='utf-8-sig',newline='') as stream:
    assert [row['category'] for row in csv.DictReader(stream)]==data['priorities']
with (folder/'metadata.csv').open(encoding='utf-8-sig',newline='') as stream:
    metadata={row['key']:row['value'] for row in csv.DictReader(stream)}
assert metadata['synthetic']=='true'
target=root/'exports'/'cit_synthetic_dataset_csv.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(folder.iterdir()):archive.write(file,arcname=folder.name+'/'+file.name)
with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
print(f'All CSV records match the source. Verified 243 teaching hours. Packaged {len(list(folder.iterdir()))} files: {target}')
