library MIPS_050_2026

/*
 * Internal ID: 26.MIPS.Mips050
 * Subject Type: Patient
 * Inverse Measure: NO
 */

using ADM

include "2026/MIPS/shared/sharedHospice.cql" called sharedHospice

// MIPS 050 Value Sets
valueset "MIPS; 050_ENCOUNTER"
valueset "MIPS; 050_PERFORMANCE_MET_0509F"
valueset "MIPS; 050_PERFORMANCE_NOT_MET_0509F_8P"
valueset "MIPS; 050_URINARY_INCONTINENCE"

// Able Value Sets
valueset "ABLE; URINARY_INCONTINENCE_INTERVENTION"
valueset "ABLE; URINARY_INCONTINENCE_MEDICATION_MAP_NDC"

parameter "Measurement Period" Interval<DateTime>

context Patient

// Populations
define "Denominator":
  exists("Denominator Encounter") Encounter
  and exists (["Diagnosis": "MIPS; 050_URINARY_INCONTINENCE"] Incontinence
              such that Interval[Incontinence.start_date, Incontinence.stop_date] overlaps "Measurement Period")
  ,
  if exists "Denominator"
  from ("Denominator Encounter") Encounter
  return
  ExtendedMeasureResultV2(
      Encounter //return 1 record even if multiple exist
      , 'Denominator Encounter' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
  )
  ,
  from ["Diagnosis": "MIPS; 050_URINARY_INCONTINENCE"] Incontinence
      where Interval[Incontinence.start_date, Incontinence.stop_date] overlaps "Measurement Period"
  return
  ExtendedMeasureResultV2(
      Incontinence //return 1 record even if multiple exist
      , 'Urinary Incontinence Diagnosis' as name
      , display_date = start_date
      , calculated_record = false
      , population = Denominator
  )

define "Denominator Exclusion G9694":
/* Option ID: G9694 */
  exists(sharedHospice."Has Hospice") HospiceEvidence
  ,
  if exists "Denominator Exclusion G9694" return
  ExtendedMeasureResultV2(
      HospiceEvidence
      , 'Evidence of Hospice' as name
      , display_date = start_date
      , calculated_record = false
      , population = Exclusion
      , option_id = G9694
  )

define "Numerator Performance Met 0509F":
/* Option ID: 0509F */
  exists(
    (   ["Clinical Activity": "MIPS; 050_PERFORMANCE_MET_0509F"] 0509F
        where   0509F.start_date during "Measurement Period"
                and (   0509F.code_modifiers not in {'8P'}
                        and 0509F.code_modifiers is not null or empty  )   ) PerformanceMet
    union ( ["Clinical Activity": "ABLE; URINARY_INCONTINENCE_INTERVENTION"] Intervention
            where Intervention.start_date during "Measurement Period")
    union ( ["Medication": "ABLE; URINARY_INCONTINENCE_MEDICATION_MAP_NDC"] IncontMed
            where Interval[IncontMed.start_date, IncontMed.stop_date] overlaps "Measurement Period")    
    ) Activity
  ,
  return
  ExtendedMeasureResultV2(
      Activity //return 1 record even if multiple exist
      , 'Urinary Incontinence Treatment' as name
      , display_date = start_date
      , calculated_record = false
      , population = Numerator
      , option_id = 0509F
  )

define "Numerator Performance Not Met 0509F-8P":
/* Option ID: 0509F-8P */
  not "Denominator Exclusion G9694"
  and not "Numerator Performance Met 0509F"

// Definitions
define "Denominator Encounter":
  ["Clinical Activity": "MIPS; 050_ENCOUNTER"] Encounter
  where Encounter.start_date during "Measurement Period"
    and AgeInYearsAt(Encounter.start_date) >= 65
    and "Patient Characteristic Sex" = "Female"
    and Encounter.provider_id.hasMeasureMembership = true
