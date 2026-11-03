"""Slovenia: acts of the Register predpisov in PIS, version by version, as corpus.d parts.

Reads only a local copy of PIS (Pravno-informacijski sistem Republike Slovenije, https://pisrs.si/api) and writes
corpus.d/<NN>-<kind>-<year>.json parts (SCHEMA.md in scripts/gitlaw_common). Deterministic: the same inputs give the
same bytes.

    python -X utf8 parse_acts.py --src <folder> --retrieved YYYY-MM-DD [--exclude ids.txt] [--report holds.jsonl]

The folder holds:
- reg.jsonl: one row per register entry read (`/api/rezultat/zbirka/id/<ID>`, reduced; the full answers are kept
  as raw/reg/<PREFIX>/<n//1000>/<n>.json.gz);
- the act's relations (`/api/povezave/med-si-akti/<zbirkaElementID>`) and the text of each of its versions
  (`/api/rezultat/neuradno-precisceno-besedilo/<id>`), either loose (raw/rel/<eid//1000>/<eid>.json.gz,
  raw/txt/<id//100000>/<id>.json.gz) or packed per act in raw/pack/<PREFIX>/<n//1000>/<n>.json.xz as
  {"rel": <relations answer>, "txt": {"<id>": {"sha256": <sha256 of the answer>, "el": [[struktura, vsebina], ...]}}}.

What becomes an act, and its versions:
- the text as enacted ("Osnovni") takes effect on the register's in-force day (veljaOd);
- each unofficial consolidated text (NPB n) takes effect on the in-force day of the act PIS names as the one whose
  entry into force produced it (sopNPBPosega); every unit that differs from the version before is credited to that
  act, because PIS names it;
- an act PIS records as no longer valid (veljaDo) gets a last version with no units on the day it ceased: the
  veljaDo when a related act (named in its relations, or naming it in theirs) took effect or began to apply that day,
  else veljaDo + 1 day when one did on that day; if both or neither, the act is held (PIS uses both conventions,
  and no day is guessed).

An act is held back (the reason goes to the report) when:
- it has no text in PIS, or no in-force day;
- an act PIS lists as changing its text (posegVBesedilo), or a Constitutional Court decision that annuls part of it,
  took or takes effect on a day for which no consolidated text exists (its text on that day is not known);
- a consolidated text's producing act has no in-force day, or the versions' days go backwards;
- PIS records it as no longer valid but still applied, or the day it ceased can't be fixed as above;
- its words, read back from the units, differ from the words of PIS's text.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html as htmlmod
import json
import lzma
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
PARTS = HERE / "corpus.d"
SITE = "https://pisrs.si"
API = "https://pisrs.si/api"

KINDS = {"Zakon": "zakon", "Uredba": "uredba", "Pravilnik": "pravilnik", "Odlok": "odlok", "Navodilo": "navodilo",
         "Odredba": "odredba", "Sklep": "sklep", "Resolucija": "resolucija", "Poslovnik": "poslovnik",
         "Statut": "statut", "Tarifa": "tarifa", "Kolektivna pogodba": "pogodba", "Deklaracija": "deklaracija",
         "Odločba US": "odlocba", "Odločba": "odlocba", "Ustavni zakon": "ustavni", "Akt": "akt", "Pravila": "pravila",
         "Navodila": "navodilo", "Merila": "merila", "Program": "program", "Strategija": "strategija",
         "Priporočilo": "priporocilo", "Smernice": "smernice", "Kodeks": "kodeks", "Splošni akt": "akt"}
LAW_KIND = {"Zakon": "law", "Ustavni zakon": "law", "Odločba US": "court", "Odločba": "court"}


# ---------------------------------------------------------------- inputs

class Src:
    def __init__(self, folder: Path):
        self.f = folder
        self._pack: dict[str, dict | None] = {}

    def reg_rows(self) -> dict[str, dict]:
        rows = {}
        p = self.f / "reg.jsonl"
        for line in p.read_text(encoding="utf-8").splitlines() if p.exists() else []:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # a row being written
            rows[r["zunanjiID"]] = r
        return rows

    def reg_raw(self, pid: str) -> bytes:
        n = int(pid[4:])
        return gzip.decompress((self.f / "raw" / "reg" / pid[:4] / str(n // 1000) / f"{n}.json.gz").read_bytes())

    def pack(self, pid: str) -> dict | None:
        if pid not in self._pack:
            n = int(pid[4:])
            p = self.f / "raw" / "pack" / pid[:4] / str(n // 1000) / f"{n}.json.xz"
            self._pack[pid] = json.loads(lzma.decompress(p.read_bytes())) if p.exists() else None
        return self._pack[pid]

    def rel(self, pid: str, eid: int) -> dict | None:
        p = self.f / "raw" / "rel" / str(eid // 1000) / f"{eid}.json.gz"
        if p.exists():
            return json.loads(gzip.decompress(p.read_bytes()))["data"]
        pk = self.pack(pid)
        return pk["rel"] if pk else None

    def txt(self, pid: str, vid: int) -> tuple[str, list] | None:
        pk = self.pack(pid)
        if pk and str(vid) in pk["txt"]:
            t = pk["txt"][str(vid)]
            return t["sha256"], t["el"]
        p = self.f / "raw" / "txt" / str(vid // 100000) / f"{vid}.json.gz"
        if not p.exists():
            return None
        raw = gzip.decompress(p.read_bytes())
        return hashlib.sha256(raw).hexdigest(), [[x["struktura"], x["vsebina"]] for x in json.loads(raw)["data"]]

    def drop(self, pid: str):
        self._pack.pop(pid, None)


# ---------------------------------------------------------------- text

QUOTES = str.maketrans({"„": '"', "“": '"', "”": '"', "»": '"', "«": '"', "–": "-", "—": "-", " ": " ",
                        " ": " ", " ": " ", " ": " ", " ": " ", "­": None})


def clean(s: str) -> str:
    """The words of an element: table cells kept apart by ' | ', other tags removed, entities decoded, typesetting
    normalised (one form of quotes and dashes, NBSP as a space), runs of white space made one space."""
    s = re.sub(r"</t[dh]\s*>", " | ", s or "", flags=re.I)
    s = re.sub(r"<br\s*/?>|</p\s*>|</tr\s*>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmlmod.unescape(s).translate(QUOTES)
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"(?:\|\s*)+$", "", s).strip()


def words(s: str) -> list[str]:
    return re.findall(r"[^\s|#]+", s)


CLEN = re.compile(r"(\d+)\s*\.\s*([a-z])?\s*\.?\s*člen", re.I)
HEADS = ("del", "poglavje", "oddelek", "pododdelek", "odsek")
SIGN = ("podpisnik", "evidencna_stevilka", "kraj_datum_sprejetja")


def read_version(elements: list) -> tuple[dict[str, dict], list[str]]:
    """One version as units in document order, and the words of every element counted (for the read-back check).
    Units: the preamble (uvod), the title (naslov), each člen with the headings that open it, text that belongs to no
    člen (besedilo), the signatures (podpis) and the final provisions of each amending act that PIS prints after the
    act (koncne-<SOP>)."""
    units: dict[str, dict] = {}
    order: list[str] = []
    counted: list[str] = []
    st = {"mode": "head", "unit": None, "pending": [], "skip_list": False, "after_hr": False}

    def unit(key: str, kind: str, label: str, single: bool = False) -> dict:
        if key in units and not single:
            i = 2
            while f"{key}-{i}" in units:
                i += 1
            key = f"{key}-{i}"
        if key not in units:
            units[key] = {"kind": kind, "label": label, "lines": []}
            order.append(key)
        return units[key]

    def flush_pending(u: dict):
        u["lines"].extend(f"## {h}" for h in st["pending"])
        st["pending"] = []

    for s, raw in elements:
        raw = raw or ""
        text = clean(raw)
        if s in ("opozorilo", "npb"):
            continue
        if st["mode"] == "head" and s in ("odstavek", "pravna_podlaga") and text.endswith("obsega:"):
            st["skip_list"] = True  # PIS's list of the acts this NPB comprises: metadata, named in the credits
            continue
        if st["skip_list"] and s.startswith("alinea"):
            continue
        st["skip_list"] = False
        if s == "napaka" and "<hr" in raw.lower():
            st["mode"], st["unit"], st["after_hr"] = "tail", None, True
            continue
        if not text:
            continue
        counted.extend(words(text))
        if st["mode"] == "tail":
            if st["after_hr"]:
                st["after_hr"] = False
                m = re.search(r"urlurid(?:&#61;|=)(\d{4})(\d+)", raw)
                if m:
                    key = f"koncne-{m.group(1)}-01-{int(m.group(2)):04d}"
                else:
                    ul = re.search(r"št\.\s*(\d+)\s*/\s*(\d+)", text)
                    key = f"koncne-ul-{ul.group(1)}-{ul.group(2)}" if ul else "koncne-x"
                st["unit"] = unit(key, "koncne", text)
            if st["unit"] is None:
                st["unit"] = unit("koncne-x", "koncne", "Končne določbe")
            st["unit"]["lines"].append(text)
            continue
        if s == "naslov" and st["mode"] in ("head", "title"):
            st["mode"] = "title"
            unit("naslov", "title", "Naslov", single=True)["lines"].append(text)
            st["unit"] = None
            continue
        if s in HEADS:
            st["mode"] = "body"
            st["pending"].append(text)
            continue
        if s in SIGN:
            st["unit"] = unit("podpis", "signature", "Podpis", single=True)
            flush_pending(st["unit"])
            st["unit"]["lines"].append(text)
            continue
        if s == "clen":
            m = CLEN.fullmatch(text)
            if m:
                st["mode"] = "body"
                n, suf = int(m.group(1)), (m.group(2) or "").lower()
                u = unit(f"clen-{n:03d}{suf}", "art", f"{n}.{suf} člen" if suf else f"{n}. člen")
                flush_pending(u)
                u["lines"].append(f"# {text}")
                st["unit"] = u
                continue
            if st["pending"]:
                st["pending"][-1] += f" {text}"  # the note of a heading, "(prenehalo veljati)"
                continue
            u = st["unit"]
            if u is not None and u["kind"] == "art" and u["lines"] and u["lines"][-1].startswith("# "):
                u["lines"][-1] += f" {text}"  # the subject of the člen, "(mandat sodnikov)"
                continue
        if st["unit"] is None or (st["unit"]["kind"] == "signature" and s not in SIGN):
            if st["mode"] == "head":
                st["unit"] = unit("uvod", "preamble", "Uvod", single=True)
            else:
                st["mode"] = "body"
                st["unit"] = unit("besedilo", "text", "Besedilo")
        flush_pending(st["unit"])
        st["unit"]["lines"].append(text)
    if st["pending"]:
        u = unit("besedilo", "text", "Besedilo")
        flush_pending(u)
    out = {}
    for k in order:
        u = units[k]
        if u["lines"]:
            out[k] = {"label": u["label"], "kind": u["kind"], "text": "\n".join(u["lines"]) + "\n"}
    return out, counted


def unit_words(units: dict) -> list[str]:
    out = []
    for u in units.values():
        out.extend(words(u["text"]))
    return out


# ---------------------------------------------------------------- acts

class Hold(Exception):
    pass


def ul_label(ul: str | None, short: str | None, pid: str) -> str:
    name = short or pid
    return f"Uradni list RS, št. {ul} ({name})" if ul else f"{name} ({pid})"


def day_plus(d: str, n: int) -> str:
    return (date.fromisoformat(d) + timedelta(days=n)).isoformat()


def npb_n(name: str) -> int:
    if name == "Osnovni":
        return 0
    m = re.fullmatch(r"NPB (\d+)", name or "")
    return int(m.group(1)) if m else -1


def build_act(src: Src, r: dict, rows: dict, pointing: dict) -> tuple[dict | None, dict]:
    """(act, laws it names) or raises Hold; (None, {}) when its inputs are not all here yet."""
    pid = r["zunanjiID"]
    if not r["npb"]:
        raise Hold("no_text")
    vers = sorted(r["npb"], key=lambda v: npb_n(v[1]))
    if npb_n(vers[0][1]) != 0 or any(npb_n(v[1]) < 0 for v in vers):
        raise Hold("no_text_as_enacted" if npb_n(vers[0][1]) != 0 else "version_name:" + str([v[1] for v in vers]))
    rel = src.rel(pid, r["zbirkaElementID"])
    texts = [src.txt(pid, vid) for vid, _ in vers]
    if rel is None or any(t is None for t in texts):
        return None, {}
    if not r.get("veljaOd"):
        raise Hold("no_in_force_day")
    if r.get("semafor") == "Neveljaven predpis, ki se še uporablja":
        raise Hold("invalid_but_still_applied")
    related: dict[str, dict] = {}
    for k in ("posegVBesedilo", "vplivi", "uradnoPreciscenoBesedilo", "avtenticnaRazlaga"):
        for x in rel.get(k) or []:
            if x.get("idVira"):
                related.setdefault(x["idVira"], x)
    npb_src = {x["id"]: x for x in rel.get("neuradnoPreciscenoBesedilo") or []}

    own_law = pid.lower()
    laws = {own_law: law_entry(r, rows)}
    days = [r["veljaOd"]]
    producers = [own_law]
    upb_notes: dict[int, str] = {}
    for vid, name in vers[1:]:
        x = npb_src.get(vid)
        if not x or not x.get("idViraNPBPosega"):
            raise Hold(f"npb_without_producer:{name}")
        prod = x["idViraNPBPosega"]
        pr = rows.get(prod) or related.get(prod)
        d = (rows.get(prod) or {}).get("veljaOd") or (related.get(prod) or {}).get("veljaOd")
        upb = any(x.get("idVira") == prod for x in rel.get("uradnoPreciscenoBesedilo") or [])
        if pr and not d and upb and pr.get("objavljeno"):
            # An official consolidated text (UPB) changes no law and has no in-force day: dated by its publication.
            d = pr["objavljeno"]
            upb_notes[len(days)] = f"Official consolidated text (UPB), dated by its publication in the Uradni list."
        if not pr or not d:
            raise Hold(f"producer_no_in_force_day:{name}:{prod}")
        if d < days[-1]:
            raise Hold(f"days_backwards:{name}:{d}<{days[-1]}")
        days.append(d)
        key = prod.lower()
        laws[key] = law_entry(rows.get(prod) or rel_row(related[prod]), rows)
        producers.append(key)

    # The day it ceased, if PIS records one.
    end = None
    if r.get("veljaDo"):
        # Days on which a related act took effect or began to apply: the acts this act's relations name, and the acts
        # whose relations say they change or affect it.
        cands = {x.get("veljaOd") for x in related.values()}
        for i in set(related) | pointing.get(pid, set()):
            cands |= {(rows.get(i) or {}).get("veljaOd"), (rows.get(i) or {}).get("uporabljaOd")}
        same, nxt = r["veljaDo"] in cands, day_plus(r["veljaDo"], 1) in cands
        if same and nxt:
            raise Hold("end_day_ambiguous:" + r["veljaDo"])
        if same:
            end = r["veljaDo"]
        elif nxt:
            end = day_plus(r["veljaDo"], 1)
        else:
            raise Hold("end_day_unclear:" + r["veljaDo"])
        if end <= days[-1]:
            raise Hold(f"end_before_last_version:{end}<={days[-1]}")

    # Every act that changes the text must have a consolidated text on its day.
    covered = set(days)
    srcs = {p.upper() for p in producers}
    for x in rel.get("posegVBesedilo") or []:
        i, d = x.get("idVira"), x.get("veljaOd") or (rows.get(x.get("idVira")) or {}).get("veljaOd")
        if i in srcs:
            continue
        if not d:
            raise Hold(f"amendment_without_day:{i}")
        if d <= days[0] or (end and d >= end) or d in covered:
            continue
        raise Hold(f"amendment_not_consolidated:{i}:{d}")
    for x in rel.get("vplivi") or []:
        i, d = x.get("idVira") or "", x.get("veljaOd")
        if i.startswith("ODLU") and re.search(r"razveljav", x.get("naziv") or "", re.I) and i not in srcs:
            if not d:
                d = x.get("objavljeno")
            if d and d > days[0] and not (end and d >= end) and d not in covered:
                raise Hold(f"annulment_not_consolidated:{i}:{d}")

    versions = []
    prev_units = None
    for i, ((vid, name), (sha, el), d, prod) in enumerate(zip(vers, texts, days, producers)):
        units, counted = read_version(el)
        if not units:
            raise Hold(f"empty_text:{name}")
        if unit_words(units) != counted:
            raise Hold(f"read_back_words_differ:{name}")
        v = {"from": d, "source_url": f"{API}/rezultat/neuradno-precisceno-besedilo/{vid}", "sha256": sha}
        if versions and d == versions[-1]["from"]:
            v["same_day"] = True
        if prev_units is None:
            v["units"] = units
            v["credits"] = {}
        else:
            changes = {k: u for k, u in units.items() if prev_units.get(k) != u}
            changes.update({k: None for k in prev_units if k not in units})
            v["changes"] = changes
            v["credits"] = {k: [prod] for k in sorted(changes)}
            if not changes:
                v["note"] = f"PIS's consolidated text ({name}) has the same words as the version before."
            if i in upb_notes:
                v["note"] = (v.get("note", "") + " " + upb_notes[i]).strip()
        versions.append(v)
        prev_units = units
    if end:
        versions.append({"from": end, "source_url": f"{API}/rezultat/zbirka/id/{pid}",
                         "sha256": hashlib.sha256(src.reg_raw(pid)).hexdigest(), "units": {}, "credits": {},
                         "note": f"PIS records the act as valid until {r['veljaDo']}."})
    kind = KINDS.get(r.get("vrstaAkta") or "")
    if not kind:
        raise Hold("unknown_kind:" + str(r.get("vrstaAkta")))
    year = (r.get("objavljeno") or r.get("sprejeto") or r["veljaOd"])[:4]
    title = clean(r["naslov"])
    act = {"slug": f"{kind}-{year}-{pid.lower()}", "short": r.get("kratica") or title, "title": title,
           "url": f"{SITE}/pregledPredpisa?id={pid}", "first_law": own_law, "earlier_laws": [], "versions": versions}
    return act, laws


def rel_row(x: dict) -> dict:
    return {"zunanjiID": x["idVira"], "naslov": x.get("naziv") or x["idVira"], "kratica": x.get("kratica"),
            "ulStLeto": x.get("uradniList"), "sprejeto": x.get("sprejeto"), "objavljeno": x.get("objavljeno"),
            "vrstaAkta": None, "_rel": True}


def law_entry(r: dict, rows: dict) -> dict:
    pid = r["zunanjiID"]
    r = rows.get(pid) or r
    vk = r.get("vrstaAkta")
    kind = LAW_KIND.get(vk) if vk else ("court" if pid.startswith("ODLU") else "law" if pid.startswith("ZAKO") else "decree")
    return {"label": ul_label(r.get("ulStLeto"), r.get("kratica"), pid), "title": clean(r.get("naslov") or pid),
            "kind": kind or "decree", "enacted": r.get("sprejeto"), "published": r.get("objavljeno"),
            "url": f"{SITE}/pregledPredpisa?id={pid}", "temporary_until": None, "restores": None, "note": None}


COUNTRY = {
    "code": "SI", "name": "Slovenia", "slug": "slovenia", "lang": "sl", "tz": "Europe/Ljubljana",
    "future_branch": "prihodnje",
    "publisher": {"name": "PIS RS (neuradno prečiščeno besedilo)", "email": "pis@pisrs.invalid"},
    "default_in_force_rule": {"text": "Ustava RS, 154. člen: a regulation takes effect on the fifteenth day after its "
                                      "publication unless it provides otherwise",
                              "source": "https://pisrs.si/pregledPredpisa?id=USTA1"},
    "licence_note": "Vir: PIS RS (Pravno-informacijski sistem Republike Slovenije), https://pisrs.si",
}
PREFIX_ORDER = {"zakon": 50, "ustavni": 49, "uredba": 55, "pravilnik": 60, "odlok": 65, "navodilo": 70, "odredba": 72,
                "sklep": 75, "odlocba": 80}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--retrieved", required=True, help="the day the inputs were retrieved (YYYY-MM-DD)")
    ap.add_argument("--exclude", help="file of PIS ids already recorded elsewhere in the repository (one per line)")
    ap.add_argument("--report")
    a = ap.parse_args()
    src = Src(Path(a.src))
    rows = src.reg_rows()
    exclude = set(Path(a.exclude).read_text(encoding="utf-8").split()) if a.exclude else set()
    # Which acts say (in their own relations) that they change or affect which: {affected id: {acting ids}}.
    pointing: dict[str, set[str]] = defaultdict(set)
    for pid, r in rows.items():
        rel = src.rel(pid, r["zbirkaElementID"]) if r.get("zbirkaElementID") else None
        src.drop(pid)
        for k in ("vplivaNa", "posegiTegaBesedilaV"):
            for x in (rel or {}).get(k) or []:
                if x.get("idVira"):
                    pointing[x["idVira"]].add(pid)
    parts: dict[str, dict] = defaultdict(lambda: {"laws": {}, "acts": []})
    holds, pending = [], 0
    for pid in sorted(rows, key=lambda p: (p[:4], int(p[4:]))):
        r = rows[pid]
        if pid in exclude or r.get("nazivZbirke") not in ("Register predpisov", "Neveljavni predpisi",
                                                           "Obsoletni in konzumirani predpisi"):
            continue
        try:
            act, laws = build_act(src, r, rows, pointing)
        except Hold as h:
            holds.append({"id": pid, "title": clean(r.get("naslov") or "")[:160], "reason": str(h)})
            src.drop(pid)
            continue
        src.drop(pid)
        if act is None:
            pending += 1
            continue
        kind, year = act["slug"].split("-")[0], act["slug"].split("-")[1]
        dec = year[:3] + "0"
        name = f"{PREFIX_ORDER.get(kind, 85)}-{kind}-{dec}s"
        parts[name]["acts"].append(act)
        parts[name]["laws"].update(laws)
    PARTS.mkdir(exist_ok=True)
    decisions = [
        "Each act's text as enacted (PIS 'Osnovni') takes effect on the day PIS's register gives as its start of "
        "validity (veljaOd); this is the in-force day, not the day of publication.",
        "Each unofficial consolidated text (NPB) takes effect on the in-force day of the act PIS names as the one "
        "whose entry into force produced it, and every unit it changes is credited to that act.",
        "A consolidated text produced by an official consolidated text (UPB), which has no in-force day, is dated by "
        "the UPB's publication in the Uradni list and credited to it.",
        "An act PIS records as no longer valid ends with a version without units, dated PIS's 'valid until' day when "
        "a related act (one its relations name, or one whose relations name it) took effect or began to apply on that "
        "day, else the day after when one did on that day; if both or neither, it is held back.",
        "An act is published only if every act PIS lists as changing its text, and every Constitutional Court decision "
        "annulling part of it, took effect on a day for which PIS has a consolidated text (or before the act, or "
        "after it ceased); the others are held back.",
        "Publisher typesetting is normalised once: NBSP as a space, one form of quotes and dashes, table cells "
        "separated by ' | '. Annexes PIS keeps as separate files are named by their link text only.",
        "The words of every version, read back from its units, equal the words of PIS's text for that version.",
    ]
    written = []
    for name in sorted(parts):
        p = parts[name]
        p["acts"].sort(key=lambda x: x["slug"])
        out = {}
        if name == min(parts):
            out["country"] = COUNTRY
        out["laws"] = dict(sorted(p["laws"].items()))
        out["acts"] = p["acts"]
        out["sources"] = [{"name": "PIS: Pravno-informacijski sistem Republike Slovenije (Register predpisov)",
                           "url": "https://pisrs.si", "retrieved": a.retrieved,
                           "licence": "Official texts of regulations are not protected by copyright (ZASP, 9. člen); "
                                      "PIS data reused with attribution",
                           "notes": "Register entries, relations between acts, and the text as enacted and every "
                                    "unofficial consolidated text (NPB) of each act, from https://pisrs.si/api."}]
        out["decisions"] = decisions
        out["ai_use"] = ["none"]
        f = PARTS / f"{name}.json"
        b = (json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if not f.exists() or f.read_bytes() != b:
            tmp = f.with_suffix(".tmp")
            tmp.write_bytes(b)
            tmp.replace(f)
        pub = PARTS / f"{name}.PUBLISH"
        line = (f"{len(p['acts'])} acts: every version's words read back from its units equal PIS's text "
                f"(retrieved {a.retrieved}); dates from PIS's register.\n")
        if not pub.exists() or pub.read_text(encoding="utf-8") != line:
            pub.write_text(line, encoding="utf-8", newline="\n")
        written.append((name, len(p["acts"])))
    if a.report:
        Path(a.report).write_text("".join(json.dumps(h, ensure_ascii=False) + "\n" for h in holds), encoding="utf-8")
    reasons = defaultdict(int)
    for h in holds:
        reasons[h["reason"].split(":")[0]] += 1
    print(json.dumps({"registered": len(rows), "published": sum(n for _, n in written), "held": len(holds),
                      "pending_fetch": pending, "held_by_reason": dict(sorted(reasons.items())), "parts": len(written)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
