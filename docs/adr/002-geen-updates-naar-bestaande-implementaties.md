# ADR-002: Geen framework-updates naar bestaande implementaties

Status: Accepted
Datum: 2026-09-15

## Context

Het framework wordt doorontwikkeld: verbeteringen die tijdens een klantproject
ontstaan moeten beschikbaar komen voor volgende klanten. De vraag is of ze ook
terug moeten naar reeds opgeleverde implementaties.

Een mechanisme daarvoor (bijvoorbeeld de generieke logica als Python-package in
een Fabric Environment) kost weken refactoring en levert permanente wrijving op:
Environments publiceren duurt 10-20 minuten per workspace, en er ontstaat een
compatibiliteitsmatrix tussen framework- en klantversies.

## Beslissing

Een klantimplementatie neemt na oplevering **geen framework-updates** over.
Het framework is een startpunt, geen runtime dependency.

Er is één gedocumenteerd uitzonderingspad voor kritieke fixes:

```bash
git remote add framework <framework-repo>
git fetch framework
git cherry-pick <sha>
```

Daarna volgt de fix de normale route naar Test en Prod. Bij een schemawijziging
hoort een migratiescript (ADR-004).

De stroom die wél bestaat is omgekeerd: verbeteringen uit klantwerk worden
handmatig teruggebracht naar het framework en vastgelegd in de CHANGELOG.

## Alternatieven

- **Generieke logica als versioneerbaar Python-package.** Verworpen voor nu:
  de investering verdient zich pas terug bij meerdere klanten met een
  supportverplichting. Zie de trigger hieronder.
- **Framework-items in een aparte workspace per omgeving.** Verworpen:
  cross-workspace referenties bevatten workspace-ID's die bij promotie breken.

## Gevolgen

- Security- en bugfixes propageren niet automatisch. Dit is een bewuste keuze,
  geen omissie.
- Na meerdere klanten bestaan er evenzoveel divergerende codebases. Bij een
  support- of managed-serviceafspraak is dat een reële kostenpost.
- De framework-versie wordt bij oplevering vastgelegd in de klantomgeving
  (tag + datum), zodat later te achterhalen is welke basis er draait.
- **Trigger tot heroverweging:** bij ±5 klanten met supportafspraak, of zodra
  dezelfde fix voor de derde keer handmatig is overgezet.
