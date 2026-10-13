"""Merge submissions and admin commands into XML. Existing XML edits remain authoritative.
Admin commands are applied exactly once via data/admin_applied.json.
"""
import json, os, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from pathlib import Path
base=Path(__file__).resolve().parents[1]
url=os.getenv('SUPABASE_URL','').rstrip('/')
key=os.getenv('SUPABASE_SERVICE_ROLE_KEY','')
if not url or not key:
    raise SystemExit('Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY GitHub secrets')
headers={'apikey':key,'Authorization':'Bearer '+key}
def fetch(table,columns,order):
    start=0
    while True:
        query=urllib.parse.urlencode({'select':columns,'order':order,'limit':500,'offset':start})
        req=urllib.request.Request(f'{url}/rest/v1/{table}?{query}',headers=headers)
        with urllib.request.urlopen(req,timeout=30) as resp: batch=json.load(resp)
        yield from batch
        if len(batch)<500: break
        start+=len(batch)
players={e.get('id'):e.attrib for e in ET.parse(base/'data/players.xml').getroot()}
rules=ET.parse(base/'data/rules.xml').getroot()
slots=[e.get('code') for e in rules.findall('./roster/position') for _ in range(int(e.get('count')))]
tree=ET.parse(base/'data/teams.xml');root=tree.getroot()
known={e.get('id') for e in root.findall('team')}
applied_file=base/'data/admin_applied.json'
applied=set(json.loads(applied_file.read_text()) if applied_file.exists() else [])

def valid_picks(picks):
    if not isinstance(picks,list) or len(picks)!=len(slots): return False
    selected=[players.get(pid) if isinstance(pid,str) else None for pid in picks]
    return all(p and p['position']==slots[i] and p['team']!='FA' for i,p in enumerate(selected)) and len({p['team'] for p in selected})==len(slots)

def write_picks(node,picks):
    for child in list(node): node.remove(child)
    for pos,pid in zip(slots,picks):ET.SubElement(node,'pick',{'position':pos,'playerId':pid})

# New submissions only. Never overwrite an existing team's owner-edited XML.
added=0
for entry in fetch('submissions','id,name,owner,picks','created_at.asc'):
    ident=str(entry.get('id',''))
    if not re.fullmatch(r'[0-9a-fA-F-]{36}',ident) or ident in known: continue
    picks=entry.get('picks',[])
    name=str(entry.get('name','')).strip();owner=str(entry.get('owner','')).strip()
    if not valid_picks(picks) or not (1<=len(name)<=60 and 1<=len(owner)<=60):continue
    node=ET.SubElement(root,'team',{'id':ident,'name':name,'owner':owner})
    write_picks(node,picks);known.add(ident);added+=1

# Apply authenticated admin actions. Actions are append-only in Supabase.
score_path=base/'data/scores.xml';score_tree=ET.parse(score_path);score_root=score_tree.getroot()
changed=0
for command in fetch('admin_actions','id,action,payload','id.asc'):
    ident=str(command['id'])
    if ident in applied:continue
    action=command['action'];p=command['payload'];tid=str(p.get('id',''))
    node=next((x for x in root.findall('team') if x.get('id')==tid),None)
    if action=='delete_team':
        if node is not None:root.remove(node)
        # Block re-import of the original submission permanently.
        known.add(tid)
    elif action=='edit_team':
        picks=p.get('picks',[]);name=str(p.get('name','')).strip();owner=str(p.get('owner','')).strip()
        if not valid_picks(picks) or not (1<=len(name)<=60 and 1<=len(owner)<=60):
            raise ValueError(f'Invalid admin edit action {ident}; fix the action before syncing')
        if node is None: raise ValueError(f'Team {tid} does not exist for edit action {ident}')
        node.set('name',name);node.set('owner',owner);write_picks(node,picks)
    elif action=='score_override':
        pid=str(p.get('playerId',''));adjustment=p.get('adjustment')
        if pid not in players or not isinstance(adjustment,(int,float)) or isinstance(adjustment,bool) or abs(adjustment)>100000:
            raise ValueError(f'Invalid score action {ident}')
        score=next((x for x in score_root.findall('score') if x.get('playerId')==pid),None)
        if score is None:score=ET.SubElement(score_root,'score',{'playerId':pid,'touchdowns':'0','fieldGoals':'0'})
        score.set('adjustment',str(adjustment))
    else:raise ValueError(f'Unknown admin action {ident}')
    applied.add(ident);changed+=1
# A deleted submission must stay deleted even on future syncs.
# Reconstruct tombstones from the durable action log on each run.
for command in fetch('admin_actions','id,action,payload','id.asc'):
    if command['action']=='delete_team':
        tid=str(command['payload'].get('id',''))
        node=next((x for x in root.findall('team') if x.get('id')==tid),None)
        if node is not None:root.remove(node)
ET.indent(tree,space='  ');tree.write(base/'data/teams.xml',encoding='utf-8',xml_declaration=True)
ET.indent(score_tree,space='  ');score_tree.write(score_path,encoding='utf-8',xml_declaration=True)
applied_file.write_text(json.dumps(sorted(applied,key=int),indent=2)+'\n')
print(f'Added {added} teams, applied {changed} new admin commands')
