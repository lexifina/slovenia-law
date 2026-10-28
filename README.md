# Slovenian law, change by change

Two acts of the Republic of Slovenia as a git repository: the Constitution (Ustava Republike Slovenije, URS,
Uradni list RS, št. 33/91-I) and the National Assembly Elections Act (Zakon o volitvah v državni zbor, ZVDZ,
Uradni list RS, št. 44/92). Each amending act is one commit, credited to that act and dated the day it took effect, at
noon in Ljubljana. The text is the text as enacted and every unofficial consolidated text (neuradno prečiščeno
besedilo, NPB) published by the Government Office for Legislation in [PIS](https://pisrs.si).

*Slovenščina: [spodaj](#slovenščina).*

## The questions, as git commands

| Question | Command |
| --- | --- |
| What did Article 68 of the Constitution say on 13 July 1997? | `python tools/na_dan.py 1997-07-13 urs 68` |
| ... and the next day, when UZS68 took effect? | `python tools/na_dan.py 1997-07-14 urs 68` |
| The whole Constitution as it stood on 1 January 2000 | `python tools/na_dan.py 2000-01-01 urs` |
| Which act wrote each paragraph of Article 68? | `git blame urs/clen-068.md` |
| Every change to Article 68, with the act and the day | `git log --follow --format="%ad %an" --date=short urs/clen-068.md` |
| The same, with the words | `git log -p --word-diff urs/clen-068.md` |
| Everything one amending act changed | `git show akt/2003-01-0899` |
| What changed in the ZVDZ on one day | `git show zvdz/2006-08-09 --stat` |
| The commit in force at the end of a day (UTC) | `git rev-list -1 --before="2004-06-15T23:59:59Z" main -- urs` |
| All amending acts with their dates | [`akti.csv`](akti.csv) |
| Changes no amending act explains | `git log --author="PIS RS" --format="%ad %s" --date=short` |
| Changes made by Constitutional Court decisions | `git log --author="odl. US" --format="%ad %an %s" --date=short` |

Article files are `clen-NNN.md` (`clen-003a.md` is Article 3.a). In PowerShell, quote a revision with a path:
`$r = git rev-list -1 --before="2004-06-15T23:59:59Z" main -- urs; git show "$($r):urs/clen-014.md"`.
After a rebuild of this repository, update an existing clone with `git fetch --force --tags`.

## The dates, and which one we use

A Slovenian act has a day it was adopted (`Adopted:`, sprejeto), the day the Uradni list published it (`Published:`,
objavljeno) and the day it took effect (`In-force:`, velja od). **Commits are dated the day the change took effect**, at
noon in Ljubljana: that is the day that decides which text applies. It is the day PIS's register of acts gives as the
start of validity (veljaOd) of the act that produced the version. Where an act applies from a later day than it took
effect, the commit also has `Applies-from:`. All dates are in every commit message.

Constitutional acts take effect when the National Assembly proclaims them, a few days before the Uradni list prints
them; those commits say so in a `Date-note:` trailer. Two Constitutional Court decisions and the official
consolidated text of 2006 have no in-force day in the register; they are dated by publication, with a `Date-note:`.
No change here is before 1970, so no date is clamped.

## How it is checked

`tools/check_repo.py` reads every version of both acts back from git on the day it took effect and compares it with
PIS: file by file with the text parsed from PIS's data, and word for word with all the words PIS gives for that
version, read independently of the parser. `tools/test_repo.py` runs the commands in this README and checks blame,
the on-date reader, the order of `git log --follow`, the tags, the trailers and the authors. The results are in
[`REPRODUCE.md`](REPRODUCE.md).

## What "author" means

The author of a commit is the act that made the change: `Uradni list RS, št. 42/97 (UZS68)`, with an address ending
`@pisrs.invalid`, which cannot exist, so `git blame` names the act. PIS's register names, for each consolidated text,
the one act whose entry into force produced it. A changed article is credited to that act only when the act's own
text names the article ("se 68. člen spremeni tako, da glasi"), makes a replacement in the whole text that explains the
change ("v celotnem besedilu zakona se besedilo ... nadomesti"), or (for UZ148, whose text PIS does not hold) its title
names it. The final provisions of an amending act, which PIS prints after the act, are credited to that act.

A change none of these explains is committed separately by `PIS RS (neuradno prečiščeno besedilo)`, with "sprememba
brez pojasnila" in its subject; it is never credited to an act. These are PIS's own editing: the move from the text as
printed in 1991 and 1992 to the consolidated form (the preamble and signatures left out, corrected misprints, the
final provisions moved after the act) and, in 2021 (URS) and 2024 (ZVDZ), the removal of the amending acts' final
provisions from the end of the text. The committer is always `Lexifina`.

Blame credits whole lines: a paragraph rewritten by two acts names only the later one. Use `--word-diff` to see what
each act changed.

## What it does not show

- Versions PIS does not publish: a consolidated text exists only after each amending act, so a change made by two acts
  on the same day is one step (it does not happen in these two acts).
- Constitutional Court decisions that declare a provision unconstitutional without changing its words; PIS records
  them in its register but not in the text.
- PIS's notes, links to case law and EU law, and the explanatory list of acts at the top of each consolidated text
  (the acts are in the commits instead).
- Any act beyond these two. The same build works for any act in PIS: add it to `ACTS` in `tools/build.py`.

Consolidated texts have no legal force; only the Uradni list Republike Slovenije is authoritative.

## How it is built

`tools/build.py` reads PIS and writes this repository from scratch; the same data gives the same hashes. Every step,
the software, the decisions made by hand and what an AI model did are in [`REPRODUCE.md`](REPRODUCE.md). Each act's
folder has a `README.md` listing its provisions with how often each changed.

## Licence

Official texts in the legislative field are not protected by copyright in Slovenia (Article 9(1)(2) ZASP). Source:
PIS, Pravno-informacijski sistem Republike Slovenije, https://pisrs.si, Služba Vlade Republike Slovenije za zakonodajo.
PIS states: "Neuradno prečiščeno besedilo predpisa predstavlja zgolj informativni delovni pripomoček, glede katerega
organ ne jamči odškodninsko ali kako drugače." The history, commit messages, tables and tools are released under
[CC0 1.0](LICENSE).

---

## Slovenščina

Ustava Republike Slovenije in Zakon o volitvah v državni zbor kot git repozitorij, po izvirnem besedilu in neuradnih
prečiščenih besedilih iz PIS.

- **Vsak commit je en spremembni akt**, vpisan kot avtor (`Uradni list RS, št. 42/97 (UZS68)`), tako da `git blame`
  pokaže, kateri akt je napisal kateri odstavek. Akt navaja register PIS, člen pa besedilo akta.
- **Vsak commit nosi datum začetka veljavnosti**, opoldne po ljubljanskem času. V sporočilu sta tudi datum sprejetja in
  datum objave v Uradnem listu.
- **Vsak člen je ena datoteka**, vsak odstavek ena vrstica.
- **Spremembe brez pojasnila niso akti.** Kjer se je besedilo spremenilo, ne da bi ga akt omenil, je avtor commita
  PIS RS in commit je tako označen.

Neuradno prečiščeno besedilo je zgolj informativni delovni pripomoček; verodostojen je samo Uradni list Republike
Slovenije.
