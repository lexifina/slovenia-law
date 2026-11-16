# Slovenija: zgodovina prava v gitu

**Slovenščina** · **[Or read it in English](README.en.md)**

<picture>
<source media="(prefers-color-scheme: dark)" srcset="data/sl/effort-dark.svg">
<img alt="Predpisi Slovenije v tem repozitoriju: kaj vsebuje, spremembe po letu začetka veljavnosti, popolnost glede na uradne vire in pravilnost vsebine" src="data/sl/effort-light.svg" width="880">
</picture>

Pravo Slovenije kot zgodovina git: ena datoteka za vsako določbo, en commit za vsako različico na dan, ko je začela veljati, avtor vsakega commita pa je predpis, ki je spremembo uvedel. `git blame` pri vsakem členu pokaže predpis, ki stoji za njim; `git log` navede vsako spremembo člena; z izbiro datuma dobite besedilo, ki je veljalo tisti dan.

Del projekta [lexifina/global-law](https://github.com/lexifina/global-law), enotne zgodovine git za pravo vseh držav: to je slovensko državno pravo, ki ga global-law bere na poti `slovenia/national/acts/`.

**Kaj vsebuje zdaj:** Ustavo in Zakon o volitvah v državni zbor z vsemi različicami (vsak po 13); 1.850 drugih predpisov iz registra PIS (vsi razen treh so zakoni) s 3.044 različicami, med njimi 742 predpisov, ki so medtem prenehali veljati, in 958 novel; ter 1.971 drugih veljavnih predpisov (1.954 zakonov in 17 uredb), vsakega le v trenutnem besedilu. [`registry/ACTS.md`](registry/ACTS.md) navaja 1.850 predpisov po vrstah, [`data/veljavni-predpisi.csv`](data/veljavni-predpisi.csv) 1.971 veljavnih, [`akti.csv`](akti.csv) pa akte, iz katerih izhaja vsaka različica prvih dveh.

Vsak predpis je v `<vrsta>/<leto>/<id PIS>/`, z eno datoteko za vsak člen (`ustava/1991/usta1/clen-068.md` je 68. člen Ustave Republike Slovenije; `zakon/2013/zako5944/` je Zakon o delovnih razmerjih, ZDR-1). Do 10. novembra 2026 je imela večina map ime po kratici predpisa (`urs/`); [`data/paths.json`](data/paths.json) vsako poveže z njeno mapo, `git log --follow` pa datoteki sledi tudi čez premik.

Besedilo je v slovenščini, kot ga objavlja PIS. Prevod v angleščino ni del tega zapisa.

## Vprašanja kot ukazi git

| Vprašanje | Ukaz |
| --- | --- |
| Vse spremembe 68. člena Ustave | `git log -p --follow --word-diff -- ustava/1991/usta1/clen-068.md` |
| Kateri predpis je napisal posamezno vrstico 68. člena? | `git blame ustava/1991/usta1/clen-068.md` |
| Vse različice Ustave z dnem, ko je vsaka začela veljati | `git log --format="%h %(trailers:key=In-force,valueonly,separator=) %an" -- ustava/1991/usta1 urs` |
| 68. člen, kot je veljal 13. julija 1997, dan preden ga je spremenil UZS68 | `python tools/na_dan.py 1997-07-13 urs 68` |

**Zunaj gita** ta zapis tudi javno in brezplačno gostimo:

- **[Vprašajte Claude o slovenskem pravu](https://global-law.lexifina.com/v1/try_claude?country=slovenia)**: odpre Claude s pripravljenim prvim vprašanjem.
- **[Vprašajte ChatGPT](https://global-law.lexifina.com/v1/try_chatgpt?country=slovenia)**: isto vprašanje v ChatGPT.
- **[Iščite po slovenskem pravu na naši spletni strani](https://lexifina.com/law?country=slovenia&q=letni+dopust)**: iskanje „letni dopust“, z besedilom vsake določbe in njenimi različicami, brez računa.
- **[REST API za razvijalce](https://global-law.lexifina.com/v1/search_law?query=letni+dopust&jurisdiction=slovenia)**: isto iskanje kot JSON, brez ključa. Dokumentacija je [tukaj](https://lexifina.com/api/global-law).

Pomočnika zapis bereta prek brezplačnega konektorja Global law (MCP, `https://global-law.lexifina.com/mcp`); prvič vam pogovor ponudi povezavo, s katero ga dodate. Vprašajte v slovenščini ali angleščini.

**Preprosto ga gostite sami.** Potrebujete le git in Python, orodja pa tečejo na vašem računalniku:

```sh
git clone --depth 1 https://github.com/lexifina/global-law && cd global-law
python3 tools/countries.py add slovenia/national/acts
python3 tools/law.py show 2026-01-01 slovenia/national/acts/ustava/1991/usta1/clen-068.md
```

Odprt v Claude Code, Cursorju, VS Code ali Codexu klon zažene tudi lokalni strežnik MCP z enakimi orodji ([MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md)).

## Datumi

Vsak commit je datiran opoldne po ljubljanskem času (Europe/Ljubljana) na dan, ko je različica začela veljati, ta dan pa nosi tudi v traileru `In-force:`:

- za vsako različico dan, ki ga register PIS navaja kot začetek veljavnosti (velja od) predpisa, iz katerega izhaja;
- ustavni zakoni začnejo veljati z razglasitvijo v Državnem zboru, nekaj dni preden jih natisne Uradni list; dve odločbi Ustavnega sodišča in uradno prečiščeno besedilo Zakona o volitvah v državni zbor v registru nimajo dneva začetka veljavnosti, zato so datirani z dnem objave; vsak tak commit to navaja v `Date-note:`;
- predpis, ki je tu le v trenutnem besedilu, je datiran z dnem, ko je sam začel veljati, če ga PIS ni nikoli prečistil, sicer z dnem začetka veljavnosti predpisa, iz katerega izhaja njegovo najnovejše prečiščeno besedilo;
- git ne more shraniti datumov pred letom 1970, zato sta različici, ki sta začeli veljati prej (1949 in 1965), datirani s 1. januarjem 1970, pravi dan pa je v `In-force:`.

Vsaka sprememba je pripisana predpisu, ki jo je uvedel, kot ga navaja PIS (`Uradni list RS, št. 42/97 (UZS68)`, odločba Ustavnega sodišča kot `odl. US`), vendar le, kadar besedilo tega predpisa spremembo pojasni. Vse drugo, tudi trenutna besedila 445 veljavnih predpisov, ki jih je PIS prečistil, in 742 prenehanj veljavnosti, je commit avtorja `PIS RS (neuradno prečiščeno besedilo)`, nikoli predpisa.

## Kako se preverja

- `tools/check_repo.py` vsako različico Ustave in Zakona o volitvah v državni zbor prebere iz gita na dan, ko je začela veljati, in jo primerja s PIS, datoteko za datoteko in besedo za besedo z vsemi besedami, ki jih PIS daje za to različico: 26 različic, 0 neujemanj.
- `tools/test_repo.py` preverja blame, orodje za datume, vrstni red `git log --follow`, oznake, trailerje in avtorje; druga izgradnja iz istih podatkov je dala iste hashe. Oboje je v [`REPRODUCE.md`](REPRODUCE.md).
- 1.850 predpisov iz registra zgradi `registry/tools/build/` iz ene datoteke korpusa, katere sha256 navaja [`registry/REPRODUCE.md`](registry/REPRODUCE.md); preverjanje te izgradnje tam še ni zabeleženo.
- [vulnerabilities/](vulnerabilities/): mogoče napake pri pripravi slovenskih predpisov, ki so jih našli detektorji global-lawa in so bile ročno preverjene.

## Česa ne prikazuje

- **Prejšnjih različic 1.971 veljavnih predpisov**, ki so tu v trenutnem besedilu; dodane bodo pred njim, ne da bi se zgodovina prepisala.
- **Podzakonskih in lokalnih predpisov, sodne prakse in prava EU.** Razen 20 uredb in drugih izvršilnih predpisov zapis vsebuje le zakone.
- **Predpisa, ki je razveljavil drug predpis.** Ob prenehanju veljavnosti se besedilo predpisa odstrani na dan, ki ga PIS navaja kot konec veljavnosti, s commitom avtorja PIS, ne predpisa, ki ga je razveljavil.
- **Odločb Ustavnega sodišča**, ki določbo razglasijo za neustavno, ne da bi spremenile njeno besedilo; PIS jih zabeleži v registru, ne v besedilu.
- **Opomb PIS**, njegovih povezav na sodno prakso in pravo EU ter seznama aktov na začetku vsakega prečiščenega besedila (akti so v commitih).

## Viri

| Vir | Vrsta | Prejšnje različice | Opombe |
| --- | --- | --- | --- |
| [PIS, Pravno-informacijski sistem Republike Slovenije](https://pisrs.si) (Služba Vlade Republike Slovenije za zakonodajo) | Uradni register predpisov z besedilom, kot je bilo sprejeto, in neuradnimi prečiščenimi besedili (NPB) | da, vsako prečiščeno besedilo z dnem začetka veljavnosti | Prebrano prek vmesnika JSON PIS; prečiščena besedila so le informativna, verodostojen je samo Uradni list Republike Slovenije |

## Licenca

Glejte [`LICENSE`](LICENSE). Uradna besedila z zakonodajnega, upravnega in sodnega področja v Sloveniji niso varovana z avtorsko pravico (2. točka prvega odstavka 9. člena ZASP); zgodovina, sporočila commitov, tabele in orodja so objavljeni pod licenco CC0 1.0.

Noben model umetne inteligence ni napisal ali spremenil pravnega besedila; skripte je napisal model umetne inteligence (glejte [`REPRODUCE.md`](REPRODUCE.md)).

To je prevod angleške različice ([README.en.md](README.en.md)); če se razlikujeta, velja angleška različica.

## Več

Iz repozitorija [lexifina/global-law](https://github.com/lexifina/global-law) (v angleščini):

- [FEATURES.md](https://github.com/lexifina/global-law/blob/main/FEATURES.md): vse funkcije in kaj mora podpirati vsak korpus (`git blame`, `law.py`, orodja MCP)
- [FAQ.md](https://github.com/lexifina/global-law/blob/main/FAQ.md): vprašanja in odgovori · [CONTRIBUTING.md](https://github.com/lexifina/global-law/blob/main/CONTRIBUTING.md): predlaganje sprememb · [MCP.md](https://github.com/lexifina/global-law/blob/main/MCP.md): strežnik MCP · [REPRODUCE.md](https://github.com/lexifina/global-law/blob/main/REPRODUCE.md): kako je nastal · [CHANGELOG.md](https://github.com/lexifina/global-law/blob/main/CHANGELOG.md)
- [FRESHNESS.md](https://github.com/lexifina/global-law/blob/main/FRESHNESS.md): kako ažuren je vsak korpus · [Spremljanje](https://github.com/lexifina/global-law/tree/main/monitoring): ali posodobitve delujejo · [WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md): kako se pri vsakem uradnem viru spremljajo spremembe
- [performance/](https://github.com/lexifina/global-law/tree/main/performance): kako hitra so orodja, izmerjeno
- [visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations): grafi in povezave v pravu vsega sveta
- [Ranljivosti](https://github.com/lexifina/global-law/tree/main/vulnerabilities): napake v predpisih, kot so bili objavljeni
