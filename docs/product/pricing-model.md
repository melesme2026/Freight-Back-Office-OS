# Pricing Model

## Purpose

This document defines how Freight Back Office OS generates revenue.

It outlines:

- pricing structure
- billing logic
- monetization strategy
- how pricing evolves from V1 to SaaS

---

## Core pricing philosophy

Pricing is based on value delivered, not just access.

The system saves:

- time
- manual labor
- errors
- missed invoices

So pricing should reflect:

- operational efficiency gained
- volume processed
- business impact

---

## Pricing model structure

The system supports a hybrid model:

1. Base subscription (monthly)
2. Usage-based pricing (per load, per driver, etc.)
3. Add-ons (future)

---

## 1. Base subscription

Every customer pays a base fee.

### Example tiers

| Plan   | Monthly Price | Includes                         |
|--------|--------------|----------------------------------|
| Starter | $49–$99     | Basic workflow, limited volume   |
| Growth  | $149–$299   | Higher volume, automation        |
| Pro     | $399+       | Advanced features, priority support |

---

## 2. Usage-based pricing

Charges scale with activity.

### Examples

- per load processed
- per driver onboarded
- per document processed (optional)

### Example pricing

| Metric     | Price     |
|------------|----------|
| Per load   | $3–$10   |
| Per driver | $5–$20   |
| Per invoice| optional |

---

## 3. Billing formula

```text
Total = Base Subscription + Usage Charges

Example scenario

Customer:
	•	Growth Plan ($199/month)
	•	50 loads processed
	•	$5 per load

Base: $199
Usage: 50 × $5 = $250
Total: $449


⸻

4. Why hybrid pricing works

Advantages
	•	predictable base revenue
	•	scalable with customer growth
	•	aligns with value delivered
	•	fair for small and large operators

⸻

5. V1 pricing approach

For V1 (your uncle phase):
	•	pricing may be simulated or simplified
	•	focus is on validating billing logic
	•	not optimizing pricing yet

Possible V1 approach:

Flat monthly fee or zero cost (testing phase)


⸻

6. Future pricing enhancements

Discounts
	•	volume discounts
	•	long-term contracts
	•	referral discounts

Add-ons
	•	premium AI extraction
	•	advanced analytics
	•	priority support
	•	custom integrations

Tier limits

Plans may include:
	•	max loads per month
	•	max drivers
	•	feature access control

⸻

7. Billing alignment with product

Pricing must align with:
	•	actual workflow usage
	•	real business operations
	•	customer perceived value

⸻

8. Risks

Underpricing
	•	system delivers high value but low revenue

Overpricing
	•	small operators cannot adopt

Misaligned pricing
	•	pricing does not match usage patterns

⸻

9. Key principle

Start simple and evolve with real usage data.

Do not over-engineer pricing before:
	•	real customers
	•	real usage patterns
	•	real feedback

⸻

10. Long-term vision

The system becomes:
	•	a recurring revenue SaaS
	•	with predictable MRR
	•	scalable across multiple customers

⸻

Summary

The pricing model:
	•	combines subscription and usage
	•	scales with customer growth
	•	reflects operational value
	•	evolves after real-world validation

