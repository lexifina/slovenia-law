<!-- lawwatch: written from data/checks by the check trail; edit the records, not this page -->

# Spremljanje: kaj se bere in kaj je iz tega nastalo

[English](README.en.md)

Kako global-law spremlja vse države: [global-law monitoring/](https://github.com/lexifina/global-law/tree/main/monitoring). Ta stran je enaka, omejena na eno državo (Slovenija): vsako branje uradnega vira, kdaj je bilo in kaj je iz njega nastalo (dodani, spremenjeni in odstranjeni predpisi). Strojno berljiva oblika je [data/checks/](../data/checks/) (JSON Lines, shema `lexifina-check/1`), v `git log` so to commiti `Kind: check`, po mesecih pa v [checks/](checks/).

**Zadnje preverjanje:** 2026-11-24 05:47 UTC, PISRS: Register predpisov in Uradni list RS: prebranih naslovov 82; dodanih 0, spremenjenih 0, odstranjenih 0; brez sprememb; neobjavljenih 14, od tega brez razloga 0. Opozorila: `publish-lag`.

## Viri

| Vir | Mape | Kako pogosto | Zadnje uspešno preverjanje | Zadnji izid | Stanje |
| --- | --- | --- | --- | --- | --- |
| [PISRS: Register predpisov in Uradni list RS](https://pisrs.si) | `ustava/`, `zakon/`, `uredba/`, `pravilnik/`, `sklep/` | dnevno | 2026-11-24 05:47 UTC | brez sprememb | spremljan: PISRS celoten register navaja le prek API za razvijalce, ki zahteva ključ; tu se bere vmesnik za njegovo spletno stranjo, ena zahteva na 2 sekundi |
| [Uradni list RS: spletišče Uradnega lista (uradni-list.si)](https://www.uradni-list.si) |  | — | — | — | zaprt vir: hrani izdaje do 28. februarja 2026; poznejše izdaje so objavljene v PISRS, ki se bere zgoraj |

## Zadnjih 30 dni

| Začetek (UTC) | Vir | Prebrano | Dodano | Spremenjeno | Odstranjeno | Neobjavljeno (brez razloga) | Izid | Commiti |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| [2026-11-24 05:44](checks/2026-11.md#si-pisrs-20261124t054419z) | pisrs | 82 | 0 | 0 | 0 | 14 (0) | brez sprememb `publish-lag` | — |
| [2026-11-23 01:46](checks/2026-11.md#si-pisrs-20261123t014603z) | pisrs | 83 | 0 | 0 | 0 | 14 (0) | brez sprememb `publish-lag` | — |
| [2026-11-23 01:42](checks/2026-11.md#si-pisrs-20261123t014214z) | pisrs | 89 | 0 | 0 | 0 | 12 (0) | brez sprememb `publish-lag` | — |

## Preverite sami

```
python tools/checktrail.py                      # zadnje preverjanje vsakega vira
python tools/checktrail.py --day 2026-11-23     # vsa preverjanja enega dne
python tools/checktrail.py --act <id>           # kdaj je bil predpis opažen in objavljen
git log --grep='^Kind: check' --format='%ci %s'  # preverjanja v zgodovini
```

Pravno veljavna je le uradna objava; besedila tukaj so kopije za branje in iskanje.
