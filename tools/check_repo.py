"""Checks the git repository against the official text: every version of both acts in PIS (the text as enacted and
every consolidated text), read back from git, must equal that version.

    python -X utf8 scripts/slovenia-law/check_repo.py [--repo ../slovenia-law] [--no-record]

Two checks per version, from the cached PIS data (no network):
1. File by file: the act's files in git at the version's commit are exactly the files the build's parser makes from
   that version's data (same set of files, same bytes). The version's commit is the last commit whose
   `Consolidated:` trailer names that version; for the last version of each day it must also be the commit that
   tools/na_dan.py picks for that day from the `In-force:` trailers.
2. Word for word: the whole act as tools/na_dan.py prints it (or, for a version followed by another on the same day,
   its files in na_dan.py's order), with its markdown marks removed, has the same words in the same order as all the
   elements PIS gives for that version, read independently of the parser (every element except PIS's warning, its
   list of the acts the text comprises, the number of the consolidated text and the rules between final provisions).
The result is written to verification.json next to this script (unless --no-record), for REPRODUCE.md.
"""
import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

TOKEN = re.compile(r'\w+|[^\w\s]')


def official_words(elements: list[dict]) -> list[str]:
    words, skip = [], False
    for x in elements:
        s, v = x['struktura'], x['vsebina'] or ''
        if s in ('opozorilo', 'npb') or (s == 'napaka' and '<hr' in v.lower()):
            continue
        t = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'<br\s*/?>', ' ', v, flags=re.I))).replace(' ', ' ')
        if s == 'odstavek' and t.strip().endswith('obsega:'):
            skip = True
            continue
        if skip and s.startswith('alinea'):
            continue
        skip = False
        words += TOKEN.findall(t)
    return words


def repo_words(text: str) -> list[str]:
    return TOKEN.findall(' '.join(re.sub(r'^(#+ )', '', l) for l in text.split('\n')))


def git(repo: str, *args: str) -> str:
    return subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True, encoding='utf-8').stdout


def files_at(repo: str, commit: str, slug: str) -> dict[str, str]:
    """The act's files at a commit, read with one ls-tree and one cat-file --batch (not one git show per file)."""
    blobs = []
    for line in git(repo, 'ls-tree', '-r', commit, f'{slug}/').split('\n'):
        if not line:
            continue
        info, f = line.split('\t', 1)
        if f.endswith('.md') and not f.endswith('/README.md'):
            blobs.append((f[len(slug) + 1:], info.split()[2]))
    if not blobs:
        return {}
    data = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo, input=''.join(f'{sha}\n' for _, sha in blobs).encode(),
                          capture_output=True).stdout
    res, pos = {}, 0
    for name, _ in blobs:
        nl = data.index(b'\n', pos)
        size = int(data[pos:nl].split()[2])
        res[name] = data[nl + 1:nl + 1 + size].decode('utf-8')
        pos = nl + 1 + size + 1
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=str(build.ROOT.parent / 'slovenia-law'))
    ap.add_argument('--no-record', action='store_true')
    args = ap.parse_args()
    sys.path.insert(0, str(Path(args.repo) / 'tools'))
    import na_dan
    built = build.build_all(offline=True)
    # Each version's commit: the last commit (newest first in the log) whose Consolidated trailer names it.
    by_url: dict[str, str] = {}
    for line in git(args.repo, 'log', '--format=%H%x09%(trailers:key=Consolidated,valueonly,separator=)', 'main').splitlines():
        h, _, url = line.partition('\t')
        if url.strip():
            by_url.setdefault(url.strip(), h)
    versions = files = bad = words = wbad = 0
    per_act, inside = {}, {}
    for b in built:
        slug = b['act']['slug']
        for i, v in enumerate(b['versions']):
            expected = {build.file_name(k): u['text'] for k, u in v['units'].items()}
            commit = by_url.get(v['url'], '')
            got = files_at(args.repo, commit, slug) if commit else {}
            versions += 1
            per_act[slug] = per_act.get(slug, 0) + 1
            files += len(expected)
            last_of_day = i + 1 == len(b['versions']) or b['versions'][i + 1]['from'] != v['from']
            if not last_of_day:
                inside.setdefault(slug, []).append(f'{v["name"]} {v["from"]}')
            if got != expected:
                bad += 1
                diff = sorted(set(got) ^ set(expected)) or [k for k in expected if got.get(k) != expected[k]]
                print(f'MISMATCH {slug} {v["name"]} {v["from"]}: {diff[:5]}')
            words += 1
            ow = official_words(v['elements'])
            if last_of_day:
                cwd = Path.cwd()
                try:
                    import os
                    os.chdir(args.repo)
                    on_day = na_dan.commit_on(v['from'], slug)
                finally:
                    os.chdir(cwd)
                if on_day != commit:
                    bad += 1
                    print(f'ON-DATE {slug} {v["name"]} {v["from"]}: na_dan picks {on_day[:10]}, version commit {commit[:10]}')
                out = subprocess.run([sys.executable, 'tools/na_dan.py', v['from'], slug], cwd=args.repo,
                                     capture_output=True, text=True, encoding='utf-8')
                whole = out.stdout if not out.returncode else ''
            else:
                whole = ''.join(got[f] + '\n' for f in sorted(got, key=lambda f: na_dan.order(f'{slug}/{f}')))
            rw = repo_words(whole)
            if ow != rw:
                wbad += 1
                k = next((k for k, (a, c) in enumerate(zip(ow, rw)) if a != c), min(len(ow), len(rw)))
                print(f'WORDS {slug} {v["name"]} {v["from"]}: official {len(ow)} vs repo {len(rw)} words; first difference at '
                      f'{k}: {" ".join(ow[max(0, k - 5):k + 5])!r} / {" ".join(rw[max(0, k - 5):k + 5])!r}')
    print(f'{versions} versions checked ({files} files), {bad} mismatches; {words} versions word for word, {wbad} mismatches')
    print('per act:', per_act, 'versions followed by another on the same day:', inside)
    if not args.no_record:
        p = HERE / 'verification.json'
        rec = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
        rec['check'] = {'versions': versions, 'files': files, 'mismatches': bad, 'wordcheck': words, 'word_mismatches': wbad,
                        'per_act': per_act, 'inside_days': inside}
        p.write_text(json.dumps(rec, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    raise SystemExit(1 if bad or wbad else 0)


if __name__ == '__main__':
    main()
