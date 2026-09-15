# ADR-004: Metadata-schema via genummerde migratiescripts

Status: Accepted
Datum: 2026-09-15

## Context

De `integration.*`-tabellen bevatten de configuratie die Landingzone, Bronze en
Silver aanstuurt. Deployment Pipelines en fabric-cicd verplaatsen *items*, geen
*rijen* — metadata reist dus niet mee met een deployment.

Daarbij is dit het enige onderdeel waar een wijziging pijn doet bij een bestaande
klant, omdat er data in zit die behouden moet blijven. Een `CREATE`-script alleen
is daarvoor niet genoeg.

## Beslissing

Het metadata-schema wordt beheerd via genummerde, idempotente migratiescripts:

```
/metadata/migrations/001_initial_schema.sql
/metadata/migrations/002_add_incremental_watermark.sql
```

Elke omgeving houdt bij welke migraties zijn toegepast. Migraties worden nooit
gewijzigd nadat ze zijn uitgerold; een correctie is een nieuwe migratie.

Structurele metadata (bronnen, entiteiten) wordt als seed in de repo beheerd en
is reviewbaar in een PR. Operationele vlaggen (`IsActive`, watermarks, overrides)
blijven in de database en worden niet gepromoveerd.

## Alternatieven

- **Alleen een `CREATE`-script per release.** Verworpen: werkt niet op een
  omgeving waar al data staat.
- **Alle metadata als data, promotie handmatig.** Verworpen: niet auditbaar en
  niet reproduceerbaar over klanten heen.
- **Alle metadata as-code.** Verworpen: "even een tabel uitzetten in Prod" moet
  zonder deployment kunnen.

## Gevolgen

- Migraties draaien als stap in de deployment-workflow (ADR-006), per omgeving.
- De splitsing structureel/operationeel moet per veld expliciet gemaakt worden;
  bij twijfel operationeel.
- Bij oplevering van een nieuwe klant draaien alle migraties op volgorde — dat is
  meteen de test of ze compleet zijn.
