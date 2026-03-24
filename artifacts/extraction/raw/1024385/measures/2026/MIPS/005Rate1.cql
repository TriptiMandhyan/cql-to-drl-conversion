library MIPS_005Rate1_2026
/*
 * Internal ID: 26.MIPS.Mips005Rate1
 * Subject Type: Patient
 * Inverse Measure: NO
 */

using ADM

// ABLE value sets
valueset "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"
valueset "ABLE; ACE_INHIBITOR_OR_ARB_INGREDIENT_NDFRT"
valueset "ABLE; LVEF_LESS_THAN_40" // CPTII codes that mean LVEF < 40%
valueset "ABLE; LVEF_LESS_THAN_OR_EQUAL_TO_40" //HCPCS codes meaning LVEF <= 40%

// MIPS value sets
valueset "MIPS; 005_RATE1_ENCOUNTER"
valueset "MIPS; 005_HEART_FAILURE"
valueset "MIPS; 005_PERFORMANCE_MET_G2092"
valueset "MIPS; 005_DENOMINATOR_EXCEPTION_G2093"
valueset "MIPS; 005_DENOMINATOR_EXCEPTION_G2094"
valueset "MIPS; 005_DENOMINATOR_EXCLUSION_M1151"


// VSAC value sets
valueset "VSAC; ACE_INHIBITOR_OR_ARB_OR_ARNI": 'urn:oid:2.16.840.1.113883.3.526.3.1139' //mapped to NDCs in Able value set
valueset "VSAC; ACE_INHIBITOR_OR_ARB_OR_ARNI_INGREDIENT": 'urn:oid:2.16.840.1.113883.3.526.3.1489'
valueset "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB": 'urn:oid:2.16.840.1.113883.3.526.3.1211'
valueset "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB": 'urn:oid:2.16.840.1.113883.3.526.3.1212'
valueset "VSAC; EJECTION_FRACTION": '2.16.840.1.113883.3.526.3.1134'
valueset "VSAC; HEART_TRANSPLANT": '2.16.840.1.113762.1.4.1178.33'
valueset "VSAC; HEART_TRANSPLANT_COMPLICATIONS": '2.16.840.1.113762.1.4.1178.56'
valueset "VSAC; HYPOTENSION": '2.16.840.1.113883.3.526.3.370'
valueset "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_PLACEMENT": '2.16.840.1.113762.1.4.1178.61'
valueset "VSAC; LEFT_VENTRICULAR_ASSIST_COMPLICATIONS": '2.16.840.1.113762.1.4.1178.58'
valueset "VSAC; MODERATE_OR_SEVERE_LVSD" '2.16.840.1.113883.3.526.3.1090'
valueset "VSAC; MEDICAL_REASON": 'urn:oid:2.16.840.1.113883.3.526.3.1007'
valueset "VSAC; PATIENT_REASON": 'urn:oid:2.16.840.1.113883.3.526.3.1008'
valueset "VSAC; PATIENT_REASON_FOR_ACE_INHIBITOR_OR_ARB_DECLINE": 'urn:oid:2.16.840.1.113883.3.526.3.1140'

//eCQM Direct Reference Codes
valueset "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"
valueset "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_II_RECEPTOR_ANTAGONIST_MECHANISM_OF_ACTION_SUBSTANCE"
valueset "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"
valueset "eCQM Direct Reference Codes; SUBSTANCE_WITH_NEPRILYSIN_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"

parameter "Measurement Period" Interval<DateTime>

context Patient

// Populations

define "Denominator".org:
    exists("Denominator Encounter with Diagnosis" Encounter)
    and exists( "Denominator Encounter" Second
                where Encounter.start_date != Second.start_date )
    and exists( "LVEF Moderately or Severely Depressed" LVEFLess40
                where LVEFLess40.start_date on or before Encounter.start_date )
    ,
    if exists "Denominator".org
    from (    "Denominator Encounter with Diagnosis" DenomEnc
                with "Denominator Encounter" Second
                such that DenomEnc.start_date != Second.start_date  )
    return
    ExtendedMeasureResultV2(
        DenomEnc
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
    and from (["Diagnosis": "MIPS; 005_HEART_FAILURE"] HFDiag
        with "Denominator Encounter with Diagnosis" DenomEnc2
        such that Interval[HFDiag.start_date,HFDiag.stop_date] overlaps Interval[DenomEnc2.start_date, DenomEnc2.stop_date])
    return
    ExtendedMeasureResultV2(
        HFDiag
        , 'Heart Failure Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )
    and from ("LVEF Moderately or Severely Depressed" LVEFEvidence
        with "Denominator Encounter with Diagnosis" DenomEnc3
        such that LVEFEvidence.start_date on or before DenomEnc3.start_date)
    return
    ExtendedMeasureResultV2(
        LVEFEvidence
        , 'LVEF Evidence' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    ) 

define "Denominator".group:
    exists("Denominator Encounter with Diagnosis" Encounter)
    and exists( "Denominator Encounter" Second
                where Encounter.start_date != Second.start_date
                    and Encounter.group_id = Second.group_id )
    and exists( "LVEF Moderately or Severely Depressed" LVEFLess40
                where LVEFLess40.start_date on or before Encounter.start_date )
  ,
  if exists "Denominator".group
  from (    "Denominator Encounter with Diagnosis" DenomEnc
            with "Denominator Encounter" Second
            such that DenomEnc.start_date != Second.start_date
                      and DenomEnc.group_id = Second.group_id  )
    return
    ExtendedMeasureResultV2(
        DenomEnc
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
    and from (["Diagnosis": "MIPS; 005_HEART_FAILURE"] HFDiag
        with "Denominator Encounter with Diagnosis" DenomEnc2
        such that Interval[HFDiag.start_date,HFDiag.stop_date] overlaps Interval[DenomEnc2.start_date, DenomEnc2.stop_date])
    return
    ExtendedMeasureResultV2(
        HFDiag
        , 'Heart Failure Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )
    and from ("LVEF Moderately or Severely Depressed" LVEFEvidence
        with "Denominator Encounter with Diagnosis" DenomEnc3
        such that LVEFEvidence.start_date on or before DenomEnc3.start_date)
    return
    ExtendedMeasureResultV2(
        LVEFEvidence
        , 'LVEF Evidence' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )

define "Denominator".provider:
    exists("Denominator Encounter with Diagnosis" Encounter)
    and exists( "Denominator Encounter" Second
                where Encounter.start_date != Second.start_date
                    and Encounter.provider_id = Second.provider_id )
    and exists( "LVEF Moderately or Severely Depressed" LVEFLess40
                where LVEFLess40.start_date on or before Encounter.start_date )
  ,
  if exists "Denominator".provider
  from (    "Denominator Encounter with Diagnosis" DenomEnc
            with "Denominator Encounter" Second
            such that DenomEnc.start_date != Second.start_date
                      and DenomEnc.provider_id = Second.provider_id  )
    return
    ExtendedMeasureResultV2(
        DenomEnc
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
    and from (["Diagnosis": "MIPS; 005_HEART_FAILURE"] HFDiag
        with "Denominator Encounter with Diagnosis" DenomEnc2
        such that Interval[HFDiag.start_date,HFDiag.stop_date] overlaps Interval[DenomEnc2.start_date, DenomEnc2.stop_date])
    return
    ExtendedMeasureResultV2(
        HFDiag
        , 'Heart Failure Diagnosis' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )
    and from ("LVEF Moderately or Severely Depressed" LVEFEvidence
        with "Denominator Encounter with Diagnosis" DenomEnc3
        such that LVEFEvidence.start_date on or before DenomEnc3.start_date)
    return
    ExtendedMeasureResultV2(
        LVEFEvidence
        , 'LVEF Evidence' as name
        , display_date = start_date
        , calculated_record = false
        , population = Denominator
        , option_id = all
    )

define "Denominator Exclusion History of Heart Transplant or LVAD M1151".org
/* Option ID: M1151 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCLUSION_M1151"] 
        union ["Clinical Activity": "VSAC; HEART_TRANSPLANT"] 
        union ["Clinical Activity": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_PLACEMENT"]
        union ["Diagnosis": "VSAC; HEART_TRANSPLANT_COMPLICATIONS"]
        union ["Diagnosis": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_COMPLICATIONS"]
    ) TransplantorLVAD
    with "Denominator".org Encounter
    such that TransplantorLVAD.start_date before or on Encounter.start_date
    ,
    return
    ExtendedMeasureResultV2(
    TransplantorLVAD
    , 'Heart Transplant or LVAD Evidence' as name
    , display_date = start_date
    , calculated_record = false
    , population = Exclusion
    , option_id = M1151
    )

define "Denominator Exclusion History of Heart Transplant or LVAD M1151".group
/* Option ID: M1151 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCLUSION_M1151"] 
        union ["Clinical Activity": "VSAC; HEART_TRANSPLANT"] 
        union ["Clinical Activity": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_PLACEMENT"]
        union ["Diagnosis": "VSAC; HEART_TRANSPLANT_COMPLICATIONS"]
        union ["Diagnosis": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_COMPLICATIONS"]
    ) TransplantorLVAD
    with "Denominator".group Encounter
    such that TransplantorLVAD.start_date before or on Encounter.start_date
    ,
    return
    ExtendedMeasureResultV2(
    TransplantorLVAD
    , 'Heart Transplant or LVAD Evidence' as name
    , display_date = start_date
    , calculated_record = false
    , population = Exclusion
    , option_id = M1151
    )

define "Denominator Exclusion History of Heart Transplant or LVAD M1151".provider
/* Option ID: M1151 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCLUSION_M1151"] 
        union ["Clinical Activity": "VSAC; HEART_TRANSPLANT"] 
        union ["Clinical Activity": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_PLACEMENT"]
        union ["Diagnosis": "VSAC; HEART_TRANSPLANT_COMPLICATIONS"]
        union ["Diagnosis": "VSAC; LEFT_VENTRICULAR_ASSIST_DEVICE_COMPLICATIONS"]
    ) TransplantorLVAD
    with "Denominator".provider Encounter
    such that TransplantorLVAD.start_date before or on Encounter.start_date
    ,
    return
    ExtendedMeasureResultV2(
    TransplantorLVAD
    , 'Heart Transplant or LVAD Evidence' as name
    , display_date = start_date
    , calculated_record = false
    , population = Exclusion
    , option_id = M1151
    )

define "Numerator Performance Met G2092".org:
/* Option ID: G2092 */
    (   ["Clinical Activity": "MIPS; 005_PERFORMANCE_MET_G2092"] P
            with ("Denominator".org) Encounter
            such that P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
    ) QC
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] Med
                with ("Denominator".org) Encounter
                such that (Interval[Med.start_date, Med.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
                            and Med.negation_reason_code_value is null or empty)
    ) Med
    ,
    if exists "Numerator Performance Met G2092".org
    from ("Numerator Performance Met G2092".org) PerfMet
    return
    ExtendedMeasureResultV2(
    PerfMet
    , 'ACE Inhibitor or ARB or ARNI Prescribed' as name
    , display_date = start_date
    , calculated_record = false
    , population = Performance Met
    , option_id = G2092
    )

define "Numerator Performance Met G2092".group:
/* Option ID: G2092 */
    (   ["Clinical Activity": "MIPS; 005_PERFORMANCE_MET_G2092"] P
            with ("Denominator".group) Encounter
            such that P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
    ) QC
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] Med
                with ("Denominator".group) Encounter
                such that (Interval[Med.start_date, Med.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
                            and Med.negation_reason_code_value is null or empty)
    ) Med
    ,
    if exists "Numerator Performance Met G2092".group
    from ("Numerator Performance Met G2092".group) PerfMet
    return
    ExtendedMeasureResultV2(
    PerfMet
    , 'ACE Inhibitor or ARB or ARNI Prescribed' as name
    , display_date = start_date
    , calculated_record = false
    , population = Performance Met
    , option_id = G2092
    )

define "Numerator Performance Met G2092".provider:
/* Option ID: G2092 */
    (   ["Clinical Activity": "MIPS; 005_PERFORMANCE_MET_G2092"] P
            with ("Denominator".provider) Encounter
            such that P.start_date during Interval[Encounter.start_date, Encounter.stop_date]
    ) QC
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] Med
                with ("Denominator".provider) Encounter
                such that (Interval[Med.start_date, Med.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]
                            and Med.negation_reason_code_value is null or empty)
    ) Med
    ,
    if exists "Numerator Performance Met G2092".provider
    from ("Numerator Performance Met G2092".provider) PerfMet
    return
    ExtendedMeasureResultV2(
    PerfMet
    , 'ACE Inhibitor or ARB or ARNI Prescribed' as name
    , display_date = start_date
    , calculated_record = false
    , population = Performance Met
    , option_id = G2092
    )

define "Denominator Exception G2093".org:
/* Option ID: G2093 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2093"] P
        with "Denominator".org E 
        such that P.start_date during Interval[E.start_date, E.stop_date]
    ) QualityCode
    union   (   (   ["Allergy": "VSAC; ACE_INHIBITOR_OR_ARB_OR_ARNI_INGREDIENT"]
                    union ["Allergy": "ABLE; ACE_INHIBITOR_OR_ARB_INGREDIENT_NDFRT"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_II_RECEPTOR_ANTAGONIST_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_NEPRILYSIN_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]) M
                with "Denominator".org E 
                such that Interval[M.start_date, M.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Allergy
    union   (   (   ["Diagnosis": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Diagnosis": "VSAC; HYPOTENSION"]
                ) D
                with "Denominator".org E 
                such that Interval[D.start_date, D.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Diagnosis
    union   (   (   ["Clinical Activity": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Clinical Activity": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Clinical Activity": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]   
                ) CA
                with "Denominator".org E 
                such that Interval[CA.start_date, CA.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   ClinicalActivity
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
                with "Denominator".org E 
                such that ( NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                            and NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; MEDICAL_REASON"])
            )   Med
    ,
    if exists "Denominator Exception G2093".org
    from ("Denominator Exception G2093".org) Exception
    return
    ExtendedMeasureResultV2(
    Exception
    , 'Medical Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2093
    )

define "Denominator Exception G2093".group:
/* Option ID: G2093 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2093"] P
        with "Denominator".group E 
        such that P.start_date during Interval[E.start_date, E.stop_date]
    ) QualityCode
    union   (   (   ["Allergy": "VSAC; ACE_INHIBITOR_OR_ARB_OR_ARNI_INGREDIENT"]
                    union ["Allergy": "ABLE; ACE_INHIBITOR_OR_ARB_INGREDIENT_NDFRT"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_II_RECEPTOR_ANTAGONIST_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_NEPRILYSIN_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]) M
                with "Denominator".group E 
                such that Interval[M.start_date, M.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Allergy
    union   (   (   ["Diagnosis": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Diagnosis": "VSAC; HYPOTENSION"]
                ) D
                with "Denominator".group E 
                such that Interval[D.start_date, D.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Diagnosis
    union   (   (   ["Clinical Activity": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Clinical Activity": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Clinical Activity": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]   
                ) CA
                with "Denominator".group E 
                such that Interval[CA.start_date, CA.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   ClinicalActivity
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
                with "Denominator".group E 
                such that ( NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                            and NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; MEDICAL_REASON"])
            )   Med
    ,
    if exists "Denominator Exception G2093".group
    from ("Denominator Exception G2093".group) Exception
    return
    ExtendedMeasureResultV2(
    Exception
    , 'Medical Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2093
    )

define "Denominator Exception G2093".provider:
/* Option ID: G2093 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2093"] P
        with "Denominator".provider E 
        such that P.start_date during Interval[E.start_date, E.stop_date]
    ) QualityCode
    union   (   (   ["Allergy": "VSAC; ACE_INHIBITOR_OR_ARB_OR_ARNI_INGREDIENT"]
                    union ["Allergy": "ABLE; ACE_INHIBITOR_OR_ARB_INGREDIENT_NDFRT"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_ANGIOTENSIN_II_RECEPTOR_ANTAGONIST_MECHANISM_OF_ACTION_SUBSTANCE"]
                    union ["Allergy": "eCQM Direct Reference Codes; SUBSTANCE_WITH_NEPRILYSIN_INHIBITOR_MECHANISM_OF_ACTION_SUBSTANCE"]) M
                with "Denominator".provider E 
                such that Interval[M.start_date, M.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Allergy
    union   (   (   ["Diagnosis": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Diagnosis": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Diagnosis": "VSAC; HYPOTENSION"]
                ) D
                with "Denominator".provider E 
                such that Interval[D.start_date, D.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   Diagnosis
    union   (   (   ["Clinical Activity": "eCQM Direct Reference Codes; ACUTE_RENAL_FAILURE_CAUSED_BY_ANGIOTENSIN_CONVERTING_ENZYME_INHIBITOR_DISORDER"]
                    union ["Clinical Activity": "VSAC; ALLERGY_TO_ACE_INHIBITOR_OR_ARB"]
                    union ["Clinical Activity": "VSAC; INTOLERANCE_TO_ACE_INHIBITOR_OR_ARB"]   
                ) CA
                with "Denominator".provider E 
                such that Interval[CA.start_date, CA.stop_date] overlaps Interval[E.start_date, E.stop_date]
            )   ClinicalActivity
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
                with "Denominator".provider E 
                such that ( NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                            and NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; MEDICAL_REASON"])
            )   Med
    ,
    if exists "Denominator Exception G2093".provider
    from ("Denominator Exception G2093".provider) Exception
    return
    ExtendedMeasureResultV2(
    Exception
    , 'Medical Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2093
    )

define "Denominator Exception G2094".org:
/* Option ID: G2094 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2094"] P
            with "Denominator".org E 
            such that P.start_date during Interval[E.start_date, E.stop_date]
        union ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
            with "Denominator".org E 
            such that (NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                      and ( NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON"]
                            or NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON_FOR_ACE_INHIBITOR_OR_ARB_DECLINE"]))
    )
    ,
    if exists "Denominator Exception G2094".org
    from ("Denominator Exception G2094".org) ExceptionPatient
    return
    ExtendedMeasureResultV2(
    ExceptionPatient
    , 'Patient Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2094
    )

define "Denominator Exception G2094".group:
/* Option ID: G2094 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2094"] P
        with "Denominator".group E 
        such that P.start_date during Interval[E.start_date, E.stop_date]   ) QC
    union   (   ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
                with "Denominator".group E 
                such that   (   NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                                and (   NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON"]
                                        or NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON_FOR_ACE_INHIBITOR_OR_ARB_DECLINE"] )   
                            )
            ) Med
    ,
    if exists "Denominator Exception G2094".group
    from ("Denominator Exception G2094".group) ExceptionPatient
    return
    ExtendedMeasureResultV2(
    ExceptionPatient
    , 'Patient Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2094
    )

define "Denominator Exception G2094".provider:
/* Option ID: G2094 */
    (   ["Clinical Activity": "MIPS; 005_DENOMINATOR_EXCEPTION_G2094"] P
            with "Denominator".provider E 
            such that P.start_date during Interval[E.start_date, E.stop_date]
        union ["Medication": "ABLE; ACE_INHIBITOR_OR_ARB_OR_ARNI_MAP_NDC"] NoACEIOrARBOrARNIOrdered
            with "Denominator".provider E 
            such that (NoACEIOrARBOrARNIOrdered.author_date during Interval[E.start_date, E.stop_date]
                      and ( NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON"]
                            or NoACEIOrARBOrARNIOrdered.negation_reason_code_type, NoACEIOrARBOrARNIOrdered.negation_reason_code_value in ["VSAC; PATIENT_REASON_FOR_ACE_INHIBITOR_OR_ARB_DECLINE"]))
    )
    ,
    if exists "Denominator Exception G2094".provider
    from ("Denominator Exception G2094".provider) ExceptionPatient
    return
    ExtendedMeasureResultV2(
    ExceptionPatient
    , 'Patient Reason Exception' as name
    , display_date = start_date
    , calculated_record = false
    , population = Denominator Exception
    , option_id = G2094
    )

define "Numerator Performance Not Met G2096".org:
/* Option ID: G2096 */
    "Denominator".org
    and not "Numerator Performance Met: G2092"
    and not "Denominator Exclusion History of Heart Transplant or LVAD M1151"
    and not "Denominator Exception: G2093"
    and not "Denominator Exception: G2094"

define "Numerator Performance Not Met G2096".group:
/* Option ID: G2096 */
    "Denominator".group
    and not "Numerator Performance Met: G2092"
    and not "Denominator Exclusion History of Heart Transplant or LVAD M1151"
    and not "Denominator Exception: G2093"
    and not "Denominator Exception: G2094"

define "Numerator Performance Not Met G2096".provider:
/* Option ID: G2096 */
    "Denominator".provider
    and not "Numerator Performance Met: G2092"
    and not "Denominator Exclusion History of Heart Transplant or LVAD M1151"
    and not "Denominator Exception: G2093"
    and not "Denominator Exception: G2094"

// Definitions
define "Denominator Encounter":
    ["Clinical Activity": "MIPS; 005_RATE1_ENCOUNTER"] Encounter
    where   Encounter.start_date during "Measurement Period"
            and AgeInYearsAt(Encounter.start_date) >= 18
            and Encounter.provider_id.hasMeasureMembership = true

define "Denominator Encounter with Diagnosis":
    "Denominator Encounter" Encounter
    with ["Diagnosis": "MIPS; 005_HEART_FAILURE"] Diag
    such that Interval[Diag.start_date,Diag.stop_date] overlaps Interval[Encounter.start_date, Encounter.stop_date]

define "LVEF Less or equal 40%"
    ["Clinical Activity": "VSAC; EJECTION_FRACTION"] LVEF
    where LVEF.result <= 40

define "LVEF Moderately or Severely Depressed":
    "LVEF Less or equal 40%"
    union ["Diagnosis": "VSAC; MODERATE_OR_SEVERE_LVSD"]
    union ["Clinical Activity": "VSAC; MODERATE_OR_SEVERE_LVSD"]
    union ["Clinical Activity": "ABLE; LVEF_LESS_THAN_40"]
    union ["Clinical Activity": "ABLE; LVEF_LESS_THAN_OR_EQUAL_TO_40"]


