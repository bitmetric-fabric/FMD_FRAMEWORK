# ADR-001: Framework als template repository

Status: Accepted
Datum: 2026-09-15

## Context

Het FMD-framework is het vertrekpunt voor klantimplementaties op Microsoft Fabric.
De eerste implementaties zijn gedaan vanuit een fork van het open-source FMD
Framework. Een fork impliceert een blijvende koppeling met upstream: merges,
conflicten in `.platform`-bestanden en logicalIds, en de verwachting dat
wijzigingen heen en weer stromen.

Die verwachting klopt niet met hoe we willen werken (zie ADR-002).

## Beslissing

De framework-repo wordt ingericht als **GitHub template repository**. Een nieuwe
klantimplementatie start met `gh repo create --template`, niet met een fork.

De relatie met upstream FMD blijft bestaan in de framework-repo zelf, als
`upstream` remote. Klantrepo's hebben die relatie niet.

## Alternatieven

- **Fork per klant.** Verworpen: suggereert een upgradepad dat we niet leveren,
  en geeft merge-conflicten in Fabric-metadatabestanden die inhoudelijk
  betekenisloos zijn.
- **Eén monorepo met alle klanten.** Verworpen: klantcode hoort niet bij elkaar
  in één repo, en scheiding van rechten wordt onwerkbaar.

## Gevolgen

- Een klantrepo heeft geen upstream-koppeling en kan er dus niet per ongeluk
  een merge vandaan halen.
- Een gerichte fix overzetten kan alsnog, door de framework-repo tijdelijk als
  remote toe te voegen en te cherry-picken. Dit is het uitzonderingspad uit ADR-002.
- Elke klantimplementatie erft de `docs/`-map, inclusief deze ADR's.
