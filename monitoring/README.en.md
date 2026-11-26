<!-- lawwatch: written from data/checks by the check trail; edit the records, not this page -->

# Monitoring: what is read and what came of it

[Slovenščina](README.md)

How global-law monitors every country: [global-law monitoring/](https://github.com/lexifina/global-law/tree/main/monitoring). This page is the same for Slovenia only: every time an official source is read, when, and what came of it (acts added, changed and removed). The machine-readable form is [data/checks/](../data/checks/) (JSON Lines, schema `lexifina-check/1`), in `git log` as `Kind: check` commits, and month by month in [checks/](checks/).

**Last check:** 2026-11-26 05:26 UTC, PISRS: Register of regulations and the Uradni list RS: 83 addresses read; 0 added, 0 changed, 0 removed; no change; 18 not published, 0 of them with no reason. Flags: `publish-lag`.

## Sources

| Source | Folders | How often | Last successful check | Last result | State |
| --- | --- | --- | --- | --- | --- |
| [PISRS: Register of regulations and the Uradni list RS](https://pisrs.si) | `ustava/`, `zakon/`, `uredba/`, `pravilnik/`, `sklep/` | daily | 2026-11-26 05:26 UTC | no change | watched: PISRS lists its whole register only through its developer API, which needs a key; this reads the interface behind its website, one request every 2 seconds |
| [Uradni list RS: the gazette's own site (uradni-list.si)](https://www.uradni-list.si) |  | — | — | — | closed source: it holds the issues to 28 February 2026; later issues are published on PISRS, read above |

## The last 30 days

| Started (UTC) | Source | Read | Added | Changed | Removed | Not published (no reason) | Result | Commits |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| [2026-11-26 05:23](checks/2026-11.md#si-pisrs-20261126t052333z) | pisrs | 83 | 0 | 0 | 0 | 18 (0) | no change `publish-lag` | — |
| [2026-11-25 05:20](checks/2026-11.md#si-pisrs-20261125t052053z) | pisrs | 89 | 0 | 0 | 0 | 17 (0) | no change `publish-lag` | — |
| [2026-11-24 05:44](checks/2026-11.md#si-pisrs-20261124t054419z) | pisrs | 82 | 0 | 0 | 0 | 14 (0) | no change `publish-lag` | — |
| [2026-11-23 01:46](checks/2026-11.md#si-pisrs-20261123t014603z) | pisrs | 83 | 0 | 0 | 0 | 14 (0) | no change `publish-lag` | — |
| [2026-11-23 01:42](checks/2026-11.md#si-pisrs-20261123t014214z) | pisrs | 89 | 0 | 0 | 0 | 12 (0) | no change `publish-lag` | — |

## Check it yourself

```
python tools/checktrail.py                      # the latest check of every source
python tools/checktrail.py --day 2026-11-23     # every check of a day
python tools/checktrail.py --act <id>           # when an act was seen and published
git log --grep='^Kind: check' --format='%ci %s'  # the checks in the history
```

Only the official publication has legal force; the texts here are copies for reading and searching.
