# How this history was made, and how to make it again

This file records exactly how the repository was built: the sources, the commands, the software, the decisions made
by hand, and what an AI model did and did not do. The build writes it, so it describes the build that made this
commit.

## Short version

```sh
git clone https://github.com/lexifina/slovenia-law && cd slovenia-law
python -X utf8 tools/build.py --repo ../rebuilt --today 2026-10-28
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
found in the application's own JavaScript). The build read 25 register entries,
2 relation lists and 48 texts:

| What | Where |
| --- | --- |
| Each act's register entry: title, Uradni list number, adopted, published, in force (veljaOd), applies (uporabljaOd), and the ids of the text as enacted ("Osnovni") and of each consolidated text (NPB) | `https://pisrs.si/api/rezultat/zbirka/id/<ID>`, and `/zbirka/sop/<SOP>` for the amending acts |
| Which act produced each consolidated text (`neuradnoPreciscenoBesedilo[].sopNPBPosega`) | `https://pisrs.si/api/povezave/med-si-akti/<register element id>` |
| The text of each version, and of each amending act as enacted, as a list of elements (title, chapter, člen, paragraph, item) | `https://pisrs.si/api/rezultat/neuradno-precisceno-besedilo/<text id>`, listed with sha256 in `data/razlicice.json` |

| Act | PIS id | Title | Versions | In force from | Units today |
| --- | --- | --- | ---: | --- | ---: |
| URS | `USTA1` | Ustava Republike Slovenije (URS) | 13 | 1991-12-23 to 2025-12-01 | 179 |
| ZVDZ | `ZAKO185` | Zakon o volitvah v državni zbor (ZVDZ) | 13 | 1992-09-27 to 2024-02-10 | 117 |

The data was retrieved on 2026-10-28, one request at a time with a pause of at least 0.7 seconds, with the user agent
`lexifina-watch/1.0 (+https://lexifina.com/watch; corpus@lexifina.com)`. PIS's robots.txt allows everything except
`/iskanje`. The website asks a browser to solve a small proof-of-work puzzle (`/api/a`) only after an error; the build
never needed or used it.

## The build, step by step

1. `python -X utf8 scripts/slovenia-law/build.py --today 2026-10-28` in Lexifina's own repository fetched the data into its
   cache and wrote this repository. `tools/build.py` here is the same file as `scripts/slovenia-law/build.py` there
   (git blob `a0deb0456fe37730c919dfe32d0256a54fbed198`), with `tools/reproduce.py`, which writes this file, `tools/check_repo.py` and `tools/test_repo.py`.
2. `python -X utf8 scripts/slovenia-law/check_repo.py` read every version of both acts back from this repository with
   `tools/na_dan.py`, on the day it took effect, and compared it file by file with the text parsed afresh from the
   cached JSON; then it compared the whole act, word for word, with all the words PIS gives for that version (without
   PIS's warning, its list of the acts the text comprises, and the number of the consolidated text). Result:
   `26 versions checked (3874 files), 0 mismatches; 26 versions word for word against all of PIS's words for that version, 0 mismatches`.
3. `python -X utf8 scripts/slovenia-law/test_repo.py` ran the functional tests below against this repository.
4. `python -X utf8 scripts/slovenia-law/build.py --offline --verify-rebuild` built the repository a second time from the
   same cache into a temporary folder and compared the hashes. A second build from the same cache into an empty folder gave the same history: the last law commit was `84fa3b57cb64d0ed10e0e0fdf77b95bff54f6024` in both, and every one of the 30 law commits and 48 tags had the same hash.
5. The build was run once more (`--offline`) to write these results into this file, and the final `main` was rebuilt
   again in a temporary folder and compared hash for hash before it was force-pushed to the private GitHub repository
   `lexifina/slovenia-law` (which held only a placeholder commit describing the sources before).

It ran with Python 3.12.10 and git version 2.46.0.windows.1 on Windows 11. No network service other than PIS is involved.

### Functional tests (`tools/test_repo.py`)

7 of 7 tests passed:

| Test | Result | Detail |
| --- | --- | --- |
| git blame on a changed provision names a law | pass | urs/clen-068.md: "Tujci lahko pridobijo ..." by Uradni list RS, št. 24/03 (UZ3a, 47, 68); authors ['Uradni list RS, št. 24/03 (UZ3a, 47, 68)', 'Uradni list RS, št. 33/91-I (URS)'] |
| the on-date tool gives the text before and after a known amendment | pass | URS 68: original wording on 1997-07-13, UZS68 wording on 1997-07-14; URS 3.a absent 2003-03-06, present 2003-03-07 |
| every law commit: its words are in force on its day and not the day before | pass | 396 article changes checked on their in-force day and the day before |
| git log --follow on a file lists its amending laws in date order | pass | urs/clen-068.md: 1991-12-23 Uradni list RS, št. 33/91-I (URS); 1997-07-14 Uradni list RS, št. 42/97 (UZS68); 2003-03-07 Uradni list RS, št. 24/03 (UZ3a, 47, 68) |
| every tag resolves and every history commit has an In-force trailer | pass | 48 tags resolve; 30 history commits all carry a parseable In-force trailer (the documentation commit has none) |
| no commit is authored by Lexifina except the documentation commit | pass | 31 commits: 26 by laws, 4 by PIS (unexplained), 1 documentation commit by Lexifina |
| the README's git commands run | pass | 11 commands from the README table ran with output: `python tools/na_dan.py 1997-07-13 urs 68`; `python tools/na_dan.py 1997-07-14 urs 68`; `python tools/na_dan.py 2000-01-01 urs`; `git blame urs/clen-068.md`; `git log --follow --format="%ad %an" --date=short urs/clen-068.md`; `git log -p --word-diff urs/clen-068.md`; `git show akt/2003-01-0899`; `git show zvdz/2006-08-09 --stat`; `git rev-list -1 --before="2004-06-15T23:59:59Z" main -- urs`; `git log --author="PIS RS" --format="%ad %s" --date=short`; `git log --author="odl. US" --format="%ad %an %s" --date=short` |

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
- **Changes.** Consecutive versions are compared file by file. 184 changes of a file were found.
- **Cause.** PIS's register names, for each consolidated text, the one act whose entry into force produced it; in
  both acts every consolidated text is produced by exactly one act. A changed file is credited to that act only on one
  of these grounds, each written in the code:
  - the amending act names this člen: 91
  - the final provisions of the amending act itself: 20
  - a replacement the amending act makes in the whole text: 14
  - the official consolidated text (uradno prečiščeno besedilo) restates the whole act: 3
  - the title of the amending act names this člen (PIS has no text of the act): 1

  55 file changes are explained by none of these, and are never credited to an act (below).
- **Date.** The day the act took effect (veljaOd in the register). Where the register has none (two Constitutional
  Court decisions and the official consolidated text ZVDZ-UPB1), the day of publication, said in `Date-note:`.
- **Commits.** One for the text as enacted of each act (2), one per act and amending act (24, of which
  0 change no words), and one per act and day for the changes no amending act explains (4), in the
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
- **Documentation commit.** Dated 2026-10-28, the day the data was retrieved, not the day of the run, so a later rebuild
  of the same data gives the same hash. It adds `corpus.json`, `akti.csv`, `data/razlicice.json`, the tools and this file.

## Changes no amending act explains

| Act | In force | Version and unit |
| --- | --- | --- |
| URS | 1997-07-14 | NPB 1 uvod |
| URS | 1997-07-14 | NPB 1 naslov |
| URS | 1997-07-14 | NPB 1 clen-6 |
| URS | 1997-07-14 | NPB 1 clen-20 |
| URS | 1997-07-14 | NPB 1 clen-39 |
| URS | 1997-07-14 | NPB 1 clen-74 |
| URS | 1997-07-14 | NPB 1 clen-134 |
| URS | 1997-07-14 | NPB 1 clen-140 |
| URS | 1997-07-14 | NPB 1 clen-160 |
| URS | 1997-07-14 | NPB 1 clen-172 |
| URS | 1997-07-14 | NPB 1 clen-173 |
| URS | 1997-07-14 | NPB 1 clen-174 |
| URS | 1997-07-14 | NPB 1 podpis |
| URS | 1997-07-14 | NPB 1 koncne/1991-01-1409 |
| URS | 2021-06-04 | NPB 11 clen-172 |
| URS | 2021-06-04 | NPB 11 clen-173 |
| URS | 2021-06-04 | NPB 11 clen-174 |
| URS | 2021-06-04 | NPB 11 koncne/1991-01-1409 |
| URS | 2021-06-04 | NPB 11 koncne/1997-01-2341 |
| URS | 2021-06-04 | NPB 11 koncne/2000-01-3052 |
| URS | 2021-06-04 | NPB 11 koncne/2003-01-0899 |
| URS | 2021-06-04 | NPB 11 koncne/2004-01-3088 |
| URS | 2021-06-04 | NPB 11 koncne/2004-01-3090 |
| URS | 2021-06-04 | NPB 11 koncne/2004-01-3092 |
| URS | 2021-06-04 | NPB 11 koncne/2006-01-2951 |
| URS | 2021-06-04 | NPB 11 koncne/2013-01-1777 |
| URS | 2021-06-04 | NPB 11 koncne/2013-01-1779 |
| URS | 2021-06-04 | NPB 11 koncne/2016-01-3208 |
| ZVDZ | 1993-03-27 | NPB 1 clen-19 |
| ZVDZ | 1993-03-27 | NPB 1 clen-37 |
| ZVDZ | 1993-03-27 | NPB 1 clen-43 |
| ZVDZ | 1993-03-27 | NPB 1 clen-53 |
| ZVDZ | 1993-03-27 | NPB 1 clen-60 |
| ZVDZ | 1993-03-27 | NPB 1 clen-90 |
| ZVDZ | 1993-03-27 | NPB 1 clen-95 |
| ZVDZ | 1993-03-27 | NPB 1 clen-107 |
| ZVDZ | 1993-03-27 | NPB 1 clen-111 |
| ZVDZ | 1993-03-27 | NPB 1 clen-112 |
| ZVDZ | 1993-03-27 | NPB 1 clen-113 |
| ZVDZ | 1993-03-27 | NPB 1 podpis |
| ZVDZ | 1993-03-27 | NPB 1 koncne/1992-01-2068 |
| ZVDZ | 2024-02-10 | NPB 12 clen-111 |
| ZVDZ | 2024-02-10 | NPB 12 clen-112 |
| ZVDZ | 2024-02-10 | NPB 12 clen-113 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/1992-01-2068 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/1993-01-0587 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/1995-01-2787 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/1997-01-3226 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2000-01-3052 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2000-01-3303 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2003-01-3567 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2006-01-3401 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2007-01-2904 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2017-01-1207 |
| ZVDZ | 2024-02-10 | NPB 12 koncne/2021-01-0618 |

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

This repository was built on 2026-10-28 in **Claude Code**, Anthropic's coding tool, by the model **Claude Opus 5.5**
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
