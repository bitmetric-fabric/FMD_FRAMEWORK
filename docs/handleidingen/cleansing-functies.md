---
title: Cleansing-functies
sidebar_position: 7
---

# Cleansing-functies

Een cleansingregel is een bewerking die Bronze of Silver bij het laden op een of meer kolommen uitvoert. Deze pagina beschrijft elke ingebouwde functie: wat ze doet, voor welke laag ze bedoeld is en welke parameters ze heeft. Hoe je een regel instelt in de editor, staat in [Een bestaande tabel wijzigen](tabel-wijzigen.md#een-cleansingregel-wijzigen).

## Hoe een regel werkt

Een regel bestaat uit drie delen:

| Deel | Betekenis |
|---|---|
| **Functie** | De naam van de functie, bijvoorbeeld `normalize_text`. |
| **Kolommen** | De kolommen waarop de functie werkt. In de editor kies je ze uit een lijst; in de configuratie staan ze gescheiden door een puntkomma (`KolomA;KolomB`). |
| **Parameters** | De instellingen van de functie, een lijst met namen en waarden. Elke parameter is optioneel, tenzij de tabel hieronder anders zegt. |

Per laag is het een lijst van regels. De regels draaien na elkaar, in de volgorde van de lijst, elk op het resultaat van de vorige.

**Welke laag?**

- Bronze draait de regels op de gelezen data, vóór de merge naar Bronze.
- Silver draait de regels op wat uit Bronze komt.
- Een Silver-regel werkt alleen op rijen die daarna veranderen. Voor de hele tabel zet je Silver opnieuw in de wachtrij met de actie *Silver opnieuw laten verwerken* op tab 5. Zie [Een cleansingregel wijzigen](tabel-wijzigen.md#een-cleansingregel-wijzigen).

## Overzicht

| Functie | Wat ze doet | Laag |
|---|---|---|
| [`normalize_text`](#normalize_text) | Tekst opschonen: spaties, hoofdletters, lege tekst als NULL | Bronze of Silver |
| [`fill_nulls`](#fill_nulls) | NULL vervangen door een standaardwaarde | Bronze of Silver |
| [`parse_datetime`](#parse_datetime) | Tekst omzetten naar een datum of tijdstempel | Bronze of Silver |
| [`clamp_min_date`](#clamp_min_date) | Datums onder een minimum vervangen | Bronze of Silver |
| [`exclude_rows`](#exclude_rows) | Rijen weglaten met bepaalde waarden | Silver |
| [`deduplicate_keys`](#deduplicate_keys) | Eén rij per sleutel houden als een bron een sleutel meerdere keren levert | Bronze |

Een eigen functie is ook mogelijk, zie [Een eigen functie](#een-eigen-functie).

## normalize_text

Maakt tekst schoon. Elke tekst wordt altijd van spaties aan het begin en einde ontdaan. Daarna gelden de parameters.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `case` | `lower`, `upper`, `title` | geen (hoofdletters blijven) | Zet de tekst om naar kleine letters, hoofdletters of een hoofdletter per woord. |
| `collapse_spaces` | `true`, `false` | `true` | Vervangt twee of meer spaties achter elkaar door één spatie. |
| `empty_as_null` | `true`, `false` | `true` | Maakt van een lege tekst NULL. |

Voorbeeld: kolom `Name`, `case = lower`. De waarde `  Euro   Zone ` wordt `euro zone`.

## fill_nulls

Vervangt NULL door een standaardwaarde. De waarde hangt af van het type van de kolom, of je geeft een waarde per kolom op.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `default_string` | tekst | geen | Vult NULL in kolommen van het type tekst. |
| `default_numeric` | getal | geen | Vult NULL in kolommen met een numeriek type. |
| `default_date` | datum als `yyyy-MM-dd` | geen | Vult NULL in kolommen van het type datum. |
| `defaults` | een waarde per kolomnaam | geen | Een waarde voor een bepaalde kolom, bijvoorbeeld `{"Region": "onbekend"}`. Gaat voor op de drie andere parameters. |

- Een kolom waarvoor geen standaardwaarde past bij haar type, blijft zoals ze is.
- `default_date` geldt voor kolommen van het type datum, niet voor tijdstempels.
- In de editor vul je `defaults` in als JSON.

## parse_datetime

Zet tekst om naar een datum of tijdstempel.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `target_type` | `date`, `timestamp` | `date` | Het type van het resultaat. |
| `formats` | lijst van formaten, bijvoorbeeld `yyyy-MM-dd`, `dd/MM/yyyy` | `yyyy-MM-dd` | De formaten die geprobeerd worden. Het eerste formaat dat past, bepaalt de waarde. |
| `into` | kolomnaam | geen | Schrijft het resultaat naar een nieuwe kolom. Werkt alleen als er precies één kolom is gekozen. |
| `keep_original` | `true`, `false` | `true` | Alleen bij `into`: bewaart de oorspronkelijke kolom of laat haar weg. |

Zonder `into` vervangt het resultaat de oorspronkelijke kolom.

## clamp_min_date

Vervangt datums onder een minimum, bijvoorbeeld de plaatshouder `0001-01-01` die sommige bronsystemen gebruiken. NULL blijft NULL.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `min` | datum als `yyyy-MM-dd` | `1900-01-01` | De ondergrens. |
| `replacement` | datum als `yyyy-MM-dd`, of een tijdstempel | gelijk aan `min` | De waarde die ervoor in de plaats komt. |
| `inclusive` | `true`, `false` | `false` | Bij `false` wordt een waarde kleiner dan `min` vervangen, bij `true` ook een waarde gelijk aan `min`. |

- De kolom moet van het type datum of tijdstempel zijn. Een kolom van een ander type geeft een fout bij het laden.
- Een datum die niet als `yyyy-MM-dd` te lezen is, geeft een fout in plaats van dat de data stilletjes verdwijnt.

Voorbeeld: kolom `ModifiedDate`, `min = 1900-01-01`. De waarde `0001-01-01` wordt `1900-01-01`.

## exclude_rows

Laat rijen weg waarvan een van de gekozen kolommen een van de opgegeven waarden heeft.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `values` | lijst van waarden | **verplicht**, niet leeg | De waarden waarvan de rij wegvalt. De vergelijking negeert hoofdletters en spaties aan de randen. |

- Een NULL in de kolom houdt de rij.
- Met meerdere kolommen valt de rij weg als **een** van de kolommen een van de waarden heeft.

**Gebruik dit als Silver-regel**, bijvoorbeeld voor een bron die een verwijdering levert als rij met een vlag, zoals `EVENT_CRUD = delete`. Silver ziet de sleutel dan als verdwenen en zet de bestaande rij op `IsDeleted = 1` en `IsCurrent = 0`. Gebruik de functie niet als Bronze-regel: bij een incrementele Bronze-merge blijft de bestaande rij dan ongewijzigd staan in plaats van dat ze als verwijderd wordt gemarkeerd.

## deduplicate_keys

Houdt één rij per primary key over als een bron dezelfde sleutel meer dan eens levert.

| Parameter | Waarden | Standaard | Werking |
|---|---|---|---|
| `keep` | `last`, `first` | `last` | `last` houdt de rij met de hoogste waarde in de ordeningskolom, `first` die met de laagste. |

- **Kolommen:** bij deze functie zijn de gekozen kolommen de **ordeningskolommen**, niet de sleutel. Kies bijvoorbeeld een tijdstempel als `EVENT_TIMESTAMP`. De sleutel is de primary key van de tabel.
- **Alleen als Bronze-regel.** Bronze voegt de hashkolom van de primary key al toe vóór de cleansing; de functie heeft die nodig en geeft anders een fout.
- Hebben twee rijen dezelfde waarde in de ordeningskolom (bijvoorbeeld een volledige dump met één tijdstempel), dan kiest de functie op basis van een hash van alle waarden. Een nieuwe laadactie houdt daardoor dezelfde rij.
- NULL in een ordeningskolom telt als de laagste waarde.
- **De functie stopt niet bij een te kleine sleutel.** Is de primary key te kort gekozen, dan vallen er rijen weg zonder fout. Alleen het aantal verwijderde rijen komt in het auditlog van het laden. Controleer de aantallen na het eerste laden.

## Een eigen functie

Een functie die niet is ingebouwd, kun je zelf toevoegen. Voeg hem toe aan het notebook `NB_FMD_CUSTOM_DQ_CLEANSING`. In de editor kies je daarna **(eigen functie)** en vul je de naam en de parameters als JSON in.

- De editor controleert een eigen functie niet. Hij geeft alleen een waarschuwing, omdat hij de functie niet kan zien. Een fout in de naam of in de parameters blijkt dus pas bij het laden.
- Een functie die niet bestaat, geeft bij het laden een fout met de lijst van beschikbare functies.

## Controles in de editor

De editor controleert elke regel voor je registreert. Het resultaat staat in de proefdraai.

| Melding | Betekenis |
|---|---|
| Geen kolommen | Een regel zonder kolommen is een fout. |
| Een kolom die de ontdekking niet kent | Een waarschuwing. Een kolom die niet bestaat, geeft pas bij het laden een fout. |
| Een verplichte parameter ontbreekt | Een fout, bijvoorbeeld `values` bij `exclude_rows`. |
| Een parameter heeft een onjuiste waarde | Een fout, bijvoorbeeld `case` met een andere waarde dan `lower`, `upper` of `title`. |
| Een parameter die de functie niet kent | Een waarschuwing: de functie negeert hem. |
| Een functie die niet is ingebouwd | Een waarschuwing, zie [Een eigen functie](#een-eigen-functie). |
