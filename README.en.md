# Slovenia: law history in git

**English** · **[Ali pa preberite v slovenščini](README.md)**

<picture>
<source media="(prefers-color-scheme: dark)" srcset="data/effort-dark.svg">
<img alt="Slovenian law in this repository: what it holds, changes by the year they took effect, completeness against the official sources, and the correctness of what is held" src="data/effort-light.svg" width="880">
</picture>

The law of Slovenia as a git history: one file per provision, one commit per version on the day it took effect, and the act that made each change as the commit's author. `git blame` names the act behind every article; `git log` lists every change to an article; picking a date gives the text in force that day.

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is Slovenia's national law, which global-law reads at `slovenia/national/acts/`.

**What is in it now:** the Constitution and the National Assembly Elections Act with every version (13 each); 1,850 further acts from PIS's register (all but three of them laws) with 3,044 versions, among them 742 acts since repealed and 958 amending acts; and 1,971 more acts in force (1,954 laws and 17 decrees), each in its current text only. [`registry/ACTS.md`](registry/ACTS.md) lists the 1,850 acts by kind, [`data/veljavni-predpisi.csv`](data/veljavni-predpisi.csv) the 1,971 in force, and [`akti.csv`](akti.csv) the acts behind every version of the first two.

Each act is in `<kind>/<year>/<PIS id>/`, one file per article (`ustava/1991/usta1/clen-068.md` is Article 68 of the Ustava Republike Slovenije, the Constitution; `zakon/2013/zako5944/` is the Zakon o delovnih razmerjih, ZDR-1, the Employment Relationships Act). Until 10 November 2026 most folders had the act's short name (`urs/`); [`data/paths.json`](data/paths.json) maps each to its folder, and `git log --follow` follows a file across the move.

The text is in Slovenian, as PIS publishes it. An English translation is not part of this record.

## Questions as git commands

| Question | Command |
| --- | --- |
| Every change to Article 68 of the Constitution | `git log -p --follow --word-diff -- ustava/1991/usta1/clen-068.md` |
| Which act wrote each line of Article 68? | `git blame ustava/1991/usta1/clen-068.md` |
| Every version of the Constitution, with the day each took effect | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- ustava/1991/usta1 urs` |
| Article 68 as in force on 13 July 1997, the day before UZS68 changed it | `python tools/na_dan.py 1997-07-13 urs 68` |

**Outside git**, we also host this record publicly, for free:

- **[Ask Claude about Slovenian law](https://global-law.lexifina.com/v1/try_claude?country=slovenia)**: opens Claude with a first question ready.
- **[Ask ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=slovenia)**: the same question in ChatGPT.
- **[Search Slovenian law on our site](https://lexifina.com/law?country=slovenia&q=letni+dopust)**: a search for "letni dopust", with each provision's text and its versions, no account needed.
- **[Developer REST API](https://global-law.lexifina.com/v1/search_law?query=letni+dopust&jurisdiction=slovenia)**: the same search as JSON, with no key. See the [documentation here](https://lexifina.com/api/global-law).

Both assistants read the record through the free Global law connector (MCP, `https://global-law.lexifina.com/mcp`); the first time, the chat gives you the link that adds it. Ask in Slovenian or in English.

**Host it yourself easily.** All it takes is git and Python, and the tools run on your machine:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add slovenia/national/acts
python3 tools/law.py show 2026-01-01 slovenia/national/acts/ustava/1991/usta1/clen-068.md
```

Opened in Claude Code, Cursor, VS Code or Codex, the clone also starts a local MCP server with the same tools ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Dates

Each commit is dated at noon, Europe/Ljubljana, on the day the version took effect, and carries it in its `In-force:` trailer:

- for every version, the day PIS's register gives as the start of validity (velja od) of the act that produced it;
- constitutional acts take effect when the National Assembly proclaims them, a few days before the Uradni list prints them; two Constitutional Court decisions and the official consolidated text of the Elections Act have no in-force day in the register and are dated by publication; each such commit says so in `Date-note:`;
- an act held only in its current text is dated by its own entry into force if PIS never consolidated it, otherwise by the entry into force of the act that produced its newest consolidated text;
- git cannot store dates before 1970, so the two versions that took effect earlier (1949 and 1965) are dated 1 January 1970, with the real day in `In-force:`.

Each change is credited to the act that made it, as PIS cites it (`Uradni list RS, št. 42/97 (UZS68)`, a Constitutional Court decision as `odl. US`), but only where that act's text explains the change. Anything else, including the current texts of 445 acts in force that PIS has consolidated and the 742 repeals, is committed by `PIS RS (neuradno prečiščeno besedilo)`, never by an act.

## How it is checked

- `tools/check_repo.py` reads every version of the Constitution and the Elections Act back from git on the day it took effect and compares it with PIS, file by file and word for word with all of PIS's words for that version: 26 versions, 0 mismatches.
- `tools/test_repo.py` checks blame, the dated tool, the order of `git log --follow`, the tags, the trailers and the authors; a second build from the same data gave the same hashes. Both are in [`REPRODUCE.md`](REPRODUCE.md).
- The 1,850 acts from the register are built by `registry/tools/build/` from one corpus file whose sha256 is stated in [`registry/REPRODUCE.md`](registry/REPRODUCE.md); no check of that build is recorded there yet.

## What it does not show

- **Earlier versions of the 1,971 acts in force** held in their current text; they are to be added behind it without rewriting history.
- **Regulations, local acts, case law and EU law.** Apart from 20 decrees and other executive acts, the record holds laws only.
- **Which act repealed an act.** A repeal removes the act's text on the day PIS gives as the end of its validity, in a commit by PIS, not by the repealing act.
- **Constitutional Court decisions** that declare a provision unconstitutional without changing its words; PIS records them in its register, not in the text.
- **PIS's notes**, its links to case law and EU law, and the list of acts at the top of each consolidated text (the acts are in the commits).

## Sources

| Source | Kind | Past versions | Notes |
| --- | --- | --- | --- |
| [PIS, Pravno-informacijski sistem Republike Slovenije](https://pisrs.si) (Služba Vlade Republike Slovenije za zakonodajo) | Official register of acts, with the text as enacted and the unofficial consolidated texts (NPB) | yes, every consolidated text and its in-force day | Read through PIS's JSON interface; consolidated texts are for information only, and only the Uradni list Republike Slovenije is authoritative |

## Licence

See [`LICENSE`](LICENSE). Official texts in the legislative, administrative and judicial field are not protected by copyright in Slovenia (Article 9(1)(2) ZASP); the history, commit messages, tables and tools are CC0 1.0.

No AI model wrote or changed legal text; the scripts were written by an AI model (see [`REPRODUCE.md`](REPRODUCE.md)).

## More

From [lexifina/global-law](https://github.com/lexifina/global-law):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): every feature, and what every corpus must support (`git blame`, `law.py`, the MCP tools)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): questions and answers · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): proposing changes · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): the MCP server · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): how it was built · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): how current each corpus is · [Monitoring](https://github.com/lexifina/global-law/tree/main/monitoring): whether updates are running · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): how each official source is watched for changes
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): how fast the tools are, measured
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): charts and bridges across the world's law
- [Vulnerabilities](https://github.com/lexifina/global-law/tree/main/vulnerabilities): mistakes in legislation as published
