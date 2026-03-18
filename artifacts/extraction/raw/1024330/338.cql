library MIPS_338_2026

/*
 * Internal Identifier: 26.MIPS.Mips338
 * Subject Type: Patient
 * Inverse: No
 */

using ADM

// MIPS value sets
valueset "MIPS; 338_ENCOUNTER"
valueset "MIPS; 338_HIV_AIDS"
valueset "MIPS; 338_PERFORMANCE_MET_G9243"
valueset "MIPS; 338_PERFORMANCE_NOT_MET_G9242"

// VSAC value sets
valueset "VSAC; HIV_VIRAL_LOAD_TESTSF": '2.16.840.1.113762.1.4.1248.377'

parameter "Measurement Period" Interval<DateTime>

context Patient

// Populations
define "Denominator":
  "Denominator Encounter" Encounter
  ,
  if exists("Denominator")
    then
    return
        ExtendedMeasureResultV2(
            Encounter //return 1 record even if multiple exist
            , 'Denominator Encounter' as name
            , display_date = start_date
            , calculated_record = false
            , population = Denominator
            , option_id = all
        )
    and from ["Diagnosis": "MIPS; 338_HIV_AIDS"] HIV
            with "Denominator" Encounter
            such that HIV.start_date on or before start of "Measurement Period" + 90 days
    return
        ExtendedMeasureResultV2(
            HIV //return 1 record even if multiple exist
            , 'HIV/AIDS Diagnosis' as name
            , display_date = start_date
            , calculated_record = false
            , population = Denominator
            , option_id = all
        )

define "Numerator Performance Met- G9243":
  /* Option ID: G9243 */
  (   (["Clinical Activity": "MIPS; 338_PERFORMANCE_MET_G9243"] P
      where P.start_date during "Measurement Period"  ) G9243
  union "Last Ordered Viral Loads with Appropriate Result" VL
  ) PerformanceMet
  ,
  if exists "Numerator Performance Met- G9243" return
  ExtendedMeasureResultV2(
      PerformanceMet //return 1 record even if multiple exist
      , 'Performance Met G9243' as name
      , display_date = start_date
      , calculated_record = false
      , population = Numerator
      , option_id = G9243
  )

define "Numerator Performance Not Met- G9242":
  /* Option ID: G9242 */
  not "Numerator Performance Met- G9243"

// Definitions
define "Denominator Encounter":
    ["Clinical Activity": "MIPS; 338_ENCOUNTER"] Encounter
    such that   (   Encounter.start_date during Interval[start of "Measurement Period", start of "Measurement Period" + 240 days]
                    and Encounter.provider_id.hasMeasureMembership = true )
    and exists (    ["Diagnosis": "MIPS; 338_HIV_AIDS"] HIV
                    where HIV.start_date on or before start of "Measurement Period" + 90 days   )
    
define "Last Ordered Viral Loads with Appropriate Result":
    (   Last(   (   ["Laboratory Test Performed": "VSAC; HIV_VIRAL_LOAD_TESTS"]
                    union ["Clinical Activity": "VSAC; HIV_VIRAL_LOAD_TESTS"] ) L
                where L.start_date during "Measurement Period"  )   sort by L.start_date ASC    )  LastViralLoad
    where     ( LastViralLoad.result_as_decimal < 200
                or LastViralLoad.result in ["eCQM Direct Reference Codes; BELOW_THRESHOLD_LEVEL_QUALIFIER_VALUE"]
                or LastViralLoad.result in ["eCQM Direct Reference Codes; NOT_DETECTED_QUALIFIER_VALUE"]    )
// First find the last one then check that the result matches