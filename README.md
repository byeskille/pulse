## https-norge

Dette er en norsk versjon av prosjektet [`pulse`](https://github.com/18F/pulse) (The pulse of the federal .gov webspace) for å vise hvordan det står til med HTTPS-bruken på domener eid av offentlige etater og virksomheter i Norge.
Løsningen for Norge benytter seg av en liste domener samlet inn av NRK. ~~Domenelisten er tilgjengelig som datasettet [norway-gov-domains](https://github.com/byeskille/norway-gov-domains)~~
Oppdatert: Domenelisten ble tatt ned fra Github sommeren 2016 etter ønske fra Norid som med henvisning til Åndsverksloven mente at listen som baserer seg på data fra blant annet dem ikke kunne ligge ute.

Prosjektet er laget av NRK, og journalist Øyvind Bye Skille, i bakkant av en rekke saker om temaet.
Se blant annet:

* [http://www.nrk.no/dokumentar/xl/1.12854582](http://www.nrk.no/dokumentar/xl/1.12854582)
* [http://www.nrk.no/dokumentar/xl/1.12859753](http://www.nrk.no/dokumentar/xl/1.12859753)

Løsningen er helt og fullt basert på kode fra virksomheten [18F](https://18f.gsa.gov), underlagt [General Services Administration](http://gsa.gov) og Det hvite hus.
Denne koden er så videre bearbeidet for bruk til en tysk versjon [https.jetzt!](https://https.jetzt) av [robbi5](https://github.com/robbi5/pulse).

Den norske versjonen er så igjen bygget på den tyske, en fork.
Tusen takk til begge miljøer for kode og spesielt til [robbi5](https://robbi5.de) for svar på noen dumme spørsmål fra en journalist som ikke egentlig er utvikler.

Det er ikke laget noen fullstendig dokumentasjon for den norske versjonen, men viderebringer info fra den tyske og amerikanske under.

## Kjente bugs:

* På oversikten over domeneeiere under [`Lokale og regionale`](https://nrkbeta.no/https-norge/https/city/agencies/) fungerer det ikke å trykke på tallet for domenene tilknyttet til etaten/virksomheten for å få opp domenene. Søket gjøres da mot `https/domains` og ikke `https/city/domains` slik det skal.

---

## https.jetzt!

Dieses Projekt bietet eine Übersicht, ob Domains deutscher Behörden das HTTPS-Protokoll (<code>https://</code>) unterstützen, und - falls ja - wie stark diese Unterstützung ist.

Entstanden am [OpenDataDay 2016](http://de.opendataday.org).
Domains aus dem [german-gov-domains](https://github.com/robbi5/german-gov-domains)-Datensatz.

Basierend auf [the pulse of the federal .gov webspace (pulse.cio.gov)](https://pulse.cio.gov) von [18F](https://18f.gsa.gov)/[General Services Administration](http://gsa.gov).

Dieses Repository ist somit ein Fork von [18F/pulse](https://github.com/18F/pulse) - die originale Readme hängt unten an.

### Neue Domains hinzufügen/Neu scannen:

Die Domains am besten dem [german-gov-domains](https://github.com/robbi5/german-gov-domains)-Datensatz hinzufügen.

Danach lassen sich mit Hilfe des [`domain-scan`-Containers](https://github.com/18F/domain-scan) neue scan-Ergebnisse erzeugen: `make update_httpsjetzt`

---

## The pulse of the federal .gov webspace

How the .gov domain space is doing at best practices and federal requirements.

| Documentation  |  Other Links |
|---|---|
| [Setup and Deploy Instructions](https://github.com/18F/pulse/blob/master/docs/setup.md)  |  [System Security Plan](https://github.com/18F/pulse/blob/master/system-security-plan.yml) |
| [a11y scan process](https://github.com/18F/pulse/blob/master/docs/a11y-instructions.md)  | [Ideas for new sections to add to the site](https://github.com/18F/pulse/blob/master/docs/other-sections.md) |
| [Ongoing Work](https://github.com/18F/pulse/blob/master/docs/project-outline.md) | [Backlog of feature requests and ideas](https://github.com/18F/pulse/issues?utf8=%E2%9C%93&q=is%3Aissue%20label%3Abacklog)  | 
|  [ATO artifacts](https://github.com/18F/pulse/blob/master/docs/ato.md)  | [Open Source Reuse of the site](https://github.com/18F/pulse/blob/master/docs/reuse.md) |
| [Project Information](https://github.com/18F/pulse/blob/master/.about.yml)  |  |


### Public domain

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
