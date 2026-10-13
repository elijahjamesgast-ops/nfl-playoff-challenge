"""Validate new Supabase submissions and append them to owner-editable teams.xml."""
import json, os, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
base=Path(__file__).resolve().parents[1]
url=os.getenv('SUPABASE_URL','').rstrip('/')
key=os.getenv('SUPABASE_SERVICE_ROLE_KEY','')
if not url or not key:
    print('Supabase secrets absent; nothing to sync.')
    raise SystemExit(0)
players={e.get('id'):e.attrib for e in ET.parse(base/'data/players.xml').getroot()}
rules=ET.parse(base/'data/rules.xml').getroot()
slots=[e.get('code') for e in rules.findall('./roster/position') for _ in range(int(e.get('count')))]
tree=ET.parse(base/'data/teams.xml'); root=tree.getroot()
known={e.get('id') for e in root.findall('team')}
headers={'apikey':key,'Authorization':'Bearer '+key}
# Paginate; order ensures reproducibility. Service key is only used in GitHub Actions.
start=0
while True:
    req=urllib.request.Request(url+'/rest/v1/submissions?select=id,name,owner,picks&order=created_at.asc&limit=500&offset='+str(start),headers=headers)
    with urllib.request.urlopen(req,timeout=30) as response:
        batch=json.load(response)
    if not batch: break
    for entry in batch:
        ident=str(entry.get('id',''))
        if not re.fullmatch(r'[0-9a-f-]{36}',ident) or ident in known: continue
        picks=entry.get('picks',[])
        if not isinstance(picks,list) or len(picks)!=len(slots): continue
        selected=[players.get(p) if isinstance(p,str) else None for p in picks]
        if any(p is None or p['position']!=slots[i] or p['team']=='FA' for i,p in enumerate(selected)): continue
        if len({p['team'] for p in selected})!=len(slots): continue
        name=str(entry.get('name','')).strip();owner=str(entry.get('owner','')).strip()
        if not(1<=len(name)<=60 and 1<=len(owner)<=60):continue
        node=ET.SubElement(root,'team',{'id':ident,'name':name,'owner':owner})
        for pos,pid in zip(slots,picks):ET.SubElement(node,'pick',{'position':pos,'playerId':pid})
        known.add(ident)
    if len(batch)<500:break
    start+=len(batch)
ET.indent(tree,space='  ')
tree.write(base/'data/teams.xml',encoding='utf-8',xml_declaration=True)
print('Published',len(known),'teams')
