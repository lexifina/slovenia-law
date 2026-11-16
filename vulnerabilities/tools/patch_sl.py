"""Slovenian fixes for the copy of global-law's scripts (references and repeal placeholders):
 1. detectors/placeholder_ref.py: PIS marks a deleted article "# 21. člen (črtan)" and one that has ceased to apply
    "# 43. člen (prenehal veljati)" (825 and 1,602 headings at the pin); only "(razveljavljen)" was read as a placeholder.
    Both are read now, only in brackets (SL_CRTAN, SL_PRENEHAL); an article in which only some numbered paragraphs
    are "(črtan)" and another still has text ("(1) (črtan). (2) Zavezanec ...") is not a placeholder (SL_PARTIAL).
 2. ingest/refscan.py SERIES: the Turkish "ek" (Ek Madde) had no word boundary, so "drugi odstavek 3. člena" (paragraph 2
    of Article 3) was taken for a separately numbered series ("odstav-ek") and the reference was dropped (SL_SERIES_EK).
 3. ingest/refscan.py PRE: an inserted article "463.a člena" was not read at all; the letter is now part of the key
    (SL_PRE_LETTER); and the letter "o" of an inserted article (clen-018o.md, "18.o člen") is a letter, not the
    Spanish or Portuguese ordinal "4o.", so Article 18.o is no longer taken for Article 18 (SL_O_SUFFIX).
 4. ingest/refscan.py is_external: "14. členu Zakona o delovnih razmerjih", "5. člena Uredbe (EU) ...", "3. člena
    navedenega zakona" name another act after the reference; only "tega zakona" (and the like) is the act's own
    (SL_EXT_AFTER).
 5. ingest/refscan.py refs: the Croatian and Serbian "član" read "4. člani v njih delujejo" (point 4: "members work in
    them") as Article 4; in Slovenian only "člen" names an article (SL_CLANI).
    python -X utf8 patch_sl.py <scripts dir>        (a fix already in place is skipped)"""
import os, sys

S = sys.argv[1]
FIXES = {
    os.path.join("detectors", "placeholder_ref.py"): [
        ("(črtan) / (prenehal veljati)", 'r"razveljavljen|',
         'r"razveljavljen|(?<=\\()črtan[aoi]?(?=\\))(?#SL_CRTAN)|(?<=\\()prenehal[aoi]?\\s+veljati(?=\\))(?#SL_PRENEHAL)|',
         "SL_CRTAN"),
        ("a numbered paragraph with text is not a placeholder", "    m = GONE.search(substantive)  # not substantive[:70]: the cut can fall inside a word\n",
         "    m = GONE.search(substantive)  # not substantive[:70]: the cut can fall inside a word\n"
         "    if m and re.match(r\"(?i)črtan|prenehal|razveljavljen\", m.group(0)) and re.search(\n"
         "            r\"\\(\\d{1,2}\\)\\s*(?!\\(?(?:črtan|prenehal|razveljavljen))\\w\", substantive):  # SL_PARTIAL\n"
         "        return False  # \"(1) (črtan). (2) Zavezanec ... mora ...\": only one paragraph is deleted\n",
         "SL_PARTIAL"),
    ],
    os.path.join("ingest", "refscan.py"): [
        ("SERIES 'ek' needs a word boundary", 'SERIES = re.compile(r"(?i)(ek|',
         'SERIES = re.compile(r"(?i)(?<!\\w)(?#SL_SERIES_EK)(ek|', "SL_SERIES_EK"),
        ("463.a člena", 'PRE = re.compile(r"(?i)(?<![\\w\\d.])(\\d{1,4})(?:\\.\\s*(?:člen\\w*|',
         'PRE = re.compile(r"(?i)(?<![\\w\\d.])(\\d{1,4})(?:\\.(?:([a-z])(?=\\s+člen)(?#SL_PRE_LETTER))?\\s*(?:člen\\w*|',
         "SL_PRE_LETTER"),
        ("PRE key reads the letter", "first = key(m.group(1), m.group(2) if rx is NORDIC else None)",
         "first = key(m.group(1), m.group(2) if rx in (NORDIC, PRE) else None)  # SL_PRE_LETTER_KEY",
         "SL_PRE_LETTER_KEY"),
        ("another act after the reference", '    if _LANG["v"] == "ru" and EXT_AFTER_RU.match(tail):\n',
         '    if _LANG["v"] == "sl" and EXT_AFTER_SL.match(tail):  # SL_EXT_AFTER\n        return True\n'
         '    if _LANG["v"] == "ru" and EXT_AFTER_RU.match(tail):\n', "SL_EXT_AFTER\n"),
        ("18.o is a letter, not an ordinal", 'if s == "º" or (s == "o" and _LANG["v"] != "en"):',
         'if s == "º" or (s == "o" and _LANG["v"] not in ("en", "sl")):  # SL_O_SUFFIX', "SL_O_SUFFIX"),
        ("člani (members) is not člen", "            if is_external(before, tail):\n                continue\n",
         "            if rx is PRE and _LANG[\"v\"] == \"sl\" and not re.search(r\"(?i)člen\", m.group(0)):  # SL_CLANI\n"
         "                continue  # Slovenian \"4. člani v njih delujejo\": point 4 and the word for members, not Article 4\n"
         "            if is_external(before, tail):\n                continue\n", "SL_CLANI"),
        ("EXT_AFTER_SL", "\n\n# Vietnamese: ",
         "\n\n# SL_EXT_AFTER_RX: Slovenian names the act after the reference: \"14. členu Zakona o ...\", \"5. člena Uredbe (EU)\",\n"
         "# \"3. člena navedenega zakona\", \"8. člena zakona, ki ureja ...\"; \"tega zakona\" / \"te uredbe\" is the act's own\n"
         "EXT_AFTER_SL = re.compile(r\"^[ \\t]*(?:[A-ZČŠŽĆĐ][\\wčšžćđ]*|(?!(?:tega|te|tem|tej|tega|tem)\\b)[a-zčšžćđ]+\\s+(?:zakon|zakonik|uredb|pravilnik|odlok|kodeks|konvencij|sporazum|pogodb|direktiv|ustav)\\w*|\"\n"
         "                          r\"(?:zakon|zakonik|uredb|pravilnik|odlok|kodeks|konvencij|sporazum|pogodb|direktiv)\\w*\\b)\")\n"
         "\n\n# Vietnamese: ", "SL_EXT_AFTER_RX"),
    ],
}
for rel, fixes in FIXES.items():
    p = os.path.join(S, rel)
    s = open(p, encoding="utf-8").read()
    for name, old, new, mark in fixes:
        if mark in s:
            print("already in place:", name)
            continue
        assert s.count(old) == 1, f"not found once in {rel}: {name} ({s.count(old)})"
        s = s.replace(old, new, 1)
        print("patched:", name)
    open(p, "w", encoding="utf-8", newline="\n").write(s)
