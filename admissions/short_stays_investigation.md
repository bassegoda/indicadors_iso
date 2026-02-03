# Short stays in E073 — investigation notes

## Context

`hosp_ward_stays.py` produces the validated cohort for E073/2024: **449 stays**.
Stay duration was analysed for outliers. Long stays (>28 days, 6 cases) were
cross-checked against all movements in the episode and validated as legitimate —
no evidence the patients left E073 during those periods.

Short stays (<24 h) are **33 cases**, all single movements.  They pass all three
admission criteria (bed assigned, year filter, prescription initiated during stay)
so they are not data errors per se.  But for a general ward they are unusual and
worth understanding before using the cohort for any comparative analysis.

## Ward layout — E073

11 distinct `place_ref` values in 2024:

| place_ref | Movements | Avg stay (h) | Max stay (h) | Notes |
|-----------|-----------|--------------|--------------|-------|
| 42111513167 | 59 | 126.6 | 477 | |
| 42111512307 | 55 | 150.7 | 1024 | |
| 42111512946 | 55 | 130.5 | 621 | |
| 42111513187 | 50 | 130.5 | 699 | |
| 42111512369 | 48 | 136.4 | 1462 | |
| 42111512967 | 48 | 145.2 | 488 | |
| 42111513172 | 48 | 163.7 | 1849 | |
| 42111512938 | 43 | 181.4 | 669 | |
| 42111512481 | 42 | 160.9 | 629 | |
| 42111512479 | 29 | 186.5 | 1822 | |
| **42109160000** | **25** | **5.0** | **28** | Holding spot — see below |

The last one (`42109160000`) behaves fundamentally differently: short stays only,
far fewer uses.  Likely a waiting/holding location rather than a real ward bed.
Some of the 33 short stays may be routed through this spot.

Some patients in E073 stay in a stationary bed for extended periods while waiting
— e.g. **pretransplant evaluation** or pending admission decisions.  Conversely,
short stays could be patients admitted to this holding area and quickly redirected.

## What to investigate

1. **Which place_ref do the 33 short stays use?**  If most map to `42109160000`
   the explanation is simple: it is a holding spot, not a ward bed.  Consider
   excluding it from the cohort (or flagging it).

2. **Where do short-stay patients go next?**  Pull all movements for the
   short-stay episodes and check the unit immediately after E073.  If they
   consistently transfer to a specific unit (e.g. another ward or ICU) the short
   stay is a routing step, not a real admission.

3. **Time-of-day pattern?**  Are short stays concentrated at specific hours
   (e.g. late-night admissions discharged at morning rounds)?

4. **Prescription check.**  All 33 passed the Rx gate, but what kind of
   prescriptions?  A single-dose or prophylactic Rx during a 2-hour stay is
   different from ongoing treatment.  (`g_prescriptions` has `start_drug_date`
   and presumably an end/duration field — check schema.)

5. **care_level_type_ref.**  The movement table has this field.  Do short stays
   cluster on a particular care level (e.g. HAH = home hospitalisation, or a
   specific ward sub-type)?

## Suggested approach

Load the 33 short-stay episodes, pull their full movement history from
`g_movements`, and do the checks above in a single exploratory script — same
pattern as the bed-gap and discrepancy investigations done previously.  The
script can live in `admissions/` temporarily and be deleted once conclusions are
reached.

## Key files

- `admissions/hosp_ward_stays.py` — production query (do not modify during investigation)
- `admissions/output/admissions_E073_2024_*.csv` — latest cohort output
- `connection.py` — DB access (`execute_query`)
- `DB_CONTEXT.md` — full schema reference
