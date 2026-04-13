library DiabetesScreening version '1.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

codesystem "SNOMED-CT": 'http://snomed.info/sct'
codesystem "ICD-10-CM": 'http://hl7.org/fhir/sid/icd-10-cm'

valueset "Diabetes Mellitus Conditions": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.103.12.1001'
valueset "HbA1c Laboratory Tests": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.198.12.1013'

code "Diabetes type 2": '44054006' from "SNOMED-CT" display 'Diabetes mellitus type 2'
code "HbA1c": '4548-4' from "SNOMED-CT" display 'Hemoglobin A1c/Hemoglobin.total in Blood'

parameter "Measurement Period" Interval<Date>

context Patient

define "Initial Population":
  AgeInYears() >= 18

define "Has Diabetes Diagnosis":
  exists ([Condition: "Diabetes Mellitus Conditions"])

define "Needs HbA1c Test":
  "Has Diabetes Diagnosis"
    and not exists ([Observation: "HbA1c Laboratory Tests"])

define "Denominator":
  "Initial Population"
    and "Has Diabetes Diagnosis"

define "Numerator":
  exists ([Observation: "HbA1c Laboratory Tests"])
