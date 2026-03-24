docs/architecture/ai-integration.md

# AI Integration

## Purpose

This document explains how AI is integrated into Freight Back Office OS.

It covers:

- where AI is used
- what problems AI helps solve
- how AI components interact with the backend
- what is placeholder vs what will become real later
- how AI should evolve after real freight documents are collected

---

## Why AI matters in this system

Freight back-office work involves large amounts of semi-structured and unstructured data:

- PDF rate confirmations
- scanned bills of lading
- mobile phone photos
- emailed invoices
- screenshots and attachments
- inconsistent document layouts

Without AI or OCR assistance, staff must:

- read every document manually
- locate key fields by eye
- compare values across documents
- detect missing or inconsistent information
- decide whether paperwork is complete

AI helps reduce that effort.

---

## AI responsibilities in the platform

In this system, AI is not meant to replace operations staff completely.

It is meant to:

- accelerate document understanding
- extract structured data
- identify anomalies
- support validation
- reduce repetitive manual review

The final authority remains with human review when confidence is low or rules fail.

---

## AI architecture in the backend

AI functionality currently lives under:

```text
backend/app/services/ai/

Current components include:
	•	ocr_service.py
	•	llm_service.py
	•	extraction_service.py
	•	confidence_service.py
	•	anomaly_detection_service.py
	•	prompt_templates/

These services are intentionally modular so placeholder logic can later be replaced with production implementations.

⸻

AI workflow in the system

Document processing flow

Document created
    ↓
OCR extracts text
    ↓
Classifier identifies document type
    ↓
LLM / extraction logic derives fields
    ↓
Confidence scores are calculated
    ↓
Validation rules evaluate extracted data
    ↓
Human review handles uncertain or failed cases


⸻

Current AI-related services

1. OCR Service

File:

backend/app/services/ai/ocr_service.py

Current role:
	•	extract raw text from stored documents
	•	return placeholder OCR output for now

Future role:
	•	integrate real OCR engine
	•	support PDFs, images, and mixed documents
	•	return page-level metadata
	•	support confidence and layout hints

Potential future engines:
	•	Tesseract
	•	AWS Textract
	•	Google Document AI
	•	Azure Document Intelligence
	•	custom OCR pipeline

⸻

2. Document Classifier

File:

backend/app/services/documents/document_classifier.py

Current role:
	•	classify a document using simple keyword logic
	•	identify likely types such as:
	•	rate confirmation
	•	bill of lading
	•	proof of delivery
	•	invoice
	•	unknown

Future role:
	•	use stronger classification based on:
	•	extracted text
	•	filename patterns
	•	document layout
	•	model predictions
	•	real labeled freight samples

⸻

3. LLM Service

File:

backend/app/services/ai/llm_service.py

Current role:
	•	return placeholder extracted fields based on document type

Future role:
	•	extract structured freight-specific fields
	•	support different prompt templates per document type
	•	provide field-level confidence
	•	normalize outputs into platform schema

Potential fields to extract later:
	•	load number
	•	invoice number
	•	broker name
	•	MC number
	•	pickup date
	•	delivery date
	•	shipper / consignee
	•	total rate
	•	accessorial fees
	•	signature presence
	•	POD details

⸻

4. Extraction Service

File:

backend/app/services/ai/extraction_service.py

Current role:
	•	orchestrate OCR
	•	classify document
	•	call LLM extraction
	•	persist extracted fields
	•	update document metadata

This is the main AI orchestration layer in V1.

Future role:
	•	support retries
	•	support model selection by document type
	•	track extraction versions
	•	support raw OCR retention
	•	store traceability metadata for audits

⸻

5. Confidence Service

File:

backend/app/services/ai/confidence_service.py

Current role:
	•	average field confidence scores

Future role:
	•	support weighted confidence
	•	confidence thresholds by field type
	•	document-level readiness scoring
	•	calibration against real outcomes

⸻

6. Anomaly Detection Service

File:

backend/app/services/ai/anomaly_detection_service.py

Current role:
	•	inspect extracted fields for obvious anomalies
	•	identify low-confidence or missing field patterns

Future role:
	•	compare documents against expected operational patterns
	•	detect suspicious or inconsistent values
	•	surface business risks before billing or submission

Examples:
	•	invoice amount does not match rate confirmation
	•	broker name differs from load metadata
	•	document appears blank or incomplete
	•	signature missing on delivery document
	•	extracted date is outside expected shipment window

⸻

Prompt templates

Folder:

backend/app/services/ai/prompt_templates/

Planned templates:
	•	ratecon_extraction.txt
	•	bol_extraction.txt
	•	invoice_extraction.txt
	•	validation_assist.txt

Purpose:
	•	isolate prompt logic from Python code
	•	make prompt tuning easier
	•	support different extraction instructions by document type

This also makes later experimentation easier without rewriting service logic.

⸻

AI + validation relationship

AI is not the final decision-maker.

The validation layer is responsible for business correctness.

Relationship

AI extracts candidate data
    ↓
Validation rules check business correctness
    ↓
Human review resolves uncertainty or conflicts

Examples:
	•	AI extracts invoice amount
	•	validation checks whether it matches expected amount
	•	if mismatch exists, validation issue is created
	•	human resolves the issue

This is the right pattern for freight operations because business correctness matters more than raw extraction confidence.

⸻

Human-in-the-loop model

This system intentionally follows a human-in-the-loop design.

AI should:
	•	reduce manual work
	•	accelerate review
	•	provide structured suggestions

Humans should:
	•	approve uncertain cases
	•	correct extracted fields
	•	resolve validation issues
	•	make business decisions

This keeps the system practical and trustworthy during early rollout.

⸻

What is placeholder today

Current AI implementation is intentionally lightweight.

Placeholder pieces in V1 foundation
	•	OCR returns placeholder text
	•	LLM extraction uses basic hardcoded logic
	•	anomaly detection is heuristic-based
	•	confidence is simple average logic
	•	no real model hosting yet
	•	no document-layout intelligence yet

That is expected at this stage.

The current goal is architecture-first readiness, not final model quality.

⸻

What should become real after uncle document testing

Once real freight paperwork is available, AI work should focus on:

1. Real field maps

Identify the actual fields required from:
	•	rate confirmations
	•	BOLs
	•	invoices
	•	PODs

2. Real extraction prompts

Build freight-specific prompts using actual samples.

3. Real OCR evaluation

Measure OCR quality on:
	•	scanned PDFs
	•	photos from drivers
	•	low-quality uploads
	•	rotated / skewed documents

4. Confidence thresholds

Decide when:
	•	auto-pass is acceptable
	•	review is required
	•	extraction should fail fast

5. Exception patterns

Document recurring anomaly patterns and convert them into rules.

⸻

AI design principles for this project

1. AI should be modular

No business-critical logic should be tightly coupled to one vendor or one model.

2. AI should be traceable

The system should record:
	•	source model
	•	source engine
	•	confidence
	•	extracted values
	•	human corrections

3. AI should support auditability

If a field is extracted incorrectly, the system should make that diagnosable.

4. AI should degrade safely

If AI is uncertain, the system should route to review rather than silently fail.

5. AI should follow business rules

Extraction quality is useful, but business validation is mandatory.

⸻

Risks

Risk 1: False confidence

A model appears accurate in testing but fails on real freight documents.

Mitigation:
	•	validate against real documents early
	•	require review for low-confidence outputs

Risk 2: Overfitting to sample docs

Logic works only for a few sample layouts.

Mitigation:
	•	collect diverse document samples
	•	separate extraction strategy from validation logic

Risk 3: Too much AI too early

The system becomes dependent on AI before workflows are stable.

Mitigation:
	•	keep AI assistive in V1
	•	prioritize operational correctness first

⸻

Future AI enhancements

Likely future improvements include:
	•	stronger OCR engine
	•	real LLM extraction prompts
	•	document layout understanding
	•	signature detection from images
	•	duplicate-document detection
	•	auto-suggested field corrections
	•	broker and carrier normalization
	•	extraction quality analytics
	•	model performance dashboards
	•	feedback loops from human corrections

⸻

Recommended phased AI roadmap

Phase A — Placeholder foundation

Already in progress.

Phase B — Real document validation

Use real uncle paperwork to tune extraction targets.

Phase C — Production OCR and extraction

Replace placeholders with real engines.

Phase D — Review assist and anomaly intelligence

Make AI more useful to operators, not just extractive.

Phase E — Advanced automation

Only after real reliability is proven.

⸻

Summary

AI in Freight Back Office OS is an assistive intelligence layer, not a black-box replacement for operations.

Its purpose is to:
	•	understand documents faster
	•	extract key data
	•	highlight anomalies
	•	reduce repetitive review work

The right path is:
	•	structure first
	•	real documents next
	•	production AI after that

