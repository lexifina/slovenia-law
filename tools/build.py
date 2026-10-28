"""Builds a git repository of Slovenian law from PIS (Pravno-informacijski sistem Republike Slovenije, pisrs.si), in
which every amending act is one commit, dated the day it took effect.

    python -X utf8 scripts/slovenia-law/build.py [--repo ../slovenia-law] [--today 2026-10-28] [--offline]
    python -X utf8 scripts/slovenia-law/build.py --offline --verify-rebuild

PIS publishes, for each act, the text as enacted ("Osnovni") and every unofficial consolidated text ("neuradno
prečiščeno besedilo", NPB 1, 2, ...). Its register of relations between acts names, for each NPB, the one act whose
entry into force produced it (the "poseg"), and the register entry of that act gives the day it took effect (veljaOd).
We take every version of the acts below, compare consecutive versions provision by provision (člen by člen), and
credit a changed člen to the act of that version when the act's own text names that člen. A change the act's text does
not explain (PIS's own editing of the consolidated text) is never credited to an act: it gets its own commit by PIS,
labelled as unexplained.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as htmlmod
import io
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = HERE / '.cache'
API = 'https://pisrs.si/api'
SITE = 'https://pisrs.si'
UA = 'lexifina-watch/1.0 (+https://lexifina.com/watch; corpus@lexifina.com)'
PAUSE = 0.7          # seconds between two requests to PIS; one request at a time
COMMITTER = ('Lexifina', 'slovenia-law@lexifina.com')
PIS = ('PIS RS (neuradno prečiščeno besedilo)', 'pis@pisrs.invalid')
FUTURE_BRANCH = 'prihodnje'

# The acts in the record: PIS's identifier, a short name and the repository folder.
ACTS = [
    {'id': 'USTA1', 'slug': 'urs', 'short': 'URS', 'names': 'ustav'},
    {'id': 'ZAKO185', 'slug': 'zvdz', 'short': 'ZVDZ', 'names': 'volitvah v državni zbor'},
]


# ---------------------------------------------------------------- fetching

REQUESTS: list[dict] = []   # every request the build made, for REPRODUCE.md
_last = [0.0]


def _get(url: str) -> bytes:
    wait = _last[0] + PAUSE - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except Exception as exc:   # a certificate chain Python does not accept on some machines: fall back to curl
        if 'CERTIFICATE' not in str(exc).upper():
            raise
        out = subprocess.run(['curl', '-sS', '-f', '-L', '--max-redirs', '4', '-A', UA, url], capture_output=True)
        if out.returncode:
            raise RuntimeError(f'curl {url}: {out.stderr.decode(errors="replace")}')
        return out.stdout


def fetch(url: str, offline: bool = False) -> bytes:
    """GET with a file cache keyed by the URL, so a rebuild reads the same bytes."""
    key = hashlib.sha256(url.encode()).hexdigest()[:32]
    path = CACHE / key
    REQUESTS.append({'url': url, 'file': path})
    if path.exists():
        return path.read_bytes()
    if offline:
        raise SystemExit(f'not cached: {url}')
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / '.gitignore').write_text('*\n')
    for attempt in range(4):
        try:
            body = _get(url)
            doc = json.loads(body)
            if doc.get('data') is None:
                raise RuntimeError(f'PIS error for {url}: {doc.get("error")}')
            path.write_bytes(body)
            return body
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError


def data(url: str, offline: bool):
    return json.loads(fetch(url, offline))['data']


def clean(s: str) -> str:
    """The words of an element: tags removed (a line break counts as a space), entities decoded, runs of white space
    made one space. Every other character is kept as PIS has it."""
    s = re.sub(r'<br\s*/?>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmlmod.unescape(s).replace(' ', ' ')
    return re.sub(r'\s+', ' ', s).strip()


# ---------------------------------------------------------------- the act, its versions and the acts behind them

def npb_number(name: str) -> int:
    return 0 if name == 'Osnovni' else int(re.fullmatch(r'NPB (\d+)', name).group(1))


def ul_label(ul: str | None) -> str:
    return f'Uradni list RS, št. {ul}' if ul else 'Uradni list RS'


def act_info(e: dict) -> dict:
    """The register entry of an act (evidencniPodatki), reduced to what the record uses."""
    kind = e.get('vrstaAkta') or ''
    short = e.get('kratica') or ('odl. US' if 'odloč' in kind.lower() else kind)
    return {'id': e['zunanjiID'], 'sop': e['sop'], 'title': clean(e['naslov']), 'short': short, 'kind': kind,
            'ul': e.get('ulStLeto'), 'adopted': e.get('sprejeto'), 'published': e.get('objavljeno'),
            'in_force': e.get('veljaOd'), 'applies': e.get('uporabljaOd'), 'organ': e.get('organSprejetja'),
            'url': f'{SITE}/pregledPredpisa?id={e["zunanjiID"]}'}


def amending_act(sop: str, offline: bool) -> dict:
    d = data(f'{API}/rezultat/zbirka/sop/{sop}', offline)
    info = act_info(d['evidencniPodatki'])
    base = [v for v in d['besedilo']['npbVerzije'] if v['naziv'] == 'Osnovni']
    info['text_url'] = f'{API}/rezultat/neuradno-precisceno-besedilo/{base[0]["id"]}' if base else None
    info['elements'] = data(info['text_url'], offline) if base else []
    return info


def act_versions(act: dict, offline: bool) -> dict:
    d = data(f'{API}/rezultat/zbirka/id/{act["id"]}', offline)
    info = act_info(d['evidencniPodatki'])
    rel = data(f'{API}/povezave/med-si-akti/{d["evidencniPodatki"]["zbirkaElementID"]}', offline)
    poseg = {r['id']: r for r in rel['neuradnoPreciscenoBesedilo']}
    versions = []
    for v in sorted(d['besedilo']['npbVerzije'], key=lambda v: npb_number(v['naziv'])):
        url = f'{API}/rezultat/neuradno-precisceno-besedilo/{v["id"]}'
        raw = fetch(url, offline)
        n = npb_number(v['naziv'])
        if n and v['id'] not in poseg:
            raise SystemExit(f'{act["slug"]}: {v["naziv"]} is not in the register of relations')
        versions.append({'name': v['naziv'], 'n': n, 'npb_id': v['id'], 'url': url,
                         'sha256': hashlib.sha256(raw).hexdigest(), 'elements': json.loads(raw)['data'],
                         'sop': poseg[v['id']]['sopNPBPosega'] if n else info['sop'],
                         'applies_note': v.get('datumZacetkaUporabe')})
    return {'info': info, 'versions': versions, 'relations_url': f'{API}/povezave/med-si-akti/{d["evidencniPodatki"]["zbirkaElementID"]}',
            'citation': clean(d['evidencniPodatki'].get('citat') or '')}


# ---------------------------------------------------------------- reading one version

CLEN = re.compile(r'(\d+)\s*\.\s*([a-z])?\s*\.?\s*člen', re.I)


def read_version(elements: list[dict], resolve=None) -> dict[str, dict]:
    """One version as units in document order: the preamble (uvod), the title (naslov), each člen (with the chapter
    and section headings that begin with it), the signatures (podpis), and the final provisions of each amending act
    that PIS prints after the act (koncne/<SOP>). Each unit is a list of lines."""
    units: dict[str, dict] = {}
    order: list[str] = []
    st = {'mode': 'head', 'unit': None, 'pending': [], 'skip_list': False, 'after_hr': False}

    def unit(key: str, kind: str, label: str) -> dict:
        if key in units and kind != 'single':
            i = 2
            while f'{key}-{i}' in units:
                i += 1
            key = f'{key}-{i}'
        if key not in units:
            units[key] = {'key': key, 'kind': kind, 'label': label, 'lines': []}
            order.append(key)
        return units[key]

    def flush_pending(u: dict):
        u['lines'].extend(f'## {h}' for h in st['pending'])
        st['pending'] = []

    for x in elements:
        s, raw = x['struktura'], x['vsebina'] or ''
        text = clean(raw)
        if s in ('opozorilo', 'npb'):
            continue
        if st['mode'] == 'head' and s == 'odstavek' and text.endswith('obsega:'):
            st['skip_list'] = True      # PIS's list of the acts this NPB comprises: metadata, in the commit trailers
            continue
        if st['skip_list'] and s.startswith('alinea'):
            continue
        st['skip_list'] = False
        if s == 'napaka' and '<hr' in raw.lower():
            st['mode'], st['unit'], st['after_hr'] = 'tail', None, True
            continue
        if st['mode'] == 'tail':
            if st['after_hr']:
                st['after_hr'] = False
                m = re.search(r'urlurid&#61;(\d{4})(\d+)', raw) or re.search(r'urlurid=(\d{4})(\d+)', raw)
                sop = resolve(text) if resolve and not m else None
                if m:
                    key = f'koncne/{m.group(1)}-01-{int(m.group(2)):04d}'
                elif sop:
                    key = f'koncne/{sop}'
                else:
                    ul = re.search(r'št\.\s*([\d/\-IVX]+)', text)
                    key = f'koncne/ul-{ul.group(1).replace("/", "-")}' if ul else 'koncne/x'
                st['unit'] = unit(key, 'koncne', text)
            if st['unit'] is None:
                st['unit'] = unit('koncne/x', 'koncne', '')
            if text:
                st['unit']['lines'].append(text)
            continue
        if not text:
            continue
        if s == 'naslov':
            st['mode'] = 'body'
            unit('naslov', 'single', 'Naslov')['lines'].append(text)
            st['unit'] = None
            continue
        if s in ('poglavje', 'oddelek'):
            st['mode'] = 'body'
            st['pending'].append(text)
            continue
        if s in ('podpisnik', 'evidencna_stevilka', 'kraj_datum_sprejetja'):
            st['unit'] = unit('podpis', 'single', 'Podpis')
            flush_pending(st['unit'])
            st['unit']['lines'].append(text)
            continue
        if s == 'clen':
            m = CLEN.fullmatch(text)
            if m and st['mode'] != 'podpis':
                st['mode'] = 'body'
                n, suf = int(m.group(1)), (m.group(2) or '').lower()
                u = unit(f'clen-{n}{suf}', 'clen', f'{n}.{suf} člen' if suf else f'{n}. člen')
                flush_pending(u)
                u['lines'].append(f'# {text}')
                st['unit'] = u
                continue
            u = st['unit']
            if u is not None and u['kind'] == 'clen' and u['lines'] and u['lines'][-1].startswith('# '):
                u['lines'][-1] += f' {text}'     # the subject of the člen, "(mandat sodnikov)"
                continue
        if st['mode'] == 'head' and st['unit'] is None:
            st['unit'] = unit('uvod', 'single', 'Uvod')
        if st['unit'] is None:
            st['unit'] = unit('uvod' if st['mode'] == 'head' else 'podpis', 'single', 'Uvod' if st['mode'] == 'head' else 'Podpis')
        flush_pending(st['unit'])
        st['unit']['lines'].append(text)
    if st['pending']:
        u = unit('podpis', 'single', 'Podpis')
        flush_pending(u)
    out = {}
    for k in order:
        u = units[k]
        u['text'] = '\n\n'.join(u['lines']) + '\n'
        out[k] = u
    return out


# ---------------------------------------------------------------- file names and order

def unit_order(key: str) -> tuple:
    if key == 'uvod':
        return (0, 0, '', '')
    if key == 'naslov':
        return (1, 0, '', '')
    m = re.fullmatch(r'clen-(\d+)([a-z]?)(.*)', key)
    if m:
        return (2, int(m.group(1)), m.group(2), m.group(3))
    if key == 'podpis':
        return (3, 0, '', '')
    return (4, 0, '', key)


def file_name(key: str) -> str:
    m = re.fullmatch(r'clen-(\d+)(.*)', key)
    if m:
        return f'clen-{int(m.group(1)):03d}{m.group(2)}.md'
    return f'{key}.md'


def section_free(text: str) -> str:
    return '\n\n'.join(l for l in text.split('\n\n') if not l.startswith('## '))


def heading_lines(text: str) -> list[str]:
    return [l for l in text.split('\n\n') if l.startswith('## ')]


# ---------------------------------------------------------------- what an amending act's text names

LIST = re.compile(r'((?:\d+\s*\.\s*(?:[a-z](?![a-zčšž]))?\s*(?:,|in|ter|oziroma|ali|do|ali)?\s*)+)(?:člen|čl\.)', re.I)
ITEM = re.compile(r'(\d+)\s*\.\s*([a-z](?![a-zčšž]))?', re.I)
RANGE = re.compile(r'od\s+(\d+)\s*\.\s*([a-z])?\s*(?:člena\s+)?do\s+(\d+)\s*\.\s*([a-z])?\s*člen', re.I)
NAMED = re.compile(r'\bčlen(?:a|u|om|i|ov)?\s+(\d+)([a-z])?\b', re.I)


def named_clens(elements: list[dict], scope: str | None = None) -> set[str]:
    """Every člen the amending act's text names in its sentences ("V 68. členu se ...", "Za 3. členom se doda nov
    3.a člen", "121., 140. in 143. člen", "od 5. do 9. člena", "člen 87"), as unit keys. The act's own article
    numbers (its "clen" headings) are not counted. With a scope (words that name the amended act, "volitvah v
    državni zbor"), only the passages from a sentence that names the act to the next sentence that names another
    act ("zakon o ...") count: an act that amends several laws numbers the articles of each."""
    keys: set[str] = set()
    inside = scope is None
    for x in elements:
        if x['struktura'] in ('clen', 'naslov'):
            continue
        t = clean(x['vsebina'] or '')
        if scope is not None:
            if scope in t.lower():
                inside = True
            elif re.search(r'\b(?:zakon|odlok|uredb|ustav)\w* o ', t, re.I):
                inside = False
        if not inside:
            continue
        for m in LIST.finditer(t):
            for i in ITEM.finditer(m.group(1)):
                keys.add(f'clen-{int(i.group(1))}{(i.group(2) or "").lower()}')
        for m in RANGE.finditer(t):
            for n in range(int(m.group(1)), int(m.group(3)) + 1):
                keys.add(f'clen-{n}')
        for m in NAMED.finditer(t):
            keys.add(f'clen-{int(m.group(1))}{(m.group(2) or "").lower()}')
    return keys


GLOBAL = re.compile(r'(?:celotnem|vsem|celem)\s+besedilu[^»"]*?besed\w*\s*[»"]([^«"]+)[«"]\s*nadomest\w*\s+z\s+besed\w*\s*[»"]([^«"]+)[«"]', re.I)


def global_replacements(elements: list[dict]) -> list[tuple[str, str]]:
    """The replacements an amending act makes "in the whole text" ("V celotnem besedilu zakona se besedilo
    »republiška volilna komisija« nadomesti z besedilom »državna volilna komisija« v ustreznih sklonih"), as pairs of
    word stems (the word without a final vowel, so that every grammatical case matches): [('republišk', 'državn')]."""
    pairs = []
    for x in elements:
        for m in GLOBAL.finditer(clean(x['vsebina'] or '')):
            old, new = m.group(1).split(), m.group(2).split()
            if len(old) != len(new):
                pairs.append((m.group(1), m.group(2)))
                continue
            for a, b in zip(old, new):
                if a != b:
                    pairs.append((a[:-1] if a[-1] in 'aeiou' else a, b[:-1] if b[-1] in 'aeiou' else b))
    return pairs


def apply_global(text: str, pairs: list[tuple[str, str]]) -> str:
    for a, b in pairs:
        text = text.replace(a, b).replace(a[:1].upper() + a[1:], b[:1].upper() + b[1:])
    return text


def names_headings(elements: list[dict]) -> bool:
    return any(re.search(r'poglavj|oddel', clean(x['vsebina'] or ''), re.I) for x in elements
               if x['struktura'] not in ('clen', 'naslov'))


# ---------------------------------------------------------------- one act: versions, changes, causes

def build_act(act: dict, offline: bool) -> dict:
    av = act_versions(act, offline)
    info = av['info']
    acts = {info['sop']: {**info, 'elements': [], 'text_url': None}}
    for v in av['versions']:
        if v['sop'] not in acts:
            acts[v['sop']] = amending_act(v['sop'], offline)

    def resolve(header: str) -> str | None:
        """The act whose final provisions follow a header that has no link: the one act of this record's versions
        with that Uradni list number whose title the header repeats."""
        low = header.lower()
        hits = [a['sop'] for a in acts.values() if a['ul'] and f'št. {a["ul"].lower()}' in low
                and re.sub(r'\s*\([^)]*\)$', '', a['title']).lower()[:40] in low]
        return hits[0] if len(hits) == 1 else None
    versions = []
    for v in av['versions']:
        a = acts[v['sop']]
        day, note = a['in_force'], None
        if not day:
            day, note = a['published'], 'no in-force day in the register; dated by publication'
        versions.append({**v, 'from': day, 'date_note': note, 'units': read_version(v['elements'], resolve)})
    # The issue day of each act's Uradni list, as the consolidated texts list it ("Uradni list RS, št. 92/21 z dne
    # 8. 6. 2021"), to show where the register's publication day disagrees.
    for v in av['versions']:
        for x in v['elements']:
            for m in re.finditer(r'št\.\s*(\S+?) z dne (\d+)\.\s*(\d+)\.\s*(\d{4})', clean(x['vsebina'] or '')):
                for a in acts.values():
                    if a['ul'] and m.group(1) in (a['ul'], f'{a["ul"]}-I'):
                        a.setdefault('issue_day', f'{m.group(4)}-{int(m.group(3)):02d}-{int(m.group(2)):02d}')
    # The act's own Uradni list number as its citation gives it (33/91-I; the register says 33/91).
    m = re.match(r'Uradni list RS, št\. ([^,\s]+)', av['citation'])
    if m and m.group(1).startswith(info['ul'] or '#') and m.group(1) != info['ul']:
        acts[info['sop']]['ul'] = info['ul'] = m.group(1)
    for p, c in zip(versions, versions[1:]):
        if c['from'] < p['from']:
            raise SystemExit(f'{act["slug"]}: {c["name"]} ({c["from"]}) is earlier than {p["name"]} ({p["from"]})')
    changes, problems = [], []
    for prev, cur in zip(versions, versions[1:]):
        A = acts[cur['sop']]
        title_el = [{'struktura': 'odstavek', 'vsebina': A['title']}]
        scope = None if act['names'] in A['title'].lower() else act['names']
        named = named_clens(A['elements'], scope)
        by_title = named_clens(title_el) - named
        named |= by_title
        heads = names_headings(A['elements'] or title_el)
        pairs = global_replacements(A['elements'])
        official = 'prečiščeno besedilo' in A['title'].lower()
        keys = sorted(set(prev['units']) | set(cur['units']), key=unit_order)
        changed = [k for k in keys if (prev['units'].get(k) or {}).get('text') != (cur['units'].get(k) or {}).get('text')]
        cause, why = {}, {}
        for k in changed:
            if official:
                cause[k], why[k] = A['sop'], 'the official consolidated text (uradno prečiščeno besedilo) restates the whole act'
            elif k == f'koncne/{A["sop"]}' and k not in prev['units']:
                cause[k], why[k] = A['sop'], 'the final provisions of the amending act itself'
            elif k.startswith('clen-') and re.sub(r'^(clen-\d+[a-z]?)-\d+$', r'\1', k) in named:
                base = re.sub(r'^(clen-\d+[a-z]?)-\d+$', r'\1', k)
                cause[k], why[k] = A['sop'], ('the title of the amending act names this člen (PIS has no text of the act)'
                                              if base in by_title else 'the amending act names this člen')
            elif pairs and k in prev['units'] and k in cur['units'] and \
                    apply_global(prev['units'][k]['text'], pairs) == cur['units'][k]['text']:
                cause[k], why[k] = A['sop'], 'a replacement the amending act makes in the whole text'
        for k in changed:     # headings: named by the act, or moved together with a člen the act changed
            if k in cause:
                continue
            a, c = (prev['units'].get(k) or {}).get('text', ''), (cur['units'].get(k) or {}).get('text', '')
            if a and c and section_free(a) == section_free(c):
                if heads:
                    cause[k], why[k] = A['sop'], 'heading; the amending act amends a chapter or section'
                    continue
                moved = set(heading_lines(a)) ^ set(heading_lines(c))
                for k2 in changed:
                    if k2 != k and k2 in cause:
                        t2 = (cur['units'].get(k2) or prev['units'].get(k2))['text']
                        if moved & set(heading_lines(t2)):
                            cause[k], why[k] = A['sop'], f'heading moved with {k2}'
                            break
        for k in changed:
            if k not in cause:
                cause[k], why[k] = 'unexplained', 'the amending act of this version does not name it'
                problems.append(f'{cur["from"]} {cur["name"]} {k}')
        groups: dict[str, list[str]] = {A['sop']: []}
        for k in changed:
            groups.setdefault(cause[k], []).append(k)
        changes.append({'from': cur['from'], 'version': cur, 'prev': prev, 'act': A['sop'], 'groups': groups, 'why': why})
    return {'act': act, 'info': info, 'versions': versions, 'acts': acts, 'changes': changes, 'problems': problems,
            'relations_url': av['relations_url'], 'citation': av['citation']}


# ---------------------------------------------------------------- the git repository

def git(repo: Path, *args: str, env: dict | None = None, input: str | None = None) -> str:
    out = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, encoding='utf-8', env=env, input=input)
    if out.returncode:
        raise SystemExit(f'git {" ".join(args)} failed: {out.stderr}')
    return out.stdout


def last_sunday(year: int, month: int) -> dt.date:
    d = (dt.date(year, month + 1, 1) if month < 12 else dt.date(year + 1, 1, 1)) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def ljubljana_offset(day: dt.date) -> int:
    """Hours ahead of UTC at noon on a day in Ljubljana (written out because this machine has no tz database). Central
    European Time; summer time since 1983, from the last Sunday in March to the last Sunday in September until 1995
    and to the last Sunday in October since 1996. The switch happens at 01:00 UTC, so noon on the first Sunday is
    already summer time and noon on the last Sunday is already winter time."""
    if day.year < 1983:
        return 1
    end = last_sunday(day.year, 9 if day.year < 1996 else 10)
    return 2 if last_sunday(day.year, 3) <= day < end else 1


def commit_date(day: str, seq: list[int]) -> str:
    """Noon in Ljubljana on the day. Git cannot record a time before 1970, so a change in force before then would be
    dated 1 January 1970 (UTC), one second apart in order, with the real day in the In-force trailer (none of the acts
    here has one)."""
    d = dt.date.fromisoformat(day)
    if d.year < 1970:
        seq[0] += 1
        return f'@{seq[0]} +0000'
    off = ljubljana_offset(d)
    stamp = int(dt.datetime(d.year, d.month, d.day, 12, tzinfo=dt.timezone(dt.timedelta(hours=off))).timestamp())
    return f'@{stamp} +0{off}00'


def author_of(a: dict) -> tuple[str, str]:
    return f'{ul_label(a["ul"])} ({a["short"]})', f'{a["id"].lower()}@pisrs.invalid'


def unit_label(u: dict) -> str:
    if u['kind'] == 'clen':
        return u['label']
    if u['kind'] == 'koncne':
        return f'končne določbe {u["key"][7:]}'
    return u['label']


def change_kind(prev: dict | None, cur: dict | None) -> str:
    if prev is None:
        return 'Dodano'
    if cur is None:
        return 'Odstranjeno'
    return 'Spremenjeno'


def write_unit(repo: Path, slug: str, key: str, unit: dict | None):
    path = repo / slug / file_name(key)
    if unit is None:
        path.unlink(missing_ok=True)
        if path.parent != repo / slug and path.parent.exists() and not any(path.parent.iterdir()):
            path.parent.rmdir()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(unit['text'], encoding='utf-8', newline='\n')


PRE_1970 = ['Git ne more zapisati datuma pred letom 1970; datum začetka veljavnosti je v In-force.',
            '(Git cannot record dates before 1970: the real day is In-force.)', '']


def act_trailers(a: dict, day: str) -> list[str]:
    t = [f'Adopted: {a["adopted"]}'] if a['adopted'] else []
    t += [f'Published: {a["published"]} ({ul_label(a["ul"])})'] if a['published'] else []
    t += [f'In-force: {day}']
    if a['applies'] and a['applies'] != day:
        t += [f'Applies-from: {a["applies"]}']
    if a['in_force'] and a['published'] and a['in_force'] < a['published']:
        t += ['Date-note: in force before its publication in the Uradni list (the register\'s veljaOd)']
    if a.get('issue_day') and a['published'] and a['issue_day'] != a['published']:
        t += [f'Date-note: the register gives publication {a["published"]}, but PIS\'s consolidated text lists '
              f'{ul_label(a["ul"])} as dated {a["issue_day"]}; both kept as the source gives them']
    if a['adopted'] and a['published'] and a['published'] < a['adopted']:
        t += ['Date-note: the register\'s publication day is before its adoption day']
    if not a['in_force']:
        t += ['Date-note: no in-force day in the register; dated by publication']
    return t


def plan_commits(built: list[dict]) -> list[tuple]:
    """Every commit, sorted by day, then act, then version: the version's act first, then the changes it does not
    explain, so that each version of PIS is exactly the state after its last commit (three constitutional acts took
    effect on 15 June 2004, two on 31 May 2013)."""
    commits = []
    for ai, b in enumerate(built):
        commits.append((b['versions'][0]['from'], ai, 0, '', {'kind': 'start', 'b': b}))
        for ch in b['changes']:
            n = ch['version']['n']
            commits.append((ch['from'], ai, n * 10 + 1, ch['act'], {'kind': 'law', 'b': b, 'ch': ch, 'sop': ch['act']}))
            if 'unexplained' in ch['groups']:
                commits.append((ch['from'], ai, n * 10 + 2, '', {'kind': 'unexplained', 'b': b, 'ch': ch}))
    commits.sort(key=lambda c: c[:4])
    return commits


def start_message(b: dict, day: str):
    a, v = b['info'], b['versions'][0]
    msg = [f'{b["act"]["short"]}: izvirno besedilo ({ul_label(a["ul"])})', '', a['title'], '',
           f'Besedilo predpisa, kot je bil sprejet, v PIS ("Osnovni"); velja od {day}.', '',
           'The act as enacted, the text PIS gives as "Osnovni", in force from this day.', '']
    trailers = act_trailers(a, day) + [f'Affecting: {b["act"]["short"]} ({len(v["units"])} units)',
                                         'Cause-basis: the act itself (text as enacted)', f'Source: {a["url"]}', f'Consolidated: {v["url"]}']
    if day < '1970-01-01':
        msg += PRE_1970
    return author_of(a), msg, trailers


def count(n: int) -> str:
    """'4 določbe', '14 določb': the Slovenian plural after a number."""
    word = {1: 'določba', 2: 'določbi', 3: 'določbe', 4: 'določbe'}.get(n % 100, 'določb')
    return f'{n} {word}'


def change_message(b: dict, ch: dict, sop: str | None, day: str):
    short = b['act']['short']
    keys = sorted(ch['groups'].get(sop or 'unexplained', []), key=unit_order)
    units = [(k, ch['prev']['units'].get(k), ch['version']['units'].get(k)) for k in keys]
    labels = [unit_label(c or p) for k, p, c in units]
    affecting = ', '.join(f'{short} {l}' for l in labels)
    v = ch['version']
    A = b['acts'][ch['act']]
    if sop:
        author = author_of(A)
        subject = f'{short}: {", ".join(labels) if labels else "besedilo nespremenjeno"} ({ul_label(A["ul"])} – {A["short"]})'
        if len(subject) > 100:
            subject = f'{short}: {count(len(labels))} ({ul_label(A["ul"])} – {A["short"]})'
        msg = [subject, '', A['title'], '']
        by_kind: dict[str, list[str]] = {}
        for (k, p, c), l in zip(units, labels):
            by_kind.setdefault(change_kind(p, c), []).append(l)
        en = {'Dodano': 'Inserted', 'Spremenjeno': 'Amended', 'Odstranjeno': 'Removed'}
        for name in ('Dodano', 'Spremenjeno', 'Odstranjeno'):
            if name in by_kind:
                msg.append(f'{name} / {en[name]}: {", ".join(by_kind[name])}')
        if by_kind:
            msg.append('')
        if not keys:
            msg += [f'PIS navaja ta akt kot podlago za {v["name"]}, vendar se zaradi njega ni spremenila nobena beseda',
                    'v besedilu, ki ga ima ta zapis.', '',
                    f'PIS names this act as the source of {v["name"]}, but no word of the text in this record changed.', '']
        if 'prečiščeno besedilo' in A['title'].lower():
            msg += ['Uradno prečiščeno besedilo ne spreminja vsebine zakona; spremembe v tem commitu so uredniške.', '',
                    'An official consolidated text does not change the law; the changes in this commit are editorial.', '']
        trailers = act_trailers(A, day)
        if affecting:
            trailers.append(f'Affecting: {affecting}')
        trailers += ['Cause-basis: ' + ('; '.join(sorted({ch['why'][k] for k in keys})) if keys else 'PIS names the act for this version')]
        trailers += [f'Source: {A["url"]}']
    else:
        author = PIS
        msg = [f'{short}: {", ".join(labels)} (sprememba brez pojasnila)' if len(labels) < 5 else
               f'{short}: {count(len(labels))} (sprememba brez pojasnila)', '',
               f'Neuradno prečiščeno besedilo v PIS ({v["name"]}) se je spremenilo tudi tam, kjer besedilo akta te',
               f'različice ({ul_label(A["ul"])} – {A["short"]}) teh določb ne omenja. Ta commit spremembe zato ne pripisuje',
               'nobenemu aktu. Gre za urejanje besedila v PIS (oblika prečiščenega besedila, prenos končnih določb,',
               'popravki). Prizadeto: ' + ', '.join(labels) + '.', '',
               f'PIS\'s consolidated text changed with {v["name"]} in places the text of that version\'s act does not',
               'name, so the change is not credited to any act. It is PIS\'s own editing of the consolidated text.', '']
        trailers = [f'In-force: {day}', f'Affecting: {affecting}', f'Version-act: {ul_label(A["ul"])} ({A["short"]})',
                    'Cause-basis: none; the version\'s act does not name these units']
    trailers += [f'Consolidated: {v["url"]}']
    if day < '1970-01-01':
        msg += PRE_1970
    return author, msg, trailers, keys


def write_repo(repo: Path, built: list[dict], docs: Path, today: str) -> tuple[list[dict], dict]:
    # The history is rebuilt from scratch each time (it is deterministic), keeping the remote it is pushed to. Git
    # marks its object files read-only, which Windows will not delete without clearing the flag first.
    remote = None
    if (repo / '.git').exists():
        out = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=repo, capture_output=True, text=True)
        remote = out.stdout.strip() or None

    def force(fn, path, _exc):
        os.chmod(path, 0o700)
        fn(path)
    if repo.exists():
        for p in repo.iterdir():
            shutil.rmtree(p, onexc=force) if p.is_dir() else p.unlink()
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'core.autocrlf', 'false')
    if remote:
        git(repo, 'remote', 'add', 'origin', remote)

    seq = [0]
    tags: dict[str, str] = {}
    switched = False
    log = []
    for day, ai, _, sop, c in plan_commits(built):
        b = c['b']
        slug = b['act']['slug']
        if day > today and not switched:
            # Changes already published but not yet in force live on their own branch, so main is the law today.
            git(repo, 'checkout', '-q', '-b', FUTURE_BRANCH)
            switched = True
        if c['kind'] == 'start':
            for key, u in b['versions'][0]['units'].items():
                write_unit(repo, slug, key, u)
            author, msg, trailers = start_message(b, day)
            keys = list(b['versions'][0]['units'])
        else:
            author, msg, trailers, keys = change_message(b, c['ch'], sop or None, day)
            for k in keys:
                write_unit(repo, slug, k, c['ch']['version']['units'].get(k))
        git(repo, 'add', '-A')
        when = commit_date(day, seq)
        env = {**os.environ, 'GIT_AUTHOR_NAME': author[0], 'GIT_AUTHOR_EMAIL': author[1], 'GIT_AUTHOR_DATE': when,
               'GIT_COMMITTER_NAME': COMMITTER[0], 'GIT_COMMITTER_EMAIL': COMMITTER[1], 'GIT_COMMITTER_DATE': when}
        git(repo, 'commit', '-q', '--allow-empty', '--cleanup=verbatim', '-F', '-', env=env,
            input='\n'.join(msg).rstrip('\n') + '\n\n' + '\n'.join(trailers) + '\n')
        head = git(repo, 'rev-parse', 'HEAD').strip()
        tags[f'{slug}/{day}'] = head
        if c['kind'] in ('law', 'start'):
            tags.setdefault(f'akt/{sop or b["info"]["sop"]}', head)
        log.append({'day': day, 'slug': slug, 'kind': c['kind'], 'sop': sop, 'author': author[0], 'units': len(keys),
                    'clamped': day < '1970-01-01'})
    for name, head in tags.items():
        git(repo, 'tag', '-f', name, head)
    if switched:
        git(repo, 'checkout', '-q', 'main')
    # Documentation, tables, the build scripts and the record of how it was made come last, by Lexifina, dated the
    # day the data was retrieved, so the same data gives the same hashes on any later day.
    for p in sorted(docs.rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            dest = repo / p.relative_to(docs)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())
    for name in ('build.py', 'reproduce.py', 'check_repo.py', 'test_repo.py'):
        (repo / 'tools' / name).write_bytes((HERE / name).read_bytes())
    write_tables(repo, built)
    from reproduce import write_manifest, write_reproduce
    write_manifest(repo, built, today)
    write_reproduce(repo, built, log, tags, REQUESTS, today)
    git(repo, 'add', '-A')
    when = commit_date(today, seq)
    env = {**os.environ, 'GIT_AUTHOR_NAME': COMMITTER[0], 'GIT_AUTHOR_EMAIL': COMMITTER[1], 'GIT_AUTHOR_DATE': when,
           'GIT_COMMITTER_NAME': COMMITTER[0], 'GIT_COMMITTER_EMAIL': COMMITTER[1], 'GIT_COMMITTER_DATE': when}
    git(repo, 'commit', '-q', '-m', f'Dokumentacija, tabele, orodja in REPRODUCE.md\n\nIn-force: {today}', env=env)
    if switched:
        git(repo, 'checkout', '-q', FUTURE_BRANCH)
        git(repo, 'merge', '-q', '--no-edit', 'main', env=env)
        git(repo, 'checkout', '-q', 'main')
    return log, tags


def write_tables(repo: Path, built: list[dict]):
    out = []
    for b in built:
        a = b['info']
        out.append({'predpis': b['act']['short'], 'uradni_list': a['ul'] or '', 'kratica': a['short'], 'naslov': a['title'],
                    'sop': a['sop'], 'sprejeto': a['adopted'] or '', 'objavljeno': a['published'] or '',
                    'velja_od': b['versions'][0]['from'], 'uporablja_od': a['applies'] or '', 'razlicica': 'Osnovni',
                    'enot': len(b['versions'][0]['units']), 'brez_pojasnila': 0, 'vir': a['url']})
        for ch in b['changes']:
            A = b['acts'][ch['act']]
            out.append({'predpis': b['act']['short'], 'uradni_list': A['ul'] or '', 'kratica': A['short'], 'naslov': A['title'],
                        'sop': A['sop'], 'sprejeto': A['adopted'] or '', 'objavljeno': A['published'] or '',
                        'velja_od': ch['from'], 'uporablja_od': A['applies'] or '', 'razlicica': ch['version']['name'],
                        'enot': len(ch['groups'].get(A['sop'], [])), 'brez_pojasnila': len(ch['groups'].get('unexplained', [])),
                        'vir': A['url']})
    out.sort(key=lambda r: (r['velja_od'], r['predpis'], r['sop']))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(out[0]), lineterminator='\n')
    w.writeheader()
    w.writerows(out)
    (repo / 'akti.csv').write_text(buf.getvalue(), encoding='utf-8', newline='\n')

    for b in built:
        act, a = b['act'], b['info']
        last = b['versions'][-1]
        counts: dict[str, int] = {}
        lastday: dict[str, str] = {}
        for ch in b['changes']:
            for keys in ch['groups'].values():
                for k in keys:
                    counts[k] = counts.get(k, 0) + 1
                    lastday[k] = ch['from']
        out = [f'# {a["title"]}', '', f'{act["short"]} · {ul_label(a["ul"])} · <{a["url"]}>', '',
               f'{len(b["versions"])} različic v PIS (izvirno besedilo in {len(b["versions"]) - 1} neuradnih prečiščenih '
               f'besedil), veljavnih od {b["versions"][0]["from"]} (zadnja od {last["from"]}).', '',
               '| Določba | Datoteka | Spremembe | Nazadnje spremenjeno |', '| --- | --- | ---: | --- |']
        for k in sorted(last['units'], key=unit_order):
            u = last['units'][k]
            out.append(f'| {unit_label(u)} | [{file_name(k)}]({file_name(k)}) | {counts.get(k, 0)} | {lastday.get(k, "")} |')
        (repo / act['slug'] / 'README.md').write_text('\n'.join(out) + '\n', encoding='utf-8', newline='\n')


# ---------------------------------------------------------------- main

def data_day() -> str:
    """The day the cached source data was retrieved (the newest file in the cache), so the documentation commit made by
    a rebuild on any later day carries the same date."""
    files = [p for p in CACHE.iterdir() if p.name != '.gitignore'] if CACHE.exists() else []
    if not files:
        return dt.date.today().isoformat()
    return dt.date.fromtimestamp(max(p.stat().st_mtime for p in files)).isoformat()


def build_all(offline: bool) -> list[dict]:
    return [build_act(a, offline) for a in ACTS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(ROOT.parent / 'slovenia-law'))
    ap.add_argument('--offline', action='store_true', help='read only the cache; fail on anything not cached')
    ap.add_argument('--today', default=None, help='the build day (default: the day the cached data was retrieved)')
    ap.add_argument('--verify-rebuild', action='store_true',
                    help='build again into a temporary folder from the cache, compare every hash with --repo, and record the result')
    args = ap.parse_args()
    if args.verify_rebuild:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([os.sys.executable, '-X', 'utf8', str(HERE / 'build.py'), '--offline', '--repo', tmp]
                                 + (['--today', args.today] if args.today else []), capture_output=True, text=True)
            if out.returncode:
                raise SystemExit(out.stderr)

            def hashes(r):
                log = git(Path(r), 'log', '--format=%H', 'main').split()
                tags = dict(l.split(' ', 1)[::-1] for l in git(Path(r), 'show-ref', '--tags').split('\n') if l)
                return log, tags
            a, b = hashes(args.repo), hashes(tmp)
            same_history = a[0][1:] == b[0][1:]
            rec = {'identical': same_history and a[1] == b[1], 'history_tip': a[0][1], 'commits': len(a[0]) - 1,
                   'tags': len(a[1]), 'main_identical': a[0][0] == b[0][0], 'main': a[0][0], 'rebuilt_main': b[0][0]}
            print(json.dumps(rec, indent=1))
            p = HERE / 'verification.json'
            ver = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
            ver['rebuild'] = {k: rec[k] for k in ('identical', 'history_tip', 'commits', 'tags')}
            p.write_text(json.dumps(ver, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
            # Git marks its objects read-only; clear the flag so the temporary folder can be removed on Windows.
            for f in Path(tmp).rglob('*'):
                os.chmod(f, 0o700)
            raise SystemExit(0 if rec['identical'] else 1)
    built = build_all(args.offline)
    today = args.today or data_day()
    for b in built:
        n = sum(len(ks) for ch in b['changes'] for ks in ch['groups'].values())
        print(f'{b["act"]["slug"]}: {len(b["versions"])} versions {b["versions"][0]["from"]}..{b["versions"][-1]["from"]}, '
              f'{len(b["versions"][-1]["units"])} units, {n} unit changes, {len(b["problems"])} unexplained')
        for p in b['problems']:
            print('   unexplained:', p)
    log, tags = write_repo(Path(args.repo), built, HERE / 'repo', today)
    print(f'repo: {len(log)} commits + 1 documentation commit, {len(tags)} tags -> {args.repo}')


if __name__ == '__main__':
    main()
