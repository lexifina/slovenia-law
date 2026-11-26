<!-- lawwatch: written from data/checks by the check trail; edit the records, not this page -->

# Spremljanje virov: kaj se spremlja (Slovenija)

[English](WATCHING.en.md)

Kako global-law spremlja vire vseh držav: [global-law WATCHING.md](https://github.com/lexifina/global-law/blob/main/WATCHING.md). Ta stran je enaka, omejena na eno državo (Slovenija): vsak uradni vir, iz katerega ta repozitorij jemlje besedila, kaj se na njem bere, kako pogosto in kdaj je bil nazadnje prebran. Vsako branje in kaj je iz njega nastalo: [monitoring/](monitoring/README.md).

| Vir | Kaj se bere | Mape | Kako pogosto | Zadnje branje | Stanje |
| --- | --- | --- | --- | --- | --- |
| [PISRS: Register predpisov in Uradni list RS](https://pisrs.si) | Uradni list RS dan za dnem (vsak objavljeni akt z ID v PIS); za vsak zakon, ustavni zakon in odločbo Ustavnega sodišča v njem akti, ki jih spreminja ali razveljavlja, in dan začetka veljavnosti; ter vpisi v registru za 60 predpisov tukaj na preverjanje (veljaven ali ne, najnovejše prečiščeno besedilo), vsak predpis približno vsakih 64 dni | `ustava/`, `zakon/`, `uredba/`, `pravilnik/`, `sklep/` | dnevno | 2026-11-26 05:23 UTC | spremljan: PISRS celoten register navaja le prek API za razvijalce, ki zahteva ključ; tu se bere vmesnik za njegovo spletno stranjo, ena zahteva na 2 sekundi |
| [Uradni list RS: spletišče Uradnega lista (uradni-list.si)](https://www.uradni-list.si) | — |  | — | — | zaprt vir: hrani izdaje do 28. februarja 2026; poznejše izdaje so objavljene v PISRS, ki se bere zgoraj |

Viri se berejo v mejah njihovih datotek robots.txt in pogojev uporabe, s premori med zahtevami.
