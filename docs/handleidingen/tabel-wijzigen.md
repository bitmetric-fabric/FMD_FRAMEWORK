---
title: Een bestaande tabel wijzigen
sidebar_position: 6
---

# Een bestaande tabel wijzigen

Een tabel die al is geregistreerd wijzig je in de registratie-editor op tab 2. Dit gaat over de wijzigingen die het vaakst voorkomen: kolommen of een bronfilter, cleansing rules, historie in Silver, een andere LoadGroup, een tabel uit- of aanzetten, een tabel volledig opnieuw laden en een andere primary key. Hoe je de editor opent en een tabel voor het eerst registreert, staat in [Bronnen en tabellen registreren](registreren.md). De schermafbeeldingen zijn opgenomen in november 2026.

## Het patroon

Elke wijziging verloopt hetzelfde:

1. Open de editor, kies de omgeving (eerst `D` of je eigen ontwikkelomgeving) en klik op **Laden uit de configdb**. De editor laadt niet vanzelf.
2. Ga naar tab **2. Tabellen**, kies de bron, zoek de tabel en klik hem aan. Rechts staan de eigenschappen. Een wijziging blijft in het geheugen van de editor tot je registreert.
3. Ga naar tab **3. Controleren en registreren**, klik op **Controleren** en daarna op **Proefdraaien (dry_run=True)**. Lees de uitkomst.
4. Is de uitkomst goed: vink de bevestiging aan en klik op **Registreren**.
5. Laad de tabel en controleer het resultaat (zie [Een tabel of bron handmatig laden](handmatig-laden.md)).
6. Zet de wijziging door naar Test en Productie (zie [Doorzetten naar Test en Productie](#doorzetten-naar-test-en-productie)).

Zo ziet de tabel eruit voor je iets wijzigt. In deze handleiding is dat een tabel die geregistreerd, actief en niet incrementeel is, met historie in Silver en zonder LoadGroup of cleansing rules.

![Tab 2 met een geregistreerde tabel geselecteerd. Rechts de eigenschappen; de LoadGroup en de vinkjes Actief, Historie in Silver en Incrementeel zijn gemarkeerd.](afbeeldingen/tabel-wijzigen/01-tabel-kiezen.png)

De status in de lijst is *geregistreerd* voor een tabel die al in de configdb staat. Heb je een wijziging gedaan die je nog niet hebt geregistreerd, dan staat er *gewijzigd*.

## De proefdraai lezen

De proefdraai schrijft niets. Hij toont per tabel wat er zou veranderen.

- **Changed** met per veld `oud -> nieuw`, bijvoorbeeld `IsHistorized 1 -> 0` of `LoadGroup (from source) -> nacht`. Zie je een veld dat je niet hebt aangeraakt, ga dan terug naar tab 2.
- **New** is een tabel die nog niet is geregistreerd.
- **WARNING** wijst op een gevolg dat je niet kunt zien in het overzicht, bijvoorbeeld dat een gewijzigde Silver-regel alleen werkt op rijen die daarna veranderen.
- **Active in this workspace but not in this list (left as is)** is de lijst met tabellen die actief zijn maar niet in deze registratie voorkomen. De proefdraai laat ze ongemoeid. Dit is geen waarschuwing.

Het overzicht erboven kleurt elke cel die afwijkt van de configdb oranje, met de oude waarde eronder (*was: ja*). Controleer dat alleen de cellen oranje zijn die je wilt wijzigen.

![Tab 3 na een proefdraai. De oranje cellen tonen de oude waarde; de uitkomst meldt per veld wat verandert en waarschuwt dat een gewijzigde Silver-regel alleen rijen raakt die daarna veranderen.](afbeeldingen/tabel-wijzigen/07-proefdraai.png)

**Registreren** blijft uitgeschakeld tot je het vakje *Ik heb de wijzigingen en de proefdraai gecontroleerd en wil registreren* aanvinkt.

## Kolommen of bronfilter wijzigen

De velden **Kolommen om te laden** en **Bronfilter** staan op tab 2 onder de eigenschappen van de tabel. Ze werken alleen voor bronnen waarvan de kolommen zijn ontdekt (SQL, Snowflake en OData).

- **Een filter wijzigen** verwijdert niets uit Bronze en Silver. Een ruimer filter haalt bij een incrementele tabel de oudere rijen niet alsnog op: reset dan het watermark (zie [Een tabel volledig opnieuw laden](#een-tabel-volledig-opnieuw-laden)).
- **De proefdraai voert het filter niet uit.** Controleer het filter eerst met een query op de bron.
- **Kolommen weghalen bij een tabel die al in Bronze staat** laat de Bronze-merge falen. Gebruik daarom eerst op tab 5 de actie **Opruimen na een PK-wijziging (Bronze en Silver wissen)**: die wist de Bronze- en Silver-tabel van de tabel, zet de open wachtrij op verwerkt en maakt het watermark leeg. Registreer daarna de nieuwe kolommen en laad de tabel opnieuw volledig. Die actie staat beschreven in [Registratie overzetten en beheren](overzetten-en-beheren.md).
- **Kolommen erbij** is niet apart gedocumenteerd. Probeer het eerst in Dev.
- **Per omgeving verschillend?** Kolommen en filter mogen per omgeving verschillen. Hoe je ze in Test of Productie zet, staat bij [Doorzetten naar Test en Productie](#doorzetten-naar-test-en-productie).

## Een cleansing rule wijzigen

Onderaan de eigenschappen staan twee keuzelijsten: **Bronze-cleansing** en **Silver-cleansing**. Elke laag heeft drie keuzes:

| Keuze | Wat ze doet |
|---|---|
| **Ongewijzigd laten** | De regels van de laag blijven zoals ze in de configdb staan. |
| **Vervangen door onderstaande regels** | De regels in de editor vervangen alle bestaande regels van de laag. |
| **Alle regels verwijderen** | De laag krijgt geen regels meer. |

Achter elke tabel in de lijst staat hoeveel regels ze heeft: `(B:1 S:0)` is één Bronze-regel en geen Silver-regel.

Kies **Vervangen door onderstaande regels** en klik op **Regel toevoegen**. De regels die je hier invult vervangen alle bestaande regels van de laag: neem de regels die al bestonden dus mee.

![De keuzelijst Bronze-cleansing staat op Vervangen door onderstaande regels. Daaronder de knop Regel toevoegen en de keuzelijst Silver-cleansing.](afbeeldingen/tabel-wijzigen/02-cleansing-kiezen.png)

Een regel bestaat uit een **Functie**, de **Kolommen** waarop ze werkt en de parameters van die functie. De knoppen ↑ en ↓ veranderen de volgorde, ✕ verwijdert de regel.

De lijst met functies bevat onder meer `normalize_text`, `fill_nulls`, `parse_datetime`, `clamp_min_date`, `exclude_rows` en *(eigen functie)*. In het voorbeeld gebruikt Bronze `normalize_text` op de kolom `Name`, met de parameter `case` op `lower`.

![Het formulier voor een Bronze-regel: functie normalize_text, de kolom Name gekozen en de parameter case op lower.](afbeeldingen/tabel-wijzigen/03-regel-bronze.png)

Silver gebruikt hier `clamp_min_date` op de kolom `ModifiedDate`. Die functie heeft de parameters `min`, `replacement` en `inclusive`.

![Het formulier voor een Silver-regel: functie clamp_min_date, de kolom ModifiedDate gemarkeerd en de parameters min, replacement en inclusive.](afbeeldingen/tabel-wijzigen/04-regel-silver.png)

Registreer en bekijk wat de regel doet:

- **Een Bronze-regel** werkt vanaf de volgende levering.
- **Een Silver-regel** werkt alleen op rijen die daarna veranderen. Moet de regel op de hele tabel gelden, zet de tabel dan opnieuw in de wachtrij van Silver. De volgende run van `PL_FMD_LOAD_SILVER` bouwt hem dan opnieuw op uit Bronze. Dat doe je met de procedure `execution.sp_RequeueSilverLayerEntities`, of met `register(…, dry_run=False, requeue_silver=True)` in de cel *Zonder editor (geavanceerd)* van het notebook. De knoppen van de editor hebben hiervoor geen keuze.
- Verandert de regel het type van een kolom of de kolommen zelf, verwijder dan eerst de Silver-tabel.

Een eigen cleansing-functie zet je eerst in `NB_FMD_CUSTOM_DQ_CLEANSING`, in Dev, en promoveer je daarna met de CODE-workspace.

## Historie in Silver aan- of uitzetten

Het vinkje **Historie in Silver** staat tussen **Actief** en **Incrementeel**. Haal het weg of zet het aan en registreer.

![Het vinkje Historie in Silver is uitgezet en gemarkeerd.](afbeeldingen/tabel-wijzigen/05-historie-uit.png)

- **Aanzetten:** de historie begint vanaf dat moment.
- **Uitzetten:** de bestaande historie blijft staan. Ruim haar zelf op (`IsCurrent = 0 AND IsDeleted = 0`) als je de opslag terug wilt.
- Een Gold-query op `IsCurrent = 1` werkt in beide standen.

## Een tabel uitzetten of weer aanzetten

Haal het vinkje bij **Actief** weg en registreer. De tabel laadt dan in geen enkele laag meer. De data in Bronze en Silver blijft staan.

Op tab 3 is dan alleen de cel *Actief* oranje, en de proefdraai meldt `IsActive 1 -> 0`.

![Tab 3 met alleen de cel Actief oranje (nee, was: ja) en in de uitkomst de regel Changed met IsActive 1 -> 0.](afbeeldingen/tabel-wijzigen/08-tabel-uitzetten.png)

- **Verwijder een tabel nooit uit de configdb.** Uitzetten is het stoppen.
- **Weer aanzetten:** vink **Actief** aan en registreer. Leveringen die nog in de wachtrij stonden, worden eerst verwerkt.
- **Wordt de tabel in Gold gebruikt?** Controleer dan vooraf wat het uitzetten daar doet: de materialized lake views blijven bestaan, maar krijgen geen nieuwe data.

## Een tabel in een andere LoadGroup zetten

Vul bij **LoadGroup** de naam van de groep in. Leeg betekent: de groep van de bron. De waarde slaat op als je het veld verlaat.

![Het veld LoadGroup, ingevuld met nacht.](afbeeldingen/tabel-wijzigen/06-loadgroup.png)

- Controleer dat er een schema met die groep bestaat in de scheduler van elke omgeving (zie [Dagelijkse routine en schedules](dagelijkse-routine.md)). Anders laadt de tabel nergens op een schema.
- Een tabel in een andere groep dan haar bron laadt niet mee in een run voor de groep van de bron. Een run zonder groep laadt alles.

## Een tabel volledig opnieuw laden

- **Eenmalig:** ga naar tab **5. Beheer**, laad de omgeving, selecteer de tabel en kies de actie **Watermark resetten (de volgende load laadt alles)**. Start daarna `PL_FMD_LOAD_ALL` voor alleen deze tabel (zie [Een tabel of bron handmatig laden](handmatig-laden.md)). Verwijder de watermarkrij niet.
- **Van incrementeel naar volledig:** haal het vinkje bij **Incrementeel** weg en registreer. Een volledige load markeert rijen die in de bron ontbreken als verwijderd.
- **Let op bij Snowflake met `delta`:** een volledige load die 0 rijen oplevert, verwijdert alle rijen van die tabel in Bronze.

## Een primary key wijzigen

Een andere primary key verandert hoe Bronze en Silver rijen herkennen. Ga zo te werk:

1. Kies op tab 2 de nieuwe sleutel bij **Primary key** en registreer.
2. Ga naar tab 5, selecteer de tabel en kies de actie **Opruimen na een PK-wijziging (Bronze en Silver wissen)**. Draai eerst de proefdraai.
3. Laad de tabel opnieuw volledig.
4. Controleer de aantallen in Bronze en Silver. Doe dit eerst in Dev.

## Doorzetten naar Test en Productie

Een promotie neemt geen registraties mee. Zet een wijziging na het registreren op tab 4 door, vóór je de DATA-workspace van een domein promoveert. De werkwijze staat in [Registratie overzetten en beheren](overzetten-en-beheren.md).

| Wijziging | Op tab 4 |
|---|---|
| Nieuwe tabel | Weergave **Overzetten**, *alles wat nieuw is* |
| Gewijzigde laadwijze, primary key, cleansing of historie | Vink **Ook tabellen bijwerken die er al staan** aan |
| Kolommen, filter, *Actief* of LoadGroup in het doel | Vink **Voor een omgeving een eigen filter of instelling gebruiken** aan, of registreer in de editor met omgeving `T` of `P` |
| Verwijderde Bronze- of Silver-tabel | Herhaal dit in het doel, vóór de load |

Draai altijd eerst de proefdraai, en laad daarna in het doel.

## Nog niet getest

- Kolommen toevoegen aan een tabel die al in Bronze staat.
- Alle functies van de lijst *Functie*. Dit zijn de schermen van `normalize_text` en `clamp_min_date`; de andere functies hebben eigen parameters.
- De cleansing-keuze *Alle regels verwijderen* en de volgorde-knoppen ↑ en ↓.
