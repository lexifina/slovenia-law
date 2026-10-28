"""Writes data/razlicice.json, corpus.json and REPRODUCE.md into the Slovenian law repository, from the facts of the
build that made it. Called by build.py; kept apart so the record of how the repository was made reads as one document.

The results of the checks (check_repo.py, test_repo.py, and the rebuild that compares hashes) are read from
verification.json next to this file, which those scripts and `build.py --verify-rebuild` write. They describe the build
before the one that writes this file, from the same data; a rebuild with the same data and the same verification.json
gives the same hashes."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def write_manifest(repo: Path, built: list[dict], today: str):
    """Every source file the text comes from, with its sha256, so a rebuild can show it read the same bytes; and the
    corpus description the global superproject reads."""
    out = {'built': today, 'source': 'https://pisrs.si', 'acts': [{
        'id': b['act']['id'], 'slug': b['act']['slug'], 'title': b['info']['title'], 'sop': b['info']['sop'],
        'relations': b['relations_url'],
        'versions': [{'name': v['name'], 'npb_id': v['npb_id'], 'in_force': v['from'], 'act': v['sop'], 'json': v['url'],
                      'sha256': v['sha256']} for v in b['versions']],
        'amending_acts': [{'sop': a['sop'], 'id': a['id'], 'ul': a['ul'], 'short': a['short'], 'title': a['title'],
                           'adopted': a['adopted'], 'published': a['published'], 'in_force': a['in_force'],
                           'applies': a['applies'], 'text': a['text_url']}
                          for a in sorted(b['acts'].values(), key=lambda a: a['sop'])],
    } for b in built]}
    (repo / 'data').mkdir(exist_ok=True)
    (repo / 'data' / 'razlicice.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    corpus = {
        'corpus': 'si/national/acts',
        'name': 'Ustava Republike Slovenije in Zakon o volitvah v državni zbor',
        'acts': [b['act']['slug'] for b in built],
        'history_from': min(b['versions'][0]['from'] for b in built),
        'built': today,
        'dates': {'commit': 'in-force', 'other_trailers': ['Adopted', 'Published', 'Applies-from', 'Date-note'],
                  'time': '12:00 Europe/Ljubljana'},
        'scope': {
            'trailer': 'Applies',
            'when_absent': 'no scope note is recorded in this corpus (transitional provisions are kept as text, not parsed); '
                           'not a statement that the change reaches every case',
            'default_reach': {
                'rule': 'prohibition of retroactive effect',
                'meaning': 'laws, regulations and general acts cannot have retroactive effect; only a law may provide that '
                           'some of its provisions have retroactive effect, where the public interest requires it and '
                           'acquired rights are not infringed',
                'authority': 'Ustava Republike Slovenije, 155. člen (Uradni list RS, št. 33/91-I)',
                'decided_here': False,
            },
        },
        'tool': 'tools/na_dan.py',
    }
    (repo / 'corpus.json').write_text(json.dumps(corpus, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def write_reproduce(repo: Path, built: list[dict], log: list[dict], tags: dict, requests: list[dict], today: str):
    blob = subprocess.run(['git', 'hash-object', str(HERE / 'build.py')], capture_output=True, text=True).stdout.strip()
    pyv = subprocess.run(['python', '--version'], capture_output=True, text=True).stdout.strip()
    gitv = subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip()
    ver = json.loads((HERE / 'verification.json').read_text(encoding='utf-8')) if (HERE / 'verification.json').exists() else {}
    files = {r['file'] for r in requests if r['file'].exists()}
    days = sorted({dt.date.fromtimestamp(f.stat().st_mtime).isoformat() for f in files})
    urls = {r['url'] for r in requests}
    kinds = {'register': sum('/zbirka/id/' in u or '/zbirka/sop/' in u for u in urls),
             'relations': sum('/povezave/' in u for u in urls),
             'texts': sum('/neuradno-precisceno-besedilo/' in u for u in urls)}
    n_law = sum(1 for c in log if c['kind'] == 'law')
    n_empty = sum(1 for c in log if c['kind'] == 'law' and not c['units'])
    n_unexp = sum(1 for c in log if c['kind'] == 'unexplained')
    n_start = sum(1 for c in log if c['kind'] == 'start')
    unexplained_units = sum(len(b['problems']) for b in built)
    n_changes = sum(c['units'] for c in log if c['kind'] != 'start')
    whys: dict[str, int] = {}
    for b in built:
        for ch in b['changes']:
            for k, w in ch['why'].items():
                if ch['groups'].get('unexplained') and k in ch['groups']['unexplained']:
                    continue
                whys[w] = whys.get(w, 0) + 1
    why_rows = '\n'.join(f'  - {w}: {n}' for w, n in sorted(whys.items(), key=lambda x: -x[1]))
    rows = '\n'.join(
        f'| {b["act"]["short"]} | `{b["act"]["id"]}` | {b["info"]["title"]} | {len(b["versions"])} | '
        f'{b["versions"][0]["from"]} to {b["versions"][-1]["from"]} | {len(b["versions"][-1]["units"])} |' for b in built)
    unexp_rows = '\n'.join(f'| {b["act"]["short"]} | {p.split(" ", 1)[0]} | {p.split(" ", 1)[1]} |'
                           for b in built for p in b['problems'])
    retrieved = ', '.join(days) if days else today
    chk = ver.get('check', {})
    det = ver.get('rebuild', {})
    smoke = ver.get('smoke', {})
    check_line = (f'`{chk["versions"]} versions checked ({chk["files"]} files), {chk["mismatches"]} mismatches; '
                  f'{chk["wordcheck"]} versions word for word against all of PIS\'s words for that version, '
                  f'{chk["word_mismatches"]} mismatches`' if chk else '(not yet run)')
    rebuild_line = (f'A second build from the same cache into an empty folder gave the same history: the last law commit '
                    f'was `{det["history_tip"]}` in both, and every one of the {det["commits"]} law commits and {det["tags"]} '
                    f'tags had the same hash.' if det.get('identical') else '(not yet run)')
    smoke_rows = '\n'.join(f'| {t["name"]} | {"pass" if t["ok"] else "FAIL"} | {t["detail"]} |' for t in smoke.get('tests', []))
    smoke_line = (f'{sum(t["ok"] for t in smoke["tests"])} of {len(smoke["tests"])} tests passed:\n\n| Test | Result | Detail |\n'
                  f'| --- | --- | --- |\n{smoke_rows}' if smoke else '(not yet run)')

    text = f"""# How this history was made, and how to make it again

This file records exactly how the repository was built: the sources, the commands, the software, the decisions made
by hand, and what an AI model did and did not do. The build writes it, so it describes the build that made this
commit.

## Short version

```sh
git clone https://github.com/lexifina/slovenia-law && cd slovenia-law
python -X utf8 tools/build.py --repo ../rebuilt --today {today}
git -C ../rebuilt rev-parse main        # the same hash as this repository's main
python -X utf8 tools/check_repo.py --repo ../rebuilt --no-record
python -X utf8 tools/test_repo.py --repo ../rebuilt --no-record
```

`tools/build.py` needs Python 3.12 or later (standard library only) and git. It reads PIS (or its own cache, `.cache/`
next to the script) and writes this repository into `--repo`. With the same PIS data and the same `--today` it gives
the same commits with the same hashes. `data/razlicice.json` lists every version it read with the sha256 of PIS's
JSON, so a rebuild can show it read the same bytes; PIS may change its data, and then the hashes change too.

## Sources

All legal text and all information about versions and amending acts come from **PIS**, Pravno-informacijski sistem
Republike Slovenije (https://pisrs.si), maintained by the Government Office for Legislation (Služba Vlade Republike
Slovenije za zakonodajo). Nothing was typed in, summarised or rewritten. PIS's website is a single-page application;
its data comes from a JSON interface at `https://pisrs.si/api`, which the build reads directly (the addresses were
found in the application's own JavaScript). The build read {kinds['register']} register entries,
{kinds['relations']} relation lists and {kinds['texts']} texts:

| What | Where |
| --- | --- |
| Each act's register entry: title, Uradni list number, adopted, published, in force (veljaOd), applies (uporabljaOd), and the ids of the text as enacted ("Osnovni") and of each consolidated text (NPB) | `https://pisrs.si/api/rezultat/zbirka/id/<ID>`, and `/zbirka/sop/<SOP>` for the amending acts |
| Which act produced each consolidated text (`neuradnoPreciscenoBesedilo[].sopNPBPosega`) | `https://pisrs.si/api/povezave/med-si-akti/<register element id>` |
| The text of each version, and of each amending act as enacted, as a list of elements (title, chapter, člen, paragraph, item) | `https://pisrs.si/api/rezultat/neuradno-precisceno-besedilo/<text id>`, listed with sha256 in `data/razlicice.json` |

| Act | PIS id | Title | Versions | In force from | Units today |
| --- | --- | --- | ---: | --- | ---: |
{rows}

The data was retrieved on {retrieved}, one request at a time with a pause of at least 0.7 seconds, with the user agent
`lexifina-watch/1.0 (+https://lexifina.com/watch; corpus@lexifina.com)`. PIS's robots.txt allows everything except
`/iskanje`. The website asks a browser to solve a small proof-of-work puzzle (`/api/a`) only after an error; the build
never needed or used it.

## The build, step by step

1. `python -X utf8 scripts/slovenia-law/build.py --today {today}` in Lexifina's own repository fetched the data into its
   cache and wrote this repository. `tools/build.py` here is the same file as `scripts/slovenia-law/build.py` there
   (git blob `{blob}`), with `tools/reproduce.py`, which writes this file, `tools/check_repo.py` and `tools/test_repo.py`.
2. `python -X utf8 scripts/slovenia-law/check_repo.py` read every version of both acts back from this repository with
   `tools/na_dan.py`, on the day it took effect, and compared it file by file with the text parsed afresh from the
   cached JSON; then it compared the whole act, word for word, with all the words PIS gives for that version (without
   PIS's warning, its list of the acts the text comprises, and the number of the consolidated text). Result:
   {check_line}.
3. `python -X utf8 scripts/slovenia-law/test_repo.py` ran the functional tests below against this repository.
4. `python -X utf8 scripts/slovenia-law/build.py --offline --verify-rebuild` built the repository a second time from the
   same cache into a temporary folder and compared the hashes. {rebuild_line}
5. The build was run once more (`--offline`) to write these results into this file, and the final `main` was rebuilt
   again in a temporary folder and compared hash for hash before it was force-pushed to the private GitHub repository
   `lexifina/slovenia-law` (which held only a placeholder commit describing the sources before).

It ran with {pyv} and {gitv} on Windows 11. No network service other than PIS is involved.

### Functional tests (`tools/test_repo.py`)

{smoke_line}

## How the text and the commits are derived

Everything below is done by `tools/build.py`, deterministically.

- **Text.** Each act is a folder (`urs/`, `zvdz/`). Each člen is one file, `clen-068.md`, `clen-003a.md` (Article 3.a).
  The chapter and section headings that begin with a člen are `##` lines at the top of its file; the člen number and
  its subject ("(prepoved povratne veljave pravnih aktov)") are the `#` line; each paragraph (odstavek), indent (alineja)
  and numbered point (točka) is one line. `naslov.md` holds the title, `uvod.md` the preamble and `podpis.md` the place,
  date, number and signatures of the text as enacted; `koncne/<SOP>.md` holds the transitional and final provisions of
  an amending act that PIS prints after the act (`koncne/1997-01-2341.md`), named by the act's SOP number.
- **Left out.** PIS's warning that a consolidated text is for information only, its list of the acts a consolidated
  text comprises (they are in the commits), the line giving the number of the consolidated text, and the rules PIS
  draws between the final provisions of different acts.
- **Normalised.** HTML tags are removed (a line break counts as a space), entities decoded and runs of white space made
  one space. Every other character is kept as PIS has it, so PIS's corrections of misprints are changes in the record.
  No U+FFFD (replacement character) occurs in the data.
- **Changes.** Consecutive versions are compared file by file. {n_changes} changes of a file were found.
- **Cause.** PIS's register names, for each consolidated text, the one act whose entry into force produced it; in
  both acts every consolidated text is produced by exactly one act. A changed file is credited to that act only on one
  of these grounds, each written in the code:
{why_rows}

  {unexplained_units} file changes are explained by none of these, and are never credited to an act (below).
- **Date.** The day the act took effect (veljaOd in the register). Where the register has none (two Constitutional
  Court decisions and the official consolidated text ZVDZ-UPB1), the day of publication, said in `Date-note:`.
- **Commits.** One for the text as enacted of each act ({n_start}), one per act and amending act ({n_law}, of which
  {n_empty} change no words), and one per act and day for the changes no amending act explains ({n_unexp}), in the
  order they took effect, then one for this documentation.
  - The author is the amending act, `Uradni list RS, št. 42/97 (UZS68)`, at an address made of the act's PIS id
    (`ustz2@pisrs.invalid`). Constitutional Court decisions are `odl. US`, as in PIS's citations.
  - Unexplained changes are by `PIS RS (neuradno prečiščeno besedilo)` and say "sprememba brez pojasnila" in the subject.
  - Author and committer dates are noon in Ljubljana on the day the change took effect (CET/CEST, the summer-time rules
    written into the code). The committer is `Lexifina <slovenia-law@lexifina.com>`. No date is before 1970.
  - The message has the act's full title, the units it inserted, amended or removed, and the trailers `Adopted:`,
    `Published:`, `In-force:`, `Applies-from:` (when the register gives a later day of application), `Date-note:`,
    `Affecting:`, `Cause-basis:` (why each unit is credited), `Source:` (the act in PIS) and `Consolidated:` (the
    exact data the version came from).
  - Tags: each act's days (`urs/1997-07-14`) and each amending act (`akt/1997-01-2341`, by SOP number).
- **Documentation commit.** Dated {today}, the day the data was retrieved, not the day of the run, so a later rebuild
  of the same data gives the same hash. It adds `corpus.json`, `akti.csv`, `data/razlicice.json`, the tools and this file.

## Changes no amending act explains

| Act | In force | Version and unit |
| --- | --- | --- |
{unexp_rows}

They fall into three groups. (1) The first consolidated text of each act differs from the text as enacted: PIS left
out the preamble and the signatures, wrote the title in the nominative ("USTAVA" for "USTAVO"), moved the act's own
final provisions after the act, and corrected misprints and punctuation in a handful of articles. (2) The Constitution
in 2021 (NPB 11) and the ZVDZ in 2024 (NPB 12): PIS stopped printing the final provisions of the amending acts after
the act and put the act's own final articles back in place. (3) Nothing else: every other change is named by its act.

## Decisions made by hand

These choices were made when the tool was written, after looking at the data. They are in the code.

1. **The acts.** The Constitution, because it is the act readers ask about first and PIS has every version since 1991,
   each produced by one constitutional act; and the National Assembly Elections Act, because it is amended often (by
   laws, Constitutional Court decisions, a constitutional act and an official consolidated text), has every version
   since its enactment in 1992 in PIS, and matches the election law chosen for Lexifina's Estonian record.
2. **The register's veljaOd is the in-force day.** The amending acts' own commencement clauses were not parsed.
3. **A change the act's text does not name is never credited to the act**, even though PIS names that act for the
   version: it is committed separately by PIS and labelled.
4. **A replacement in the whole text** ("v celotnem besedilu ... v ustreznih sklonih") explains a change only when
   applying it to the old text, word stem for word stem, gives exactly the new text.
5. **UZ148** (Uradni list RS, št. 47/13): PIS has no text of this constitutional act; its title ("o spremembi 148. člena")
   is the evidence for the one article it changed, said in `Cause-basis:`.
6. **The official consolidated text ZVDZ-UPB1** (Uradni list RS, št. 109/06) restates the whole act; the changes PIS
   shows with it are credited to it and described as editorial.
7. **Slovenian only.** Slovenian is the official language; PIS's English translations are not official.

## What an AI model did

This repository was built on {today} in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5**
(model id `claude-opus-5-5`), working from a brief by the user at Lexifina: a private "git for law" repository for
Slovenia to the same standard as Lexifina's other corpora (Estonia, Liechtenstein, Luxembourg, Switzerland, the UK,
the US Code and the Grundgesetz).

The model:

- **Researched the source:** PIS's website and the JSON interface behind it, the shape of its data, its terms of use,
  and prior art (below).
- **Wrote all the code and text in this repository:** `tools/build.py`, `tools/reproduce.py`, `tools/check_repo.py`,
  `tools/test_repo.py`, `tools/na_dan.py`, the README, this file and the licence, and chose the design described in them.
- **Ran the commands above** and checked the results.

The model did **not**:

- **Write or edit any legal text.** Every word of every provision, every date and every act's title is copied by the
  script from PIS.
- **Take part in building the history.** No AI model is called when the history is built or checked.

The user decided what was in scope and decides whether the repository is ever made public. The work was not reviewed
line by line by a lawyer. PIS itself says that consolidated texts are an informative working aid only; only the
Uradni list Republike Slovenije is authoritative.

## Prior art

- [legalize-dev](https://github.com/legalize-dev) publishes consolidated-version histories for many countries
  (one commit per consolidated version, credited to a generic author). At the time of this build it had no Slovenian
  parser or repository; nothing was taken from it.
- Lexifina's other corpora, whose rules this one follows, especially the Liechtenstein and Estonian builders, from which
  the structure of `build.py`, `check_repo.py` and the on-date tool was adapted.
"""
    (repo / 'REPRODUCE.md').write_text(text, encoding='utf-8', newline='\n')
