<!-- lawwatch: written from data/checks by the check trail; edit the records, not this page -->

# Watching the sources: what is watched for Slovenia

[Slovenščina](WATCHING.md)

How global-law watches every country's sources: [global-law WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md). This page is the same for Slovenia only: every official source this repository takes text from, what is read on it, how often and when it was last read. Every read and what came of it: [monitoring/](monitoring/README.en.md).

| Source | What is read | Folders | How often | Last read | State |
| --- | --- | --- | --- | --- | --- |
| [PISRS: Register of regulations and the Uradni list RS](https://pisrs.si) | the Uradni list RS day by day (every act published, with its PIS id); for each law, constitutional act and Constitutional Court decision in it, the acts it amends or repeals and the day it takes effect; and the register entries of 60 acts held here a check (in force or not, newest consolidated text), every act about every 64 days | `ustava/`, `zakon/`, `uredba/`, `pravilnik/`, `sklep/` | daily | 2026-11-23 01:42 UTC | watched: PISRS lists its whole register only through its developer API, which needs a key; this reads the interface behind its website, one request every 2 seconds |
| [Uradni list RS: the gazette's own site (uradni-list.si)](https://www.uradni-list.si) | — |  | — | — | closed source: it holds the issues to 28 February 2026; later issues are published on PISRS, read above |

Sources are read within their robots.txt and terms, with pauses between requests.
