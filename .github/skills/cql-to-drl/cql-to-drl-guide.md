# CQL to DRL Conversion Guide

This guide captures practical conversion patterns for year-over-year MIPS measure updates, with emphasis on EMRv2, attribution loops, and fire-once dedup guards.

## 1. Denominator With option_id = all and Multiple Extended Results

When CQL denominator includes multiple ExtendedMeasureResultV2 returns under option_id = all, DRL must emit denominator EMR for each named evidence item.

Important: `option_id = all` is a fan-out instruction, not a literal option id.

1. Do not write `all` as the option id argument in `controlSet.addPatientEMR(...)`.
2. Expand to one EMR row per concrete measure option code that applies to the measure, for example denominator option codes and gap/success option codes used by the measure.
3. For each evidence name returned by CQL, emit rows for each concrete option code in scope.
4. Preserve the exact option-code text, including punctuation (for example `0509F-8P`).

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
5. If source CQL uses `option_id = all`, emit EMR rows for all concrete option codes; never emit a row whose option id is the literal string `all`.

Fan-out example:

```drools
// CQL option_id = all means emit all concrete option ids, not "all"
controlSet.addPatientEMR($program, $patient, $measure, "", "Denominator Encounter", "G9694", PopulationEnum.denominator, $encounter, ...);
controlSet.addPatientEMR($program, $patient, $measure, "", "Denominator Encounter", "0509F", PopulationEnum.denominator, $encounter, ...);
controlSet.addPatientEMR($program, $patient, $measure, "", "Denominator Encounter", "0509F-8P", PopulationEnum.denominator, $encounter, ...);
```

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

Required shape for encounter-based EMR attribution:

```drools
controlSet.addPatientEMR($program, $patient, $measure, "", ...);

if ($encounter.isPresent($encounter.groupExternalIds)) {
  for (String groupExternalId : $encounter.getGroupExternalIds()) {
    controlSet.addPatientEMR($program, $patient, $measure, groupExternalId, ...);
  }
}

if ($encounter.isPresent($encounter.providerExternalId)) {
  controlSet.addPatientEMR($program, $patient, $measure, $encounter.providerExternalId, ...);
}
```

Do not collapse this to org-only EMR output when the reference DRL emits group/provider copies. Missing the loops changes reporting behavior, not just formatting.

Required shape for status propagation when the reference DRL splits org from group/provider:

```drools
rule 'YearYYYY.MipsNNN.Success.<Option>.Org'
when
  ...
then
  controlSet.addPatientMeasureStatus($program, $patient, $measure, MeasureStatusValue.SUCCESS, "<Option>");
end

rule 'YearYYYY.MipsNNN.Success.<Option>.GroupAndProvider'
when
  ...
then
  if ($encounter.isPresent($encounter.groupExternalIds)) {
    for (String groupExternalId : $encounter.getGroupExternalIds()) {
      controlSet.addGroupPatientMeasureStatus($program, $patient, groupExternalId, $measure, MeasureStatusValue.SUCCESS, "<Option>");
    }
  }
  if ($encounter.isPresent($encounter.providerExternalId)) {
    controlSet.addProviderPatientMeasureStatus($program, $patient, $encounter.providerExternalId, $measure, MeasureStatusValue.SUCCESS, "<Option>");
  }
end
```

If a production/reference DRL already uses split org and group/provider rules, preserve that structure unless the mapping notes explain why a different shape is equivalent.

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
6. Encounter-based denominator EMR writes org first, then group/provider copies when those identifiers are present.
7. If the source comment says `return 1 record even if multiple exist`, the accumulate function matches the intended evidence-selection direction from the reference DRL.
8. For `option_id = all`, denominator EMR emits one row per concrete option code and emits no literal `all` option id row.

Minimum denominator EMR template for encounter-centric measures:

```drools
rule 'YearYYYY.MipsNNN.Denominator.EMR'
salience -10
when
  EncounterDenominator($program: program, $encounter: clinicalActivity, $measure: measure, measure == 'YearYYYY.MipsNNN')
  $patient: Patient()
  $evidence: QdmDatatype() from accumulate (
    ...,
    earliestQdmDatatype($result)
  )
  and not (exists YearYYYYMipsNNNDenominatorEMR())
then
  insert(new YearYYYYMipsNNNDenominatorEMR());
  controlSet.addPatientEMR($program, $patient, $measure, "", ...);
  if ($encounter.isPresent($encounter.groupExternalIds)) {
    for (String groupExternalId : $encounter.getGroupExternalIds()) {
      controlSet.addPatientEMR($program, $patient, $measure, groupExternalId, ...);
    }
  }
  if ($encounter.isPresent($encounter.providerExternalId)) {
    controlSet.addPatientEMR($program, $patient, $measure, $encounter.providerExternalId, ...);
  }
end
```

## 7. Quick Review Questions

- Does CQL comment include `//return 1 record even if multiple exist`?
- If yes, where is the marker fact and guard?
- Are denominator evidence records present in EMR output (not only numerator)?
- Are all renamed value sets aligned with the CQL source block?
- Are group/provider loops using `groupExternalIds` and provider presence checks?
- Does the DRL preserve the same earliest vs latest evidence-selection direction used by the production reference?
- Did any CQL null-or-empty condition get rewritten into a stricter DRL predicate?
- If a reference rule is split into `.Org` and `.GroupAndProvider`, did the generated DRL preserve that separation or justify the deviation?
- Are shared-library queries or facts referenced exactly as provided by the shared DRL contract, with unresolved dependencies called out instead of being invented locally?
- If CQL uses `option_id = all`, did the DRL fan out into concrete option-code rows instead of emitting `all` as an option id?

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
5. Preserve the reference DRL's evidence-selection direction. If production uses `earliestQdmDatatype` or `earliestClinicalActivity`, do not silently replace it with latest accumulation.
6. Apply `salience -10` consistently to EMR rules when reference DRLs use delayed EMR emission.
7. Treat `option_id = all` as expansion semantics: emit all applicable concrete option-code rows and never emit a literal `all` option id in EMR output.

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

## 13. Evidence Selection Direction

Choose accumulate functions from clinical semantics and production parity, not convenience.

1. If the CQL or embedded comments say `return 1 record even if multiple exist`, inspect the reference DRL to determine whether the selected record should be earliest or latest.
2. Denominator evidence and first qualifying treatment evidence often use earliest selection because the output is serving as proof that the condition was met, not the most recent occurrence.
3. Do not switch `earliest` to `latest` unless the CQL meaning or reference implementation clearly requires the most recent evidence.
4. Record the chosen direction in mapping notes when it is not obvious from the clause text.

Regression to avoid: replacing `earliestQdmDatatype($result)` with `latestQdmDatatype($result)` in a rule that production uses for audit-style evidence output.

## 14. Null And Empty Predicate Preservation

Preserve logical equivalence when translating CQL predicates into DRL constraints.

1. A CQL condition that allows `null`, `empty`, or `not in {'8P'}` must not become a stricter DRL condition that requires non-null and non-empty values.
2. Translate the logic shape first, then the syntax. `A or B or C` in the source must stay an OR-equivalent condition in DRL.
3. If the target DRL syntax is awkward, keep the predicate in a query or helper condition rather than changing its meaning.
4. When in doubt, compare the final DRL predicate against the production/reference DRL line by line.

Regression to avoid:

```drools
(codeModifiers == null || codeModifiers.isEmpty || withCodeModifiersNotIn('8P'))
```

must not be rewritten as:

```drools
codeModifiers != null,
!codeModifiers.isEmpty(),
withCodeModifiersNotIn("8P")
```

## 15. Shared Dependency Contract

Many MIPS measures rely on shared hospice, frailty, palliative-care, or similar queries/facts defined outside the measure-specific DRL.

1. Reuse shared queries/facts only when the contract already exists in the target DRL ecosystem or reference files.
2. Preserve the shared query/fact name exactly. Do not invent local substitutes with guessed semantics.
3. If the measure depends on a shared query or declared fact that is not present in the available references, document it as `TODO: needs domain confirmation` in mapping notes and plan notes.
4. Do not hide unresolved shared dependencies by generating a placeholder rule that always passes.

For shared dependencies, the converter must answer two questions explicitly:

- Which shared query/fact is being referenced?
- Where is that contract defined or why is it still unresolved?

## 16. Naming Preservation Review

Preserve stable naming behavior from production/reference DRLs when it carries business meaning.

1. Keep option ids intact in output payloads, including punctuation such as `0509F-8P`.
2. Preserve clinically meaningful rule suffixes when the reference DRL uses them consistently, for example `Exclusion.hospice` rather than collapsing everything to the option id.
3. Do not normalize names solely to satisfy a generator preference if the reference DRL and downstream systems expect the original shape.
4. If a validator or naming rule forces a deviation, record the deviation and rationale in mapping notes.

## 17. Option All Expansion Rule

`option_id = all` in EMRv2 means all applicable concrete option ids for that measure and population.

1. Build the concrete option-code set from the approved extraction and reference DRL behavior.
2. Emit one `addPatientEMR` call per evidence name per concrete option code.
3. Apply the same fan-out for org, each group id, and provider id when attribution loops are required.
4. Ensure option ids used in EMR fan-out are consistent with measure status options used in success, exclusion, and gap rules.
5. Never emit `all` as option id in EMR output rows.

Validation cue: for each CQL clause with `option_id = all`, verify there is at least one EMR row per concrete option code and zero EMR rows with option id `all`.
