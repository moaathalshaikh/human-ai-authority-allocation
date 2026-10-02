# Annotation Instructions
## LLM Deductive Coding Study — Human Baseline

---

## What is this task?

You will read **113 short evidence claims** extracted from published software engineering research papers about **Continuous Integration (CI)**.

Your job is to assign **one code** from a predefined list to each claim.

This is called **deductive coding** — you are not creating new categories, you are assigning claims to an existing taxonomy.

---

## What you need

You have two files:

1. **Your annotation sheet** (CSV file, your tab only)
   - Column A: Row number
   - Column B: Claim ID (e.g., C924)
   - Column C: The claim text — **read this carefully**
   - Column D: **Your answer goes here** — write the exact code name
   - Column E: Notes — write here if you are unsure or the claim is ambiguous

2. **Taxonomy Reference tab** (CSV file)
   - 6 themes, 31 codes total
   - Always copy the code name exactly as written

---

## Step-by-step

**Step 1:** Open the CSV file and go to **Taxonomy Reference** tab first.
Read through all 6 themes and their codes to get familiar with them.
This takes about 10 minutes and is important.

**Step 2:** Go to your annotation tab (Annotator 1 or Annotator 2).

**Step 3:** For each claim:

- Read the claim in Column C
- Ask yourself: *"What is this claim saying about CI?"*
- Find the code in the Taxonomy Reference that best describes it
- Copy the code name exactly into Column D

**Step 4:** If you are unsure between two codes, write your best guess in Column D and explain your uncertainty in Column E.

**Step 5:** Every claim must have an answer in Column D. Do not skip any.

---

## Important rules

| Rule | Why |
|------|-----|
| **One code per claim** | Each claim gets exactly one code, even if it seems to fit more than one |
| **Copy the code exactly** | Spelling must match the Taxonomy Reference — do not paraphrase |
| **Do not discuss with the other annotator** | Your answers must be independent |
| **Do not search the internet** | Use only the taxonomy and your own judgment |
| **Work at your own pace** | There is no time pressure, but most people finish in 2–3 hours |

---

## How to choose the right code

Ask yourself these questions in order:

1. **What is the main topic of the claim?**
   → Find the matching theme first (e.g., Build Patterns, Quality Assurance...)

2. **What specific effect or relationship does the claim describe?**
   → Find the code within that theme

3. **Does the claim match the code description closely?**
   → If yes, use it. If not, try another theme.

---

## Example

**Claim:** *"CI HELPS TO CATCH PROBLEMS AS EARLY AS POSSIBLE"*

- Main topic: catching problems → relates to quality
- Theme: **QUALITY ASSURANCE**
- Best matching code: **CI IS RELATED TO AN INCREASE QUALITY ASSESSMENT**
- Write in Column D: `CI IS RELATED TO AN INCREASE QUALITY ASSESSMENT`

---

## What happens with your answers?

Your annotations will be compared with:
- The other annotator's answers
- An expert gold-standard annotation

This comparison measures **inter-rater agreement** — how consistently different people assign the same codes. Your individual answers will not be judged as right or wrong.

---

## If you finish

Print to me CSV file here and I will convert it to csv so i will copy and paste inside txt file and i will change the extension to csvm, and send it back without changing any other columns.

Thank you for your time. Your contribution directly supports research on AI-assisted systematic literature reviews.

---

*Questions? Contact the research team before starting.*