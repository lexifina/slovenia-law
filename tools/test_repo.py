"""Functional tests of the Slovenian law repository: what a reader does with it, run against the built repository.

    python -X utf8 scripts/slovenia-law/test_repo.py [--repo ../slovenia-law] [--no-record]

Standard library only, and it does not import the builder: everything it knows comes from the repository itself
(the README, the history, the trailers and data/razlicice.json). The results are written to verification.json next to
this script (unless --no-record), for REPRODUCE.md.
"""
import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS: list[dict] = []
LAW_MAIL = re.compile(r'^[a-z0-9]+@pisrs\.invalid$')


def run(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), cwd=repo, capture_output=True, text=True, encoding='utf-8')


def git(repo: str, *args: str) -> str:
    out = run(repo, 'git', *args)
    if out.returncode:
        raise AssertionError(f'git {" ".join(args)}: {out.stderr.strip()}')
    return out.stdout


def na_dan(repo: str, day: str, act: str, unit: str | None = None) -> subprocess.CompletedProcess:
    return run(repo, sys.executable, 'tools/na_dan.py', day, act, *([unit] if unit else []))


def test(name: str):
    def wrap(fn):
        def inner(repo):
            try:
                detail = fn(repo)
                RESULTS.append({'name': name, 'ok': True, 'detail': detail})
            except AssertionError as exc:
                RESULTS.append({'name': name, 'ok': False, 'detail': str(exc)[:300]})
        inner.__name__ = fn.__name__
        return inner
    return wrap


def is_law(name: str, mail: str) -> bool:
    return bool(LAW_MAIL.match(mail)) and mail != 'pis@pisrs.invalid' and name.startswith('Uradni list RS')


@test('git blame on a changed provision names a law')
def t_blame(repo):
    out = git(repo, 'blame', '--line-porcelain', 'urs/clen-068.md')
    pairs = re.findall(r'^author (.+)\nauthor-mail <([^>]+)>', out, re.M)
    lines = {}
    for (name, mail), text in zip(pairs, re.findall(r'^\t(.*)$', out, re.M)):
        lines[text] = (name, mail)
    tujci = [v for t, v in lines.items() if t.startswith('Tujci lahko pridobijo lastninsko pravico')]
    assert tujci and is_law(*tujci[0]), f'line on foreigners\' property not credited to a law: {tujci}'
    laws = sorted({n for n, m in pairs if is_law(n, m)})
    assert laws, 'no line of urs/clen-068.md is credited to a law'
    return f'urs/clen-068.md: "Tujci lahko pridobijo ..." by {tujci[0][0]}; authors {laws}'


@test('the on-date tool gives the text before and after a known amendment')
def t_on_date(repo):
    before = na_dan(repo, '1997-07-13', 'urs', '68')
    after = na_dan(repo, '1997-07-14', 'urs', '68')
    assert before.returncode == 0 and after.returncode == 0, before.stderr + after.stderr
    assert 'Tujci lahko pridobijo lastninsko pravico' not in before.stdout, 'new wording already there on 1997-07-13'
    assert 'Tujci lahko pridobijo lastninsko pravico' in after.stdout, 'UZS68 wording missing on 1997-07-14'
    assert 'Na zemljiščih tujci ne morejo pridobiti lastninske pravice' in before.stdout, 'original wording missing before'
    ins = na_dan(repo, '2003-03-06', 'urs', '3a'), na_dan(repo, '2003-03-07', 'urs', '3a')
    assert ins[0].returncode != 0 and ins[1].returncode == 0, 'Article 3.a should appear on 2003-03-07, not before'
    return 'URS 68: original wording on 1997-07-13, UZS68 wording on 1997-07-14; URS 3.a absent 2003-03-06, present 2003-03-07'


@test('every law commit: its words are in force on its day and not the day before')
def t_every_change(repo):
    """For every article a law commit changed: tools/na_dan.py's choice of commit for the in-force day gives the new
    text, and for the day before gives the text before that day. The reader's own commit_on() picks the commit (once per
    act and day); file contents are read with one ls-tree and one cat-file --batch per commit. A file changed again
    later on the same day is checked only at its last change that day."""
    import os
    sys.path.insert(0, str(Path(repo) / 'tools'))
    import na_dan as reader
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        on: dict[tuple, str] = {}
        trees: dict[str, dict] = {}

        def commit_on(day, act):
            if (day, act) not in on:
                on[(day, act)] = reader.commit_on(day, act)
            return on[(day, act)]

        def text(commit, path):
            if not commit:
                return None
            if commit not in trees:
                blobs = [l.split('\t', 1) for l in git(repo, 'ls-tree', '-r', commit).split('\n') if l]
                blobs = [(f, info.split()[2]) for info, f in blobs if f.endswith('.md')]
                data = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo, capture_output=True,
                                      input=''.join(f'{b}\n' for _, b in blobs).encode()).stdout
                res, pos = {}, 0
                for f, _ in blobs:
                    nl = data.index(b'\n', pos)
                    size = int(data[pos:nl].split()[2])
                    res[f] = data[nl + 1:nl + 1 + size].decode('utf-8')
                    pos = nl + 1 + size + 1
                trees[commit] = res
            return trees[commit].get(path)

        log = git(repo, 'log', '--reverse', '--name-only',
                  '--format=@@%H%x09%ae%x09%(trailers:key=In-force,valueonly,separator=)', 'main')
        commits = []
        for block in log.split('@@')[1:]:
            head, *names = [l for l in block.split('\n') if l.strip()]
            h, mail, day = (head.split('\t') + ['', ''])[:3]
            commits.append((h, mail, day.strip(), names))
        first_day = {}
        for h, mail, day, names in commits:
            for f in names:
                if day:
                    first_day.setdefault(f.split('/')[0], day)
        n = 0
        for i, (h, mail, day, names) in enumerate(commits):
            if not day or not LAW_MAIL.match(mail) or mail == 'pis@pisrs.invalid':
                continue
            prev_day = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
            for f in names:
                if not re.search(r'/clen-\d+[a-z]?\.md$', f):
                    continue
                if any(d == day and f in nm for _, _, d, nm in commits[i + 1:]):
                    continue
                act = f.split('/')[0]
                assert text(commit_on(day, act), f) == text(h, f), f'{f} on {day} differs from commit {h[:10]}'
                before = [c for c, _, d, _ in commits[:i] if d and d < day]
                old = text(before[-1], f) if before else None
                if prev_day >= first_day[act]:
                    assert text(commit_on(prev_day, act), f) == old, f'{f} on {prev_day} is not the text before {h[:10]}'
                n += 1
    finally:
        os.chdir(cwd)
    assert n > 0, 'no law commit changed an article'
    return f'{n} article changes checked on their in-force day and the day before'


@test('git log --follow on a file lists its amending laws in date order')
def t_follow(repo):
    out = git(repo, 'log', '--follow', '--reverse', '--format=%an%x09%ae%x09%(trailers:key=In-force,valueonly,separator=)',
              'urs/clen-068.md')
    rows = [l.split('\t') for l in out.splitlines() if l]
    days = [r[2] for r in rows]
    assert days == sorted(days), f'not in date order: {days}'
    laws = [r[0] for r in rows if is_law(r[0], r[1])]
    assert any('UZS68' in l for l in laws) and any('UZ3a' in l for l in laws), f'expected UZS68 and UZ3a: {laws}'
    return 'urs/clen-068.md: ' + '; '.join(f'{r[2]} {r[0]}' for r in rows)


@test('every tag resolves and every history commit has an In-force trailer')
def t_tags_trailers(repo):
    tags = git(repo, 'tag', '--list').split()
    for t in tags:
        git(repo, 'rev-parse', '--verify', f'{t}^{{commit}}')
    branches = ['main'] + (['prihodnje'] if git(repo, 'branch', '--list', 'prihodnje').strip() else [])
    missing, unparsed, total = [], [], 0
    docs = git(repo, 'rev-parse', 'main').strip()
    for b in branches:
        for h in git(repo, 'rev-list', b).split():
            if h == docs:
                continue
            msg = git(repo, 'log', '-1', '--format=%B', h)
            parsed = subprocess.run(['git', 'interpret-trailers', '--parse'], cwd=repo, input=msg, capture_output=True,
                                    text=True, encoding='utf-8').stdout
            total += 1
            if not re.search(r'^In-force: \d{4}-\d{2}-\d{2}$', parsed, re.M):
                (unparsed if re.search(r'^In-force:', msg, re.M) else missing).append(h[:10])
    assert not missing and not unparsed, f'without In-force: {missing}; trailer block not parsed: {unparsed}'
    return f'{len(tags)} tags resolve; {total} history commits all carry a parseable In-force trailer (the documentation commit has none)'


@test('no commit is authored by Lexifina except the documentation commit')
def t_authors(repo):
    rows = [l.split('\t') for l in git(repo, 'log', '--format=%H%x09%an%x09%ae%x09%cn%x09%ce', 'main').splitlines()]
    lex = [r for r in rows if r[1] == 'Lexifina' or 'lexifina' in r[2]]
    assert len(lex) == 1 and lex[0][0] == rows[0][0], f'Lexifina-authored commits: {[r[0][:10] for r in lex]}'
    assert all(r[3] == 'Lexifina' and r[4] == 'slovenia-law@lexifina.com' for r in rows), 'a committer is not Lexifina'
    kinds = {'law': sum(is_law(r[1], r[2]) for r in rows), 'PIS': sum(r[2] == 'pis@pisrs.invalid' for r in rows)}
    assert kinds['law'] + kinds['PIS'] + 1 == len(rows), 'an author is neither a law, PIS nor the documentation'
    return f'{len(rows)} commits: {kinds["law"]} by laws, {kinds["PIS"]} by PIS (unexplained), 1 documentation commit by Lexifina'


@test('the README\'s git commands run')
def t_readme(repo):
    readme = (Path(repo) / 'README.md').read_text(encoding='utf-8')
    cmds = [c for c in re.findall(r'^\|[^|]*\| `([^`]+)` \|$', readme, re.M)]
    assert cmds, 'no commands found in the README table'
    for c in cmds:
        out = run(repo, *[sys.executable if a == 'python' else a for a in shlex.split(c)])
        assert out.returncode == 0 and out.stdout.strip(), f'{c}: exit {out.returncode}, {out.stderr.strip()[:200]}'
    return f'{len(cmds)} commands from the README table ran with output: ' + '; '.join(f'`{c}`' for c in cmds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(HERE.parents[1].parent / 'slovenia-law'))
    ap.add_argument('--no-record', action='store_true')
    args = ap.parse_args()
    for t in (t_blame, t_on_date, t_every_change, t_follow, t_tags_trailers, t_authors, t_readme):
        t(args.repo)
    for r in RESULTS:
        print(('PASS ' if r['ok'] else 'FAIL ') + r['name'] + ': ' + r['detail'])
    if not args.no_record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['smoke'] = {'tests': RESULTS}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(0 if all(r['ok'] for r in RESULTS) else 1)


if __name__ == '__main__':
    main()
