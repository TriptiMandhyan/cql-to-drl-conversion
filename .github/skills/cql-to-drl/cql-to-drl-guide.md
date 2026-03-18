# CQL to DRL Conversion Guide

This guide captures practical conversion patterns for year-over-year MIPS measure updates, with emphasis on EMRv2, attribution loops, and fire-once dedup guards.

## 1. Denominator With option_id = all and Multiple Extended Results

When CQL denominator includes multiple ExtendedMeasureResultV2 returns under option_id = all, DRL must emit denominator EMR for each named evidence item.

Example CQL shape:

```cql
define "Denominator":
  exists("Denominator Encounter")
  ,
  if exists("Denominator") then
    return ExtendedMeasureResultV2(Encounter, 'Denominator Encounter', ...)
    and return ExtendedMeasureResultV2(HIV, 'HIV/AIDS Diagnosis', ...)
```

Required DRL pattern:

1. Denominator eligibility rule inserts EncounterDenominator only.
2. Separate denominator EMR rule (salience -10) writes EMR output.
3. Rule is guarded by a dedicated marker fact (`not(exists YearYYYYMipsNNNDenominatorEMR())`).
4. Use accumulate earliest/latest selection for non-encounter evidence to honor "return 1 record even if multiple exist".

## 2. Fire-Once Marker Pattern for EMR

For any EMR-only rule:

```drools
declare YearYYYYMipsNNN<ScopeOrPurpose>EMR
end

rule 'YearYYYY.MipsNNN.<Purpose>.EMR'
salience -10
when
  ...
  and not (exists YearYYYYMipsNNN<ScopeOrPurpose>EMR())
then
  insert(new YearYYYYMipsNNN<ScopeOrPurpose>EMR());
  controlSet.addPatientEMR(...);
end
```

Why: status APIs are generally idempotent; EMR APIs are append-style and will duplicate without explicit guards.

## 3. Single-Encounter `.all` Attribution Pattern

For measures like MIPS155 and MIPS338 where denominator logic is encounter-centric and attribution does not require cross-activity ID matching:

- Keep `.groupAndProvider` status rule with inline loops.
- Keep `.org` status rule with a fire-once marker for org output.
- In EMR rules, emit org/group/provider from one guarded rule:
  - org attribution: `""`
  - groups: iterate `for (String groupExternalId : $encounter.getGroupExternalIds())`
  - provider: `$encounter.providerExternalId`

## 4. Numerator With Multiple Source Definitions

If one numerator option can be satisfied by different evidence sources (for example, direct CPT/G-code activity OR latest qualifying lab result), two DRL rules are valid and preferred when they share one EMR marker.

Pattern:

- `ExtendedMeasureResult.<Option>.Part1` for source A
- `ExtendedMeasureResult.<Option>.Part2` for source B
- both guarded by `not(exists <SharedMarker>())`

This preserves CQL intent while avoiding duplicate EMR output.

## 5. Value Set Rename Checklist (Year Updates)

Always re-check CQL comment block and update DRL value sets exactly:

- diagnosis/value-set renames (example: `HIV_AIDS` -> `338_HIV_AIDS`)
- lab/value-set renames (example: `HIV_VIRAL_LOAD` -> `HIV_VIRAL_LOAD_TESTS`)
- direct reference code year namespace updates

Do not leave old aliases in DRL when CQL has moved to new canonical names.

## 6. Denominator EMR Completeness Checklist

Before finalizing a similar measure:

1. Denominator has an EMR rule (not just status rules).
2. Every denominator ExtendedMeasureResultV2 return name in CQL has a corresponding addPatientEMR output.
3. Rule writes org/group/provider attribution when using `.all` pattern.
4. Rule uses fire-once marker.
5. Rule compiles and passes measure test fixture expectations.

## 7. Quick Review Questions

- Does CQL comment include `//return 1 record even if multiple exist`?
- If yes, where is the marker fact and guard?
- Are denominator evidence records present in EMR output (not only numerator)?
- Are all renamed value sets aligned with the CQL source block?
- Are group/provider loops using `groupExternalIds` and provider presence checks?

## 8. Rule Naming Standard (Required)

Generated rule names must follow reference naming used in year2026 DRLs:

- `Year<year>.Mips<measure>.Denominator`
- `Year<year>.Mips<measure>.Denominator.EMR`
- `Year<year>.Mips<measure>.Exclusion.<Option>.EMR`
- `Year<year>.Mips<measure>.Success.<Option>.EMR[.Org|.Group|.Provider]`
- `Year<year>.Mips<measure>.Gap.<Option>`

Do not generate ticket- or sequence-based names such as:

- `1048701_denominator_001`
- `denominator_rule_1`
- `mips488_r7`

## 9. Marker Naming Standard (Required)

Marker declares must match `Year<year>Mips<measure><Purpose>EMR` and stay semantically tied to fire-once behavior.

Examples:

- `Year2026Mips488DenominatorEMR`
- `Year2026Mips488ExclusionM1187EMR`
- `Year2026Mips488SuccessM1189EMROrg`

Avoid ticket-based marker names such as `T1048701_ExclusionM1187EMR`.

## 10. EMR Semantics Contract (Required)

1. EMR rules must include marker guard and marker insertion in the same rule.
2. EMR evidence names and option ids must reflect CQL `ExtendedMeasureResultV2` names and option ids.
3. When attribution is encounter-based `.all`, include org (`""`), each group id, and provider id when present.
4. Do not mix status API writes and EMR API writes in a way that changes expected output cardinality.

## 11. Fact Modeling Standard (Required)

Generated DRL must mirror fact style in reference files:

1. Use engine/platform domain facts in `when` clauses:
  - `Program`, `Patient`, `ClinicalActivity`, `Diagnosis`, `LaboratoryTestPerformed`/`QdmDatatype` as applicable.
  - `EncounterDenominator` for denominator carry-forward between rules.
2. Include standard header imports used by references:
  - `import com.ablehealth.model.*`
  - `import com.ablehealth.payloads.*`
  - `import com.ablehealth.results.*`
  - `global PatientResults controlSet;`
3. `declare` blocks should be narrow and intentional:
  - fire-once markers (for EMR/status dedup), and
  - small helper state facts (for split sources/attribution), usually with one identifier field.
4. Avoid synthetic wrapper facts that hide source semantics:
  - Do not define monolithic facts such as `M488Context`, `M488Evidence`, `M488EmrOutput`.
  - Prefer direct matching on underlying domain facts and value-set predicates.

## 12. Fact Review Checklist

- Does denominator insert `EncounterDenominator` with measure id?
- Are downstream rules consuming `EncounterDenominator` instead of custom copied context facts?
- Are marker/helper declares specific and minimal (not generic record containers)?
- Do imports and global declarations match reference measure style?
