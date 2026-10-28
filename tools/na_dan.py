"""Prints an act, or one provision of it, as it stood on a given day, from this repository's history.

    python tools/na_dan.py 2003-01-01 urs 68          # Article 68 of the Constitution on 1 January 2003
    python tools/na_dan.py 2003-01-01 urs 3a          # Article 3.a (inserted in 2003)
    python tools/na_dan.py 1995-01-01 zvdz            # the whole National Assembly Elections Act on 1 January 1995
    python tools/na_dan.py 2000-01-01 urs naslov      # the title; also uvod, podpis, koncne/1997-01-2341

Each commit carries the day its change took effect in an `In-force:` trailer, which is the source of truth (git cannot
store dates before 1970, and a commit date is noon local time). The text in force on a day is the last commit on or
before it that touches the act. Changes published but not yet in force would be on the branch "prihodnje"; a date
after today reads from there. Standard library only.
"""
import datetime as dt
import re
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def order(path: str) -> tuple:
    """The order of an act's files: preamble, title, articles by number, signatures, final provisions of amending acts."""
    name = path.split('/', 1)[1]
    if name == 'uvod.md':
        return (0, 0, '', '')
    if name == 'naslov.md':
        return (1, 0, '', '')
    m = re.fullmatch(r'clen-(\d+)([a-z]?)(.*)\.md', name)
    if m:
        return (2, int(m.group(1)), m.group(2), m.group(3))
    if name == 'podpis.md':
        return (3, 0, '', '')
    return (4, 0, '', name)


def file_for(key: str) -> str:
    m = re.fullmatch(r'(\d+)\.?([a-z]?)', key)
    if m:
        return f'clen-{int(m.group(1)):03d}{m.group(2)}.md'
    return key if key.endswith('.md') else f'{key}.md'


def commit_on(day: str, act: str) -> str:
    branch = 'prihodnje' if day > dt.date.today().isoformat() and git('branch', '--list', 'prihodnje').strip() else 'main'
    out = git('log', '--format=%H%x09%(trailers:key=In-force,valueonly,separator=)', branch, '--', f'{act}/')
    for line in out.splitlines():
        h, _, d = line.partition('\t')
        if d.strip() and d.strip() <= day:
            return h
    return ''


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, act = sys.argv[1], sys.argv[2]
    dt.date.fromisoformat(day)
    commit = commit_on(day, act)
    if not commit:
        sys.exit(f'{act} is not in the record on {day}.')
    if len(sys.argv) > 3:
        name = file_for(sys.argv[3])
        try:
            sys.stdout.write(git('show', f'{commit}:{act}/{name}'))
        except subprocess.CalledProcessError:
            sys.exit(f'{act}/{name} was not in the text on {day}.')
        return
    files = [f for f in git('ls-tree', '-r', '--name-only', commit, f'{act}/').split('\n')
             if f.endswith('.md') and not f.endswith('/README.md')]
    for f in sorted(files, key=order):
        sys.stdout.write(git('show', f'{commit}:{f}') + '\n')


if __name__ == '__main__':
    main()
