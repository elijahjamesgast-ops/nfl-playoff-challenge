"""Rebuild cumulative postseason scores from ESPN; preserve manual adjustments."""
import json
import re
import unicodedata
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

BASE = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl'
DATA = Path(__file__).resolve().parents[1] / 'data'


def fetch(endpoint, **params):
    url = f'{BASE}/{endpoint}?{urllib.parse.urlencode(params)}'
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def normalize(name):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', name).lower())


def extract(data, by_name, by_id):
    totals = defaultdict(lambda: [0, 0])
    for team in data['boxscore']['players']:
        for category in team['statistics']:
            kind = category['name']
            labels = category.get('labels', [])
            if kind in ('passing', 'rushing', 'receiving', 'kickReturns', 'puntReturns', 'kickreturns', 'puntreturns', 'interceptions', 'fumbles'):
                label, slot = 'TD', 0
            elif kind == 'kicking':
                label, slot = 'FG', 1
            else:
                continue
            if label not in labels:
                continue
            index = labels.index(label)
            for entry in category.get('athletes', []):
                athlete = entry['athlete']
                raw = str(entry['stats'][index]).split('/')[0]
                if raw in ('--', '-', ''):
                    continue
                count = int(raw)
                if not count:
                    continue
                pid = by_id.get(str(athlete['id'])) or by_name.get(normalize(athlete['displayName']))
                if pid:
                    totals[pid][slot] += count
                else:
                    print('Unmatched scorer:', athlete['displayName'], athlete['id'])
    return totals


def main():
    season = int(ET.parse(DATA / 'rules.xml').getroot().get('season'))
    mode = ET.parse(DATA / 'rules.xml').getroot().get('scoringMode', 'playoffs')
    today = datetime.now(ZoneInfo('America/Chicago')).date()
    if mode == 'test':
        start = date.fromisoformat(ET.parse(DATA / 'rules.xml').getroot().get('testStart'))
        end = today
        phase = 2
    elif mode == 'playoffs':
        start = date(season + 1, 1, 1)
        end = min(today, date(season + 1, 2, 28))
        phase = 3
    else:
        raise ValueError(f'Unknown scoring mode: {mode}')
    games = {}
    day = start
    while day <= end:
        board = fetch('scoreboard', dates=day.strftime('%Y%m%d'), limit=100)
        for g in board['events']:
            if (g.get('season', {}).get('type') == phase
                and g.get('season', {}).get('year') == season
                and g['status']['type']['state'] in ('in', 'post')
                and 'pro bowl' not in g['name'].lower()):
                games[g['id']] = g
        day += timedelta(days=1)
    if not games:
        print('No started games; leaving scores unchanged.')
        return
    roster = list(ET.parse(DATA / 'players.xml').getroot())
    by_name = {normalize(p.get('name')): p.get('id') for p in roster}
    by_id = {p.get('espnId'): p.get('id') for p in roster if p.get('espnId')}
    print(f'Scoring mode: {mode}; {start} through {end}')
    totals = defaultdict(lambda: [0, 0])
    for gid, game in games.items():
        print('Reading', game['name'], gid)
        for pid, counts in extract(fetch('summary', event=gid), by_name, by_id).items():
            totals[pid][0] += counts[0]
            totals[pid][1] += counts[1]
    path = DATA / 'scores.xml'
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = {n.get('playerId'): n for n in root.findall('score')}
    for pid in nodes.keys() | totals.keys():
        node = nodes.get(pid)
        if node is None:
            node = ET.SubElement(root, 'score', playerId=pid)
        td, fg = totals[pid]
        node.set('touchdowns', str(td))
        node.set('fieldGoals', str(fg))
    root.set('updated', datetime.now(timezone.utc).isoformat(timespec='seconds'))
    ET.indent(tree, space='  ')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    print(f'Updated scores from {len(games)} games.')


if __name__ == '__main__':
    main()
