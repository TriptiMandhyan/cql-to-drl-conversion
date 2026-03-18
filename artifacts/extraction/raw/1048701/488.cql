library MIPS_488_2026

/*
 * Internal ID: 26.MIPS.Mips488
 * Subject Type: Patient
 * Inverse Measure: No
 *
  */

using ADM

include "2026/MIPS/shared/sharedHospice.cql" called sharedHospice
include "2026/MIPS/shared/sharedPalliativeCare.cql" called sharedPalliativeCare

// MIPS value sets
valueset "MIPS; 488_DIABETES"
valueset "MIPS; 488_ENCOUNTER"
valueset "MIPS; 488_DENOMINATOR_EXCLUSION_M1186"
valueset "MIPS; 488_DENOMINATOR_EXCLUSION_M1187"
valueset "MIPS; 488_DENOMINATOR_EXCLUSION_M1188"
valueset "MIPS; 488_PERFORMANCE_MET_M1189"
valueset "MIPS; 488_PERFORMANCE_NOT_MET_M1190"

// ABLE value sets
valueset "ABLE; ESRD"
valueset "ABLE; CKD_STAGE_5"

// VSAC value sets
valueset "VSAC; ESTIMATED_GLOMERULAR_FILTRATION_RATE"
valueset "VSAC; URINE_ALBUMIN_CREATININE_RATIO"

parameter "Measurement Period" Interval<DateTime>

context Patient

// Populations
define "Denominator":
    ["Clinical Activity": "MIPS; 488_ENCOUNTER"] Encounter
    where   Encounter.start_date during "Measurement Period"
            and Encounter.provider_id.hasMeasureMembership = true
            and AgeInYearsAt(Encounter.start.date) in Interval[18, 85]
    with ["Diagnosis": "MIPS; 488_DIABETES"] Diabetes
    such that Interval [Diabetes.start_date, Diabetes.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
    ,
    from "Denominator Encounter" Encounter
    return
    ExtendedMeasureResultV2(
        Encounter
        , 'Denominator Encounter' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )
    and from ["Diagnosis": "MIPS; 488_DIABETES"] Diabetes
        with "Denominator Encounter" Encounter
        such that Interval[Diabetes.start_date, Diabetes.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
    return
    ExtendedMeasureResultV2(
        Diabetes
        , 'Diabetes Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )

define "Denominator Exclusion Hospice or Palliative Care M1186":
/*  Option ID: M1186 */
    (   exists (["Clinical Activity": "MIPS; 488_DENOMINATOR_EXCLUSION_M1186"] QDC
                where QDC.start_date during "Measurement Period")   ) QDCMet
    or exists (sharedHospice."Has Hospice")
    or exists (sharedPalliativeCare."Has Palliative Care")
    ,
    if exists QDCMet
    then return
    ExtendedMeasureResultV2(
        QDCMet
        , 'Hospice or Palliative Care Quality Code' as name
        , display_date = start_date
        , calculated_record = false
        , population = Exclusion
        , option_id = M1186
    )
    else if exists (sharedHospice."Has Hospice") HospiceEvidence
    then return
    ExtendedMeasureResultV2(
        HospiceEvidence
        , 'Evidence of Hospice' as name
        , display_date = start_date
        , calculated_record = false
        , population = Exclusion
        , option_id = M1186
    )
    else if exists (sharedPalliativeCare."Has Palliative Care") PalliativeEvidence
    then return
    ExtendedMeasureResultV2(
        PalliativeEvidence
        , 'Evidence of Palliative Care' as name
        , display_date = start_date
        , calculated_record = false
        , population = Exclusion
        , option_id = M1186
    )

define "Denominator Exclusion ESRD M1187":
/*  Option ID: M1187 */
    (   (   ["Clinical Activity": "MIPS; 488_DENOMINATOR_EXCLUSION_M1187"]
            union ["Diagnosis": "ABLE; ESRD"]  ) ESRDEvidence
        where ESRDEvidence.start_date during "Measurement Period"  ) M1187Evidence
    ,
    if exists "Denominator Exclusion ESRD M1187" return
    ExtendedMeasureResultV2(
        M1187Evidence
        , 'ESRD Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Exclusion
        , option_id = M1187
    )

define "Denominator Exclusion CKD Stage 5 M1188":
/*  Option ID: M1188 */
    (   (   ["Clinical Activity": "MIPS; 488_DENOMINATOR_EXCLUSION_M1188"]
            union ["Diagnosis": "ABLE; CKD_STAGE_5"]  ) CKDEvidence
        where CKDEvidence.start_date during "Measurement Period"  ) M1188Evidence
    ,
    if exists "Denominator Exclusion CKD Stage 5 M1188" return
    ExtendedMeasureResultV2(
        M1188Evidence
        , 'CKD Stage 5 Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Exclusion
        , option_id = M1188
    )

define "Numerator Performance Met M1189":
/* Option ID: M1189 */
    (   ["Clinical Activity": "MIPS; 488_PERFORMANCE_MET_M1189"] QDC
        where QDC.start_date during "Measurement Period"    ) QCMet
    or  (   exists  (   ["Laboratory Test": "VSAC; ESTIMATED_GLOMERULAR_FILTRATION_RATE"] eGFRTest
                        where   (   eGFRTest.start_date during "Measurement Period"
                                    and eGFRTest.result is not null )   ) eGFRMet
            and exists  (   ["Laboratory Test": "VSAC; URINE_ALBUMIN_CREATININE_RATIO"] uACRTest
                            where   (   uACRTest.start_date during "Measurement Period"
                                        and uACRTest.result is not null )  ) uACRMet
        ) LabsMet
    ,
    if exists QCMet
    return
    ExtendedMeasureResultV2(
        QCMet
        , 'Kidney Health Evaluation Quality Code' as name
        , display_date = start_date
        , calculated_record = false
        , population = Numerator Performance Met
        , option_id = M1189
    )
    else if exists LabsMet
    then return
    ExtendedMeasureResultV2(
        eGFRMet
        , 'eGFR Lab Test' as name
        , display_date = start_date
        , calculated_record = false
        , population = Numerator Performance Met
        , option_id = M1189
    )  
    and return
    ExtendedMeasureResultV2(
        uACRMet
        , 'uACR Lab Test' as name
        , display_date = start_date
        , calculated_record = false
        , population = Numerator Performance Met
        , option_id = M1189
    )

define "Numerator Performance Not Met M1190":
/*  Option ID: M1190 */
    not "Denominator Exclusion Hospice or Palliative Care M1186"
    and not "Denominator Exclusion ESRD M1187"
    and not "Denominator Exclusion CKD Stage 5 M1188"
    and not "Numerator Performance Met M1189"
