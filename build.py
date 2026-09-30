#!/usr/bin/env python3
"""OKC client dashboard builder.

Everything in this repo is public. Keep it client-safe: no team names, internal notes, approvals, tools or credits.

Inputs:  tasks.json (client wording), status.json ({task_id: {status: done|progress|waiting, link, at}}),
         config.json (keywords, targets, rankings, needs, update text, chat endpoint), okc-logo.png
Output:  index.html (served by Netlify at okc-seo-dashboard.netlify.app)
Run:     python3 build.py
"""
import base64, datetime as dt, json, re, sys
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).parent
cfg = json.loads((HERE / 'config.json').read_text())

sp = HERE / 'status.json'
status = json.loads(sp.read_text()) if sp.exists() else {}
now = dt.datetime.now(ZoneInfo('America/Chicago'))
today = now.date()
start = dt.date.fromisoformat(cfg['program']['start'])
end = dt.date.fromisoformat(cfg['program']['end'])



tasks = []
for t in json.loads((HERE / 'tasks.json').read_text()):
    st = status.get(t['id'], {})
    s = st.get('status') if st.get('status') in ('done', 'progress', 'waiting') else 'scheduled'
    tasks.append(dict(t, status=s, link=st.get('link') if s == 'done' else None, at=st.get('at')))

# ---- this month's deliverables
ref = max(start, min(today, end))
mkey = ref.strftime('%Y-%m')
month_tasks = [t for t in tasks if t['date'].startswith(mkey)]
def count(pred):
    sel = [t for t in month_tasks if pred(t)]
    return sum(t['status'] == 'done' for t in sel), len(sel)
tg = cfg['targets']
gbp = count(lambda t: t['label'].startswith('Google post'))
lst = count(lambda t: t['cat'] == 'Citations')
bl = count(lambda t: t['label'].startswith('Backlink placed'))
blog = count(lambda t: t['label'].startswith('Blog published'))
soc = count(lambda t: t['cat'] == 'Social')
rev = count(lambda t: t['cat'] == 'Reviews')
pins = count(lambda t: t['cat'] == 'Map Pins')
monthly = [
    {'name': 'Google posts', 'done': gbp[0], 'target': tg['gbp'], 'unit': 'posts'},
    {'name': 'Business listings', 'done': lst[0], 'target': tg['listings'], 'unit': 'new or fixed'},
    {'name': 'Backlinks', 'done': bl[0], 'target': tg['backlinks'], 'unit': 'up to'},
    {'name': 'Blog posts', 'done': blog[0], 'target': blog[1], 'unit': 'published'},
    {'name': 'Google Maps pins', 'done': pins[0], 'target': pins[1], 'unit': 'service areas'},
    {'name': 'Review checks', 'done': rev[0], 'target': rev[1], 'unit': 'every reply answered'},
    {'name': 'Social posts', 'done': soc[0], 'target': tg['social'], 'unit': 'Facebook and Instagram'},
]

# ---- week view: Mon-Fri of the current week (next week on weekends, week 1 before start)
wref = max(start, min(today, end))
if wref.weekday() >= 5: wref += dt.timedelta(days=7 - wref.weekday())
monday = wref - dt.timedelta(days=wref.weekday())
week = []
for i in range(5):
    d = monday + dt.timedelta(days=i)
    items = [t for t in tasks if t['date'] == d.isoformat()]
    if d < start or d > end: continue
    week.append({'date': d.isoformat(), 'items': [{k: t[k] for k in ('area', 'label', 'status', 'link')} for t in items]})

recent = sorted([t for t in tasks if t['status'] == 'done'], key=lambda t: (t['at'] or t['date']), reverse=True)[:12]
recent = [{k: t[k] for k in ('date', 'area', 'label', 'link')} for t in recent]

total_days = (end - start).days + 1
elapsed = min(max((today - start).days + 1, 0), total_days)
week_no = min(max((wref - (start - dt.timedelta(days=start.weekday()))).days // 7 + 1, 1), 14)
total_weeks = ((end - (start - dt.timedelta(days=start.weekday()))).days // 7) + 1

data = {
    'client': cfg['client'], 'site': cfg['site'], 'program': cfg['program'], 'agency': cfg['agency'],
    'updated': now.strftime('%Y-%m-%dT%H:%M'), 'today': today.isoformat(), 'month': mkey,
    'progress': {'elapsed': elapsed, 'days': total_days, 'week': week_no, 'weeks': total_weeks,
                 'done': sum(t['status'] == 'done' for t in tasks), 'total': len(tasks),
                 'active': sum(t['status'] in ('progress', 'waiting') for t in tasks)},
    'monthly': monthly, 'keywords': cfg['keywords'], 'rankings': cfg.get('rankings', {}),
    'week': week, 'recent': recent, 'needs': cfg['needs'], 'update': cfg.get('client_update'),
    'chat': {'url': cfg.get('chat_url', ''), 'token': cfg.get('chat_token', '')},
}

logo = 'data:image/png;base64,' + base64.b64encode((HERE / 'okc-logo.png').read_bytes()).decode()
body = (HERE / 'template.html').read_text().replace('__DATA__', json.dumps(data, separators=(',', ':'))).replace('__LOGO__', logo)
(HERE / 'index.html').write_text(
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    '<meta name="robots" content="noindex,nofollow"></head><body>' + body + '</body></html>')
print('built', mkey, 'tasks', len(tasks), 'done', data['progress']['done'], 'week', week_no, 'of', total_weeks)
