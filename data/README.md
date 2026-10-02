# Data

## Source and licence

The 113 claims, the 31-code taxonomy with its six themes, the code
definitions, and the reference labels are taken from the artefact of a
published systematic literature review:

> Soares, E., Sizilio, G., Santos, J., da Costa, D. A., & Kulesza, U. (2022).
> The effects of continuous integration on software development: a systematic
> literature review. *Empirical Software Engineering*, 27, 78.
> https://doi.org/10.1007/s10664-021-10114-1

> Soares, E., Sizilio, G., Santos, J., Alencar, D., & Kulesza, U. (2021).
> SLR Artifacts - CONTINUOUS INTEGRATION QUALITY IMPACTS (Version v.1.0.2)
> [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.4545623

That dataset is licensed under Creative Commons Attribution 4.0
International (CC BY 4.0). The material derived from it is redistributed
here under the same licence, with attribution to the authors above. The
claim texts and code labels are reproduced verbatim, including their
capitalisation and wording irregularities; no label was edited. The corpus
is the 113 single-labelled claims among the 125 coded claims of the source
review.

## Contents

| Folder | Contents |
|---|---|
| `reference/` | `ci_claims_reference.json`: the 113 claims with study metadata, reference code and reference theme. `codebook.csv`: the 31 codes grouped under the six themes. |
| `instruments/` | Everything given to the annotators: the two sets of written instructions, the scaffolded sheet (original workbook and blank template), the three blank unscaffolded sheets (claim order randomised independently for each annotator), the codebook with definitions given to the unscaffolded group, and the two escalation sheets exactly as sent. |
| `human/blind/` | The five blind coding sheets as returned: `scaffolded_H1`, `scaffolded_H2`, `unscaffolded_A1` to `unscaffolded_A3`. |
| `human/escalation/` | The two escalation sheets as returned by H1 and H2. |
| `model/unscaffolded/` | 150 JSON files: three models x five context levels x ten runs, 113 decisions each (16,950 decisions). Each record holds the predicted code before normalisation, the reported confidence, and the full raw response. File names keep the run timestamp. |
| `model/scaffolded/` | Three CSV files, one per model: L1, ten runs, 113 decisions each (3,390 decisions), with the predicted code string before normalisation and the reported confidence. Full raw responses were not retained for this condition. |

Annotators are identified only by the identifiers used in the paper:
H1 and H2 (scaffolded group) and A1 to A3 (unscaffolded group).

## Corrections applied to the returned sheets

The returned sheets are released as returned, with four exceptions, none of
which changes a code, a decision, or any text written by an annotator:

1. **Elapsed-time column removed** from both returned escalation sheets.
   Elapsed time was recorded but not analysed in the paper.
2. **One pre-filled value restored** in the returned escalation sheet of H2:
   the model confidence for claim C959 reads 0.75 in the returned file and
   0.72 in the sheet as sent, which matches the model's output. The value as
   sent is used. Both sheets as sent are in `instruments/`.
3. **Two claim texts restored** in the returned escalation sheet of H1 (C905
   and C930), where saving the file had corrupted a typographic apostrophe;
   the text is taken from the sheet as sent.
4. **Delimiter normalised** in `human/blind/unscaffolded_A3.csv`, which was
   returned with semicolons; it now uses commas like the other sheets. Every
   cell value is unchanged.

Code strings in the human sheets are kept exactly as written, including one
malformed string. The scoring conventions are applied at analysis time, in
`scripts/06_reproduce_paper.py`, not to the files.
