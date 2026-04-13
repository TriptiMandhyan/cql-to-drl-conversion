library HypertensionCheck version '2.0.0'

using FHIR version '4.0.1'

include FHIRHelpers version '4.0.1' called FHIRHelpers

codesystem "LOINC": 'http://loinc.org'
codesystem "SNOMED-CT": 'http://snomed.info/sct'

valueset "Essential Hypertension": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.464.1003.104.12.1011'
valueset "Blood Pressure Measurements": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.526.3.1032'
valueset "Antihypertensive Medications": 'http://cts.nlm.nih.gov/fhir/ValueSet/2.16.840.1.113883.3.526.3.1009'

parameter "Measurement Period" Interval<Date>
parameter "Systolic Threshold" Integer
parameter "Diastolic Threshold" Integer

context Patient

define "Initial Population":
  AgeInYears() >= 18
    and AgeInYears() < 85

define "Has Hypertension":
  exists ([Condition: "Essential Hypertension"])

define "On Antihypertensive Therapy":
  exists ([MedicationRequest: "Antihypertensive Medications"])

define "Denominator":
  "Initial Population"
    and "Has Hypertension"

define "Numerator":
  "Denominator"
    and exists ([Observation: "Blood Pressure Measurements"])

define "Denominator Exclusions":
  not "Has Hypertension"
