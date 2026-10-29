# BO-04 fraud detection model card

## Intended use
Pre-completion risk assessment for the demonstration checkout. The assessment
routes an order to allow or review; it is not proof that a payment method was
stolen, and it does not replace the audited human disposition.

## Data
- Deterministic synthetic generator: `services/api/ml/fraud/generate.py`
- Snapshot: `fraud-synthetic-2026-10-27-v1`, 3,000 transactions, ~17% positive
- Split: stratified 60% train / 20% validation / 20% sealed holdout
- Signals: amount versus customer norm, new shipping address, payment-token
  reuse, 24-hour order velocity, prior failed attempts, overnight order hour,
  high absolute amount, first order, account age, item count, weekend, and
  time-of-day encodings
- Not used: real card data, device fingerprints, card-network or issuer
  signals, chargeback labels, or customer PII

## Models and selection
A scaled logistic-regression baseline and histogram gradient boosting are
trained on the identical feature vector. The threshold is chosen on validation
to maximize recall subject to a false-positive rate at or below 0.09 (a safety
margin under the 0.10 target) and clamped to at most 0.70 per DEC-010. The
model with the higher validation recall is selected; PR-AUC breaks ties.

## Sealed-holdout results (selected logistic model)
| Metric | Value |
|---|---|
| Threshold | 0.6985 |
| Recall | 0.833 |
| False-positive rate | 0.078 |
| Precision | 0.685 |
| F1 | 0.752 |
| PR-AUC | 0.854 |
| ROC-AUC | 0.954 |

Gradient boosting: recall 0.824 at 0.088 FPR on the holdout, with lower
validation recall. Both models and confusion matrices are recorded in
`services/api/artifacts/fraud.evaluation.json`.

## Serving policy
- Forced `risk-high`/`risk-fail` sandbox tokens keep deterministic behavior.
- Ordinary tokens are scored by the model; score >= threshold or DEC-010's
  0.70 floor routes to review.
- Missing artifact, inference error, or evidence-write failure returns
  `assessment_failed`, which routes to review. Completion cannot bypass an
  assessment.
- Each assessment stores its model version and reasons; review decisions are
  audited in `risk_review_decisions`.

## Limitations
- Synthetic labels prove pipeline, threshold, and policy behavior only.
- No real fraud process, device fingerprint, or card-network signal is used.
- The model has not been calibrated or tested on production traffic.
- Real deployment requires labeled provider data, re-evaluation, monitoring,
  drift checks, and a reviewed threshold.

## Reproduction
```bash
uv run --project services/api python services/api/ml/fraud/generate.py
uv run --project services/api python services/api/ml/fraud/train.py
```
