library MIPS_007Rate1_2026 CoronaryArterDiseaseBetaBlockerTherapyLeftVentricularSystolicDysfunction

/*
 * Internal ID: 26.MIPS.Mips007Rate1
 * Subject Type: Patient
 * Inverse Measure: false
 */

using ADM

// ABLE value sets
valueset "ABLE; LVEF_LESS_THAN_OR_EQUAL_TO_40"  //  CPTII codes that mean LVEF less than or equal to 40%
valueset "ABLE; LVEF_LESS_THAN_40"  //  CPTII codes that mean LVEF less than 40%
valueset "ABLE; MODERATE_OR_SEVERE_LVSD"    //  MEDCIN codes

// MIPS value sets
valueset "MIPS; 007_CARDIAC_SURGERY"
valueset "MIPS; 007_CORONARY_ARTERY_DISEASE"
valueset "MIPS; 007_ENCOUNTER"
valueset "MIPS; 007_PERFORMANCE_MET_G9189_OR_4008F"
valueset "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"
valueset "MIPS; 007_DENOMINATOR_EXCEPTION_G9190"
valueset "MIPS; 007_DENOMINATOR_EXCEPTION_G9191"
valueset "MIPS; 007_PERFORMANCE_NOT_MET_G9188"

// VSAC value sets
valueset "VSAC; ALLERGY_TO_BETA_BLOCKER_THERAPY": '2.16.840.1.113883.3.526.3.1177'
valueset "VSAC; ARRHYTHMIA": '2.16.840.1.113883.3.526.3.366'
valueset "VSAC; ASTHMA": '2.16.840.1.113883.3.526.3.362'
valueset "VSAC; BRADYCARDIA": '2.16.840.1.113883.3.526.3.412'
valueset "VSAC; BETA_BLOCKER_THERAPY": '2.16.840.1.113883.3.526.3.1174'
valueset "VSAC; BETA_BLOCKER_THERAPY_INGREDIENT": '2.16.840.1.113883.3.526.3.1493'
valueset "VSAC; EJECTION_FRACTION": '2.16.840.1.113883.3.526.3.1134'
valueset "VSAC; HYPOTENSION": '2.16.840.1.113883.3.526.3.370'
valueset "VSAC; INTOLERANCE_TO_BETA_BLOCKER_THERAPY": '2.16.840.1.113883.3.526.3.1177'
valueset "VSAC; MODERATE_OR_SEVERE_LVSD": '2.16.840.1.113883.3.526.3.1090'
valueset "VSAC; BETA_BLOCKER_THERAPY_FOR_LVSD": '2.16.840.1.113883.3.526.3.1184'

parameter "Measurement Period" Interval<DateTime>

context Patient

/* Populations */
define "Denominator".org:
    "Denominator Encounter with CAD or Hx Cardiac Surgery and LVEF <40" AttributedEncounter
    with "Denominator Encounter" Second
    such that AttributedEncounter.Encounter.start_date != Second.start_date
,
return
ExtendedMeasureResultV2(
      AttributedEncounter.Encounter
      , 'Denominator Encounter 1' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      Second
      , 'Denominator Encounter 2' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.Cardiac
      , 'CAD/Cardiac Surgery Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.LVEFLess40
      , 'LVEF Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)

define "Denominator".group:
    "Denominator Encounter with CAD or Hx Cardiac Surgery and LVEF <40" AttributedEncounter
    with "Denominator Encounter" Second
    such that AttributedEncounter.Encounter.start_date != Second.start_date
                and AttributedEncounter.Encounter.group_id = Second.group_id
,
return
ExtendedMeasureResultV2(
      AttributedEncounter.Encounter
      , 'Denominator Encounter 1' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      Second
      , 'Denominator Encounter 2' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.Cardiac
      , 'CAD/Cardiac Surgery Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.LVEFLess40
      , 'LVEF Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)

define "Denominator".provider:
    "Denominator Encounter with CAD or Hx Cardiac Surgery and LVEF <40" AttributedEncounter
    with "Denominator Encounter" Second
    such that AttributedEncounter.Encounter.start_date != Second.start_date
                and AttributedEncounter.Encounter.provider_id = Second.provider_id
,
return
ExtendedMeasureResultV2(
      AttributedEncounter.Encounter
      , 'Denominator Encounter 1' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      Second
      , 'Denominator Encounter 2' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.Cardiac
      , 'CAD/Cardiac Surgery Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)
and return
ExtendedMeasureResultV2(
      AttributedEncounter.LVEFLess40
      , 'LVEF Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
      , option_id = all
)

define "Numerator Performance Met G9189".org:
/* Option ID: G9189 */
    (   ["Clinical Activity": "MIPS; 007_PERFORMANCE_MET_G9189_OR_4008F"] P
        with "Denominator".org Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and (   P.code_modifiers not in {'8P','1P','2P','3P'}
                            or P.code_modifiers isEmpty
                            or P.code_modifiers = null  )
    )
    union   (   ["Medication": "VSAC; BETA_BLOCKER_THERAPY_FOR_LVSD"] BetaBlocker
                with "Denominator".org Encounter
                such that Interval[BetaBlocker.start_date, BetaBlocker.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]) Evidence
,
return
ExtendedMeasureResultV2(
      Evidence
      , 'Evidence of Beta Blocker Therapy' as name
      , display_date = start_date
      , calculated_record = false
      , population = Numerator Performance Met
      , option_id = G9189
)

define "Numerator Performance Met G9189".group:
/* Option ID: G9189 */
    (   ["Clinical Activity": "MIPS; 007_PERFORMANCE_MET_G9189_OR_4008F"] P
        with "Denominator".group Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and (   P.code_modifiers not in {'8P','1P','2P','3P'}
                            or P.code_modifiers isEmpty
                            or P.code_modifiers = null  )
    )
    union   (   ["Medication": "VSAC; BETA_BLOCKER_THERAPY_FOR_LVSD"] BetaBlocker
                with "Denominator".group Encounter
                such that Interval[BetaBlocker.start_date, BetaBlocker.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]) EvidenceGroup
,
return
ExtendedMeasureResultV2(
      EvidenceGroup
      , 'Evidence of Beta Blocker Therapy' as name
      , display_date = start_date
      , calculated_record = false
      , population = Numerator Performance Met
      , option_id = G9189
)

define "Numerator Performance Met G9189".provider:
/* Option ID: G9189 */
    (   ["Clinical Activity": "MIPS; 007_PERFORMANCE_MET_G9189_OR_4008F"] P
        with "Denominator".provider Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and (   P.code_modifiers not in {'8P','1P','2P','3P'}
                            or P.code_modifiers isEmpty
                            or P.code_modifiers = null  )
    )
    union   (   ["Medication": "VSAC; BETA_BLOCKER_THERAPY_FOR_LVSD"] BetaBlocker
                with "Denominator".provider Encounter
                such that Interval[BetaBlocker.start_date, BetaBlocker.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]) EvidenceProvider
,
return
ExtendedMeasureResultV2(
      EvidenceProvider
      , 'Evidence of Beta Blocker Therapy' as name
      , display_date = start_date
      , calculated_record = false
      , population = Numerator Performance Met
      , option_id = G9189
)

define "Denominator Exception G9190".org:
/* Option ID: G9190 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"]  P1
        with "Denominator".org Encounter
        such that   P1.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and P1.code_modifiers = '1P' )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9190"] P2
                with "Denominator".org Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] )
    union   (   "Medical Exception" M
                with "Denominator".org Encounter
                such that Interval[M.start_date, M.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]  ) ExceptionOrg
,
return
ExtendedMeasureResultV2(
      ExceptionOrg
      , 'Denominator Exception G9190 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9190
)

define "Denominator Exception G9190".group:
/* Option ID: G9190 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"]  P1
        with "Denominator".group Encounter
        such that   P1.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and P1.code_modifiers = '1P' )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9190"] P2
                with "Denominator".group Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] )
    union   (   "Medical Exception" M
                with "Denominator".group Encounter
                such that Interval[M.start_date, M.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]  ) ExceptionGroup
,
return
ExtendedMeasureResultV2(
      ExceptionGroup
      , 'Denominator Exception G9190 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9190
)

define "Denominator Exception G9190".provider:
/* Option ID: G9190 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"]  P1
        with "Denominator".provider Encounter
        such that   P1.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                    and P1.code_modifiers = '1P' )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9190"] P2
                with "Denominator".provider Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] )
    union   (   "Medical Exception" M
                with "Denominator".provider Encounter
                such that Interval[M.start_date, M.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]  ) ExceptionProvider
,
return
ExtendedMeasureResultV2(
      ExceptionProvider
      , 'Denominator Exception G9190 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9190
)

define "Denominator Exception G9191".org:
/* Option ID: G9191 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"] P
        with "Denominator".org Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                     and P.code_modifiers = '2P'    )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9191"] P2
                with "Denominator".org Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] ) ExceptionOrg
,
return
ExtendedMeasureResultV2(
      ExceptionOrg
      , 'Denominator Exception G9191 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9191
)

define "Denominator Exception G9191".group:
/* Option ID: G9191 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"] P
        with "Denominator".group Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                     and P.code_modifiers = '2P'    )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9191"] P2
                with "Denominator".group Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] ) ExceptionGroup
,
return
ExtendedMeasureResultV2(
      ExceptionGroup
      , 'Denominator Exception G9191 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9191
)


define "Denominator Exception G9191".provider:
/* Option ID: G9191 */
    (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_4008F"] P
        with "Denominator".provider Encounter
        such that   P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
                     and P.code_modifiers = '2P'    )
    union   (   ["Clinical Activity": "MIPS; 007_DENOMINATOR_EXCEPTION_G9191"] P2
                with "Denominator".provider Encounter
                such that P2.start_date during Interval[Encounter.start_date, Encounter.stop_date] ) ExceptionProvider
,
return
ExtendedMeasureResultV2(
      ExceptionProvider
      , 'Denominator Exception G9191 Evidence' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator Exception
      , option_id = G9191
)

define "Numerator Performance Not Met G9188".org:
/* Option ID: G9188 */
    "Denominator".org
    and not "Numerator Performance Met G9189"
    and not "Denominator Exception G9190"
    and not "Denominator Exception G9191"

define "Numerator Performance Not Met G9188".group:
/* Option ID: G9188 */
    "Denominator".group
    and not "Numerator Performance Met G9189"
    and not "Denominator Exception G9190"
    and not "Denominator Exception G9191"

define "Numerator Performance Not Met G9188".provider:
/* Option ID: G9188 */
    "Denominator".provider
    and not "Numerator Performance Met G9189"
    and not "Denominator Exception G9190"
    and not "Denominator Exception G9191"

//Definitions
define "LVEF Less Than Or Equal To 40%"
    ["Clinical Activity": "VSAC; EJECTION_FRACTION"] LVEF
    where LVEF.result <= 40

define "LVEF Moderately or Severely Depressed":
    "LVEF Less Than Or Equal To 40%"
    union ["Diagnosis": "VSAC; MODERATE_OR_SEVERE_LVSD"]
    union ["Clinical Activity": "VSAC; MODERATE_OR_SEVERE_LVSD"]
    union ["Clinical Activity": "ABLE; MODERATE_OR_SEVERE_LVSD"]
    union ["Clinical Activity": "ABLE; LVEF_LESS_THAN_OR_EQUAL_TO_40"]
    union ["Clinical Activity": "ABLE; LVEF_LESS_THAN_40"]

define "Denominator Encounter"
    ["Clinical Activity": "MIPS; 007_ENCOUNTER"] Encounter
    where   Encounter.start_date during Interval[start of "Measurement Period", end of "Measurement Period"] 
            and AgeInYearsAt(Encounter.start_date) >= 18
            and Encounter.provider_id.hasMeasureMembership = true

define "Denominator Encounter with CAD or Hx Cardiac Surgery and LVEF <40":
    "Denominator Encounter" Encounter
    with    (   ["Diagnosis": "MIPS; 007_CORONARY_ARTERY_DISEASE"]
                union  ["Clinical Activity": "MIPS; 007_CARDIAC_SURGERY"] )  Cardiac
    such that Interval[Cardiac.start_date, Cardiac.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
    and     with    "LVEF Moderately or Severely Depressed" LVEFLess40
            such that LVEFLess40.start_date on or before Encounter.stop_date
    return Encounter, Cardiac, LVEFLess40

define "Medical Exception":
    ["Allergy": "VSAC; BETA_BLOCKER_THERAPY_INGREDIENT"]
    union ["Allergy": "VSAC; ALLERGY_TO_BETA_BLOCKER_THERAPY"]
    union ["Allergy": "VSAC; INTOLERANCE_TO_BETA_BLOCKER_THERAPY"]
    union ["Diagnosis": "VSAC; BETA_BLOCKER_THERAPY_INGREDIENT"]
    union ["Diagnosis": "VSAC; ALLERGY_TO_BETA_BLOCKER_THERAPY"]
    union ["Diagnosis": "VSAC; INTOLERANCE_TO_BETA_BLOCKER_THERAPY"]
    union ["Diagnosis": "VSAC; ARRHYTHMIA"]
    union ["Diagnosis": "VSAC; HYPOTENSION"]
    union ["Diagnosis": "VSAC; ASTHMA"]
    union ["Diagnosis": "VSAC; BRADYCARDIA"]
    union ["Clinical Activity": "VSAC; INTOLERANCE_TO_BETA_BLOCKER_THERAPY"]
    union ["Clinical Activity": "VSAC; ALLERGY_TO_BETA_BLOCKER_THERAPY"]
