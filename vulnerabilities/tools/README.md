# Tools

The scripts behind this Slovenia-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/slovenia-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only slovenia-law and its commit (language `sl`).
`build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py` and `config.json` sit two folders above the
scripts.

| Script | What it does |
| --- | --- |
| `run.sh` | Indexes the history and texts, maps paths to each act's folder (`map_moved.py`), adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `map_moved.py` | Rewrites the paths in the history table to each act's folder since the move of 10 November 2026 (`data/paths.json`, `urs/` to `ustava/1991/usta1/`), so that an act's history is not split in two at the move; here it rewrote 229,388 paths of 1,973 folders |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the history detectors read every change; changed for this repository (below) |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (the one here) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Slovenian and English, light and dark |
| `config.json` | The repository, the Slovenian category names and chart labels, and what is not law: `registry/`, `data/`, `tools/` and the root files (`README.md`, `README.en.md`, `REPRODUCE.md`, `corpus.json`, `LICENSE`, `akti.csv`) |
| `apply_patches.py` | Applies the patches below to a copy of the scripts, each once, in a fixed order, and records them in `.kit_patches.json` (`python -X utf8 apply_patches.py <scripts dir>`); later patches edit text earlier ones inserted, so a patch is never run twice on the same copy. `patch_sl.py` is last in its order |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts |
| `patch_detectors_vi.py`, `patch_es.py`, `patch_ca.py`, `patch_en.py`, `patch_de.py`, `patch_en_et.py`, `patch_co.py`, `patch_sv.py`, `patch_pt.py`, `patch_ru.py`, `patch_r18.py`, `patch_xk.py`, `patch_mo.py`, `patch_lu.py`, `patch_li.py`, `patch_mx.py`, `patch_mn.py`, `patch_mt.py`, `patch_np.py`, `patch_en_nr.py`, `patch_dv.py`, `patch_az.py`, `patch_ar.py`, `patch_en_nz.py`, `patch_nb.py`, `patch_mk.py`, `patch_pa.py`, `patch_py.py`, `patch_pe.py`, `patch_en_ph.py`, `patch_qa.py`, `patch_nl.py` | The same for the dates, references and currency names of other languages and jurisdictions; they change nothing in Slovenian text |
| `patch_build_r7.py`, `patch_build_links.py` | Bring a country's `build_vulns.py` up to date (reviews matched on 400 characters of context; a file deleted before the move of folders linked under its old folder); already applied to the `build_vulns.py` here |
| `patch_sl.py` | The fixes made for this repository, in the same form (`python -X utf8 patch_sl.py <scripts dir>`; a fix already in place is skipped, each one found by a marker that survives later edits; see below) |
| `redo.py` | Runs `apply_patches.py`, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `--full` runs every step again through `run.sh`, sends every category to the model and keeps every review already made; `EMBED_FONTS` names the script that embeds the chart's fonts); not needed here, as the fixes were in place before the review |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(registry|data|tools)/|^[^/]+$'`; every law is under `ustava/`, `zakon/` or `uredba/`, so
the review of lapsed time limits in law texts drew the same 40 flags as the review of all of them.

Changes made for this repository:

- `add_root.py` counts as law, beside `law`, `decree` and `publisher` (versions from PIS's consolidated texts), the kinds
  `Zakon` and `Uredba` (acts as enacted) and `court` (three commits of decisions that changed a text): 5,027
  rows; documentation commits (8) keep their own kind.
- `patch_sl.py`, references to repealed placeholders (`detectors/placeholder_ref.py`): PIS marks an article that is gone
  "# 21. člen (črtan)" (825 headings at the pin) or "# 43. člen (prenehal veljati)" (1,602); only "(razveljavljen)" was read,
  and the first run found 4 references. Both are now read, in brackets only; an article in which only some numbered
  paragraphs are "(črtan)" and another still has text ("(1) (črtan). (2) Zavezanec ...") is not a placeholder. With the
  reference fixes below this raised 114 flags, all read by hand.
- `patch_sl.py`, references (`ingest/refscan.py`): the Turkish series marker "ek" (Ek Madde) had no word boundary, so
  "drugi odstavek 3. člena" ("odstav-ek") was dropped as a reference; "463.a člena" was not read at all, and the letter is
  now part of the key; the file `clen-018o.md` (Article 18.o) was read as Article 18, because "o" was taken for the Spanish
  and Portuguese ordinal ("4o."); "14. členu Zakona o delovnih razmerjih", "5. člena Uredbe (EU) ..." and "3. člena
  navedenega zakona" name another act after the number (only "tega zakona" and the like are the act's own); and "4. člani"
  (point 4, "members") was read as Article 4 through the Croatian and Serbian "član". The first run reported 10 references to
  deleted provisions and the run with these fixes 3; the three are article headings written without a space ("31. člen(črtan)") at the end
  of the file of the article before, not references.
- `pins.json` already named the language (`sl`); Slovenian months in the genitive ("januarja" ... "decembra") and "do" were
  already in the time-limit search, and the tolar is already a dead currency.

Limits of global-law's detectors that still show in this repository and were left as they are (see the edge cases):
`ingest/refscan.py` reads only the last of "15. in 16. člena" and "od 20. do 25. člena" (the number before "člen"), and
articles lettered č, š or ž ("52.č člena") are not read as references; `detectors/placeholder_ref.py` sees only placeholders
that have a file of their own, so the 486 placeholder headings kept in the previous article's file are not targets.
