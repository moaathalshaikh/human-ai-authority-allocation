#!/usr/bin/env python3
"""
Who Decides, and on What Evidence? -- replication package
=========================================================
Step 6 of 6. Recompute the quantities reported in the paper from the
released data, write them to results/tables/, and check each against
the value printed in the paper.

Usage:
    python scripts/06_reproduce_paper.py

Requires: pandas, numpy, scikit-learn (see requirements.txt).
No API access is needed; this step reads only files in data/.

Conventions used throughout, as described in Section 3.5:
  * Model code strings are normalised to the nearest canonical label
    (difflib, cutoff 0.6) before scoring; literal figures are also
    available via --literal.
  * Human code strings are compared after upper-casing, collapsing
    whitespace, and treating a stray double quote as a space.
  * Differences between accuracies are computed from unrounded values.
"""

import argparse
import csv
import difflib
import glob
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal

import numpy as np
from sklearn.metrics import cohen_kappa_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "results", "tables")
MODELS = ["claude-haiku-4-5", "deepseek-chat", "gpt-4o-mini"]
LEVELS = ["L1", "L2", "L3", "L4", "L5"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def norm(s):
    return re.sub(r"\s+", " ", (s or "").replace('"', " ").strip().upper())


def load_reference():
    ref = json.load(open(os.path.join(DATA, "reference", "ci_claims_reference.json"),
                         encoding="utf-8"))
    gold = {d["paper_id"]: norm(d["labels"]["code"]) for d in ref}
    theme = {d["paper_id"]: d["labels"]["theme"].strip().upper() for d in ref}
    return ref, gold, theme


def read_sheet(path):
    """Annotation sheet -> {claim_id: (code, note)}; header and theme rows skipped."""
    text = open(path, encoding="utf-8-sig").read()
    out = {}
    for r in csv.reader(text.splitlines()):
        if len(r) > 3 and re.fullmatch(r"C\d+", r[1].strip()):
            out[r[1].strip()] = (norm(r[3]), r[4].strip() if len(r) > 4 else "")
    return out


def load_unscaffolded(model, level):
    rows = []
    for f in sorted(glob.glob(os.path.join(DATA, "model", "unscaffolded", model, level, "*.json"))):
        run = int(re.search(r"_run(\d+)_", os.path.basename(f)).group(1))
        for r in json.load(open(f, encoding="utf-8")):
            rows.append({"cid": r["paper_id"], "run": run,
                         "code": norm(r["prediction"].get("code")),
                         "conf": r["prediction"].get("confidence"),
                         "parse": r["meta"].get("parse_success")})
    return rows


def load_scaffolded(model):
    p = os.path.join(DATA, "model", "scaffolded", f"{model}_L1.csv")
    return [{"cid": r["claim_id"], "run": int(r["run"]), "code": norm(r["predicted_code"]),
             "conf": float(r["confidence"])} for r in csv.DictReader(open(p, encoding="utf-8-sig"))]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def fleiss_kappa(table):
    table = np.asarray(table, dtype=float)
    n = table.sum(1)[0]
    p_j = table.sum(0) / table.sum()
    P_i = ((table ** 2).sum(1) - n) / (n * (n - 1))
    return (P_i.mean() - (p_j ** 2).sum()) / (1 - (p_j ** 2).sum())


def band(c):
    d = Decimal(str(c or 0))
    for i, lo in enumerate(["0.0", "0.2", "0.4", "0.6", "0.8"]):
        if i == 4 or d < Decimal(lo) + Decimal("0.2"):
            return i


def fmt(x, nd):
    return f"{x:.{nd}f}"


class Checker:
    def __init__(self):
        self.rows = []

    def check(self, where, what, paper, computed):
        ok = str(paper) == str(computed)
        self.rows.append((where, what, str(paper), str(computed), "PASS" if ok else "FAIL"))

    def report(self):
        path = os.path.join(OUT, "verification_report.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["paper_location", "quantity", "reported", "recomputed", "status"])
            w.writerows(self.rows)
        failed = [r for r in self.rows if r[4] == "FAIL"]
        print(f"\n{len(self.rows)} checks, {len(self.rows) - len(failed)} PASS, {len(failed)} FAIL"
              f"  ->  {os.path.relpath(path, ROOT)}")
        for r in failed:
            print("  FAIL", r)
        return not failed


def write_table(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--literal", action="store_true",
                    help="score model strings literally instead of normalising them")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    ck = Checker()

    ref, gold, theme = load_reference()
    taxonomy = sorted(set(gold.values()))
    code_theme = {gold[c]: theme[c] for c in gold}
    canon = (lambda s: s) if args.literal else \
        (lambda s: s if s in taxonomy else (difflib.get_close_matches(s, taxonomy, n=1, cutoff=0.6) or [s])[0])
    claims = sorted(gold)

    # ---------------- corpus (Section 3.1) ----------------
    per_theme_claims = Counter(theme.values())
    per_theme_codes = defaultdict(set)
    for c in claims:
        per_theme_codes[theme[c]].add(gold[c])
    codes_per_theme = {t: len(v) for t, v in per_theme_codes.items()}
    claims_per_code = Counter(gold.values())
    ck.check("3.1", "claims", 113, len(claims))
    ck.check("3.1", "codes", 31, len(taxonomy))
    ck.check("3.1", "themes", 6, len(per_theme_claims))
    ck.check("3.1", "studies", 36, len({d["input"]["study_title"] for d in ref}))
    ck.check("3.1", "claims per theme (min-max)", "5-29",
             f"{min(per_theme_claims.values())}-{max(per_theme_claims.values())}")
    ck.check("3.1", "codes per theme (min-max)", "2-10",
             f"{min(codes_per_theme.values())}-{max(codes_per_theme.values())}")
    ck.check("3.1", "codes carrying a single claim", 11, sum(1 for v in claims_per_code.values() if v == 1))
    ck.check("3.1", "claims with no recorded variables", 34,
             sum(1 for d in ref if not str(d["input"].get("variables") or "").strip()))
    ck.check("3.1", "labels beginning 'CI IS ASSOCIATED WITH'", 22,
             sum(1 for t in taxonomy if t.startswith("CI IS ASSOCIATED WITH ")))
    ck.check("3.1", "labels beginning 'CI IS RELATED TO'", 6,
             sum(1 for t in taxonomy if t.startswith("CI IS RELATED TO ")))
    defs = {norm(r["Code"]): (r.get("Definition") or "").strip()
            for r in csv.DictReader(open(os.path.join(DATA, "instruments", "codebook_with_definitions.csv"),
                                         encoding="utf-8-sig"))}
    ck.check("3.1", "codes without a written definition", 3, sum(1 for v in defs.values() if not v))
    choice = [codes_per_theme[theme[c]] for c in claims]
    ck.check("3.2", "median scaffolded choice set", 8, int(statistics.median(choice)))
    ck.check("3.2", "% claims under a theme of <=4 codes", "48.7",
             fmt(100 * sum(1 for x in choice if x <= 4) / len(choice), 1))

    # ---------------- human blind coding ----------------
    hum = {k: read_sheet(os.path.join(DATA, "human", "blind", f"{p}_{k}.csv"))
           for k, p in [("H1", "scaffolded"), ("H2", "scaffolded"),
                        ("A1", "unscaffolded"), ("A2", "unscaffolded"), ("A3", "unscaffolded")]}
    code = {k: {c: v[0] for c, v in s.items()} for k, s in hum.items()}
    hdr = {}
    for k, path in [("H1", "scaffolded_H1"), ("H2", "scaffolded_H2")]:
        cur = None
        for r in csv.reader(open(os.path.join(DATA, "human", "blind", path + ".csv"),
                                 encoding="utf-8-sig").read().splitlines()):
            if r and r[0].startswith("\u25b8"):
                cur = r[0].replace("\u25b8", "").replace("Theme:", "").strip().upper()
            elif len(r) > 3 and re.fullmatch(r"C\d+", r[1].strip()):
                hdr.setdefault(k, {})[r[1].strip()] = cur
    ck.check("3.2", "theme header matches reference theme (H1 sheet)", "113 of 113",
             f"{sum(hdr['H1'][c] == theme[c] for c in claims)} of 113")

    def acc(k):
        v = {c: x for c, x in code[k].items() if x not in ("?", "")}
        return sum(x == gold[c] for c, x in v.items()) / len(v), len(v)

    accs = {k: acc(k) for k in code}
    for k, exp in [("H1", "0.912"), ("H2", "0.938"), ("A1", "0.811"), ("A2", "0.779"), ("A3", "0.735")]:
        ck.check("Table: decision-space effects", f"accuracy {k}", exp, fmt(accs[k][0], 3))
    ck.check("Table: decision-space effects", "A1 denominator (abstentions excluded)", 111, accs["A1"][1])
    ck.check("3.2", "abstentions (A1)", 2, sum(1 for x in code["A1"].values() if x in ("?", "")))
    ck.check("3.2", "remarks A1 / A2 / A3", "4/2/3",
             "/".join(str(sum(1 for v in hum[k].values() if v[1])) for k in ["A1", "A2", "A3"]))
    h_scaf = (accs["H1"][0] + accs["H2"][0]) / 2
    h_unsc = (accs["A1"][0] + accs["A2"][0] + accs["A3"][0]) / 3
    ck.check("Table: decision-space effects", "human mean scaffolded", "0.925", fmt(h_scaf, 3))
    ck.check("Table: decision-space effects", "human mean unscaffolded", "0.775", fmt(h_unsc, 3))
    ck.check("4.1", "human accuracy drop (points)", "15.0", fmt(100 * (h_scaf - h_unsc), 1))
    k_h = cohen_kappa_score([code["H1"][c] for c in claims], [code["H2"][c] for c in claims])
    ck.check("Table: decision-space effects", "Cohen kappa H1-H2", "0.944", fmt(k_h, 3))
    common = [c for c in claims if all(code[k][c] not in ("?", "") for k in ["A1", "A2", "A3"])]
    ck.check("Table: decision-space effects", "claims coded by every unscaffolded annotator", 111, len(common))
    pk = {f"{a}-{b}": cohen_kappa_score([code[a][c] for c in common], [code[b][c] for c in common])
          for a, b in [("A1", "A3"), ("A2", "A3"), ("A1", "A2")]}
    ck.check("Table: decision-space effects", "pairwise kappa (A1-A3 / A2-A3 / A1-A2)", "0.670/0.697/0.726",
             "/".join(fmt(v, 3) for v in pk.values()))
    cats = sorted({code[k][c] for k in ["A1", "A2", "A3"] for c in common})
    fl = fleiss_kappa([[sum(code[k][c] == cat for k in ["A1", "A2", "A3"]) for cat in cats] for c in common])
    ck.check("Table: decision-space effects", "Fleiss kappa A1-A3", "0.697", fmt(fl, 3))
    ck.check("4.1", "kappa drop", "0.247", fmt(0.944 - 0.697, 3))
    herr = [(c, code[k][c]) for k in ["H1", "H2"] for c in claims if code[k][c] != gold[c]]
    hcross = sum(1 for c, x in herr if code_theme.get(x) != theme[c])
    ck.check("4.1", "H1+H2 cross-theme errors", "1 of 17", f"{hcross} of {len(herr)}")

    # ---------------- model coding ----------------
    U = {m: {l: load_unscaffolded(m, l) for l in LEVELS} for m in MODELS}
    S = {m: load_scaffolded(m) for m in MODELS}
    total = sum(len(U[m][l]) for m in MODELS for l in LEVELS)
    ck.check("3.3", "unscaffolded model decisions", "16,950", f"{total:,}")
    ck.check("3.3", "scaffolded model decisions", "3,390", f"{sum(len(S[m]) for m in MODELS):,}")
    ck.check("3.5", "all decisions", "21,003",
             f"{total + sum(len(S[m]) for m in MODELS) + 5 * 113 + 98:,}")
    ck.check("3.5", "JSON parse success", "100%",
             "100%" if all(r["parse"] for m in MODELS for l in LEVELS for r in U[m][l]) else "<100%")

    def macc(rows):
        return sum(canon(r["code"]) == gold[r["cid"]] for r in rows) / len(rows)

    a_u = {m: macc(U[m]["L1"]) for m in MODELS}
    a_s = {m: macc(S[m]) for m in MODELS}
    for m, eu, es in [("claude-haiku-4-5", "0.835", "0.897"), ("deepseek-chat", "0.779", "0.867"),
                      ("gpt-4o-mini", "0.604", "0.652")]:
        ck.check("Table: decision-space effects", f"accuracy {m} unscaffolded L1", eu, fmt(a_u[m], 3))
        ck.check("Table: decision-space effects", f"accuracy {m} scaffolded", es, fmt(a_s[m], 3))
    gains = [100 * (a_s[m] - a_u[m]) for m in MODELS]
    ck.check("4.1", "model gain range (points)", "4.9-8.8", f"{fmt(min(gains), 1)}-{fmt(max(gains), 1)}")
    c = "claude-haiku-4-5"
    ck.check("4.1", "Claude lead over unscaffolded human mean", "6.1", fmt(100 * (a_u[c] - h_unsc), 1))
    ck.check("4.1", "human lead over scaffolded Claude", "2.7", fmt(100 * (h_scaf - a_s[c]), 1))
    ck.check("4.1", "apparent model deficit", "8.9", fmt(100 * (h_scaf - a_u[c]), 1))
    merr = [(r["cid"], canon(r["code"])) for m in MODELS for r in U[m]["L1"] if canon(r["code"]) != gold[r["cid"]]]
    mcross = sum(1 for cid, x in merr if code_theme.get(x) != theme[cid])
    ck.check("4.1", "model cross-theme errors at L1", "465 of 884 (52.6%)",
             f"{mcross} of {len(merr)} ({fmt(100 * mcross / len(merr), 1)}%)")
    c916 = {canon(r["code"]) for r in S[c] if r["cid"] == "C916"}
    ck.check("4.1", "C916 scaffolded (Claude): reference code in all runs", "yes",
             "yes" if c916 == {gold["C916"]} else "no")

    write_table("decision_space_accuracy_agreement.csv",
                ["party", "unscaffolded", "scaffolded"],
                [[m, fmt(a_u[m], 3), fmt(a_s[m], 3)] for m in MODELS] +
                [[k, fmt(accs[k][0], 3), ""] for k in ["A1", "A2", "A3"]] +
                [[k, "", fmt(accs[k][0], 3)] for k in ["H1", "H2"]] +
                [["human mean", fmt(h_unsc, 3), fmt(h_scaf, 3)],
                 ["kappa pairwise", "/".join(fmt(v, 3) for v in pk.values()), fmt(k_h, 3)],
                 ["kappa Fleiss", fmt(fl, 3), ""]])

    # ---------------- FM2: instrument-induced failure ----------------
    inval = {m: [r for l in LEVELS for r in U[m][l] if r["code"] not in taxonomy and r["code"] != "NO MATCHING CODE"]
             for m in MODELS}
    nmc = sum(1 for m in MODELS for l in LEVELS for r in U[m][l] if r["code"] == "NO MATCHING CODE")
    n_inv = sum(len(v) for v in inval.values())
    ck.check("3.5", "NO MATCHING CODE abstentions (Claude, outside L1)", 10, nmc)
    ck.check("4.2", "invalid strings, unscaffolded", "1,247 (7.4%)", f"{n_inv:,} ({fmt(100 * n_inv / total, 1)}%)")
    ck.check("4.2", "abbreviated SOFTWARE DEVELOPMENT BENEFITS", "1,167",
             f"{sum(1 for v in inval.values() for r in v if r['code'] == 'SOFTWARE DEVELOPMENT BENEFITS'):,}")
    drift = {m: 100 * len(inval[m]) / (5 * 1130) for m in MODELS}
    ck.check("Table: instrument effects", "drift % (Claude / DeepSeek / GPT)", "0.2/0.0/21.8",
             "/".join(fmt(drift[m], 1) for m in MODELS))
    corrected = sum(1 for v in inval.values() for r in v if canon(r["code"]) == gold[r["cid"]])
    ck.check("4.2", "invalid strings carrying the correct judgement", 110, corrected)
    for m, exp in [("gpt-4o-mini", "1.7"), ("claude-haiku-4-5", "0.2")]:
        rows = [r for l in LEVELS for r in U[m][l]]
        lit = sum(r["code"] == gold[r["cid"]] for r in rows) / len(rows)
        nor = sum(canon(r["code"]) == gold[r["cid"]] for r in rows) / len(rows)
        ck.check("4.2", f"normalisation shift {m} (points)", exp, fmt(100 * (nor - lit), 1))
    shown = {cl: per_theme_codes[theme[cl]] for cl in claims}
    tbl3 = []
    for m in MODELS:
        off = [r for r in S[m] if canon(r["code"]) not in shown[r["cid"]]]
        comp = [r for r in S[m] if canon(r["code"]) in shown[r["cid"]]]
        tbl3.append([m, fmt(drift[m], 1), len(off), fmt(100 * len(off) / len(S[m]), 1),
                     fmt(a_s[m], 3), fmt(macc(comp), 3)])
        if m == "gpt-4o-mini":
            ab = [r for r in S[m] if r["code"] == "SOFTWARE DEVELOPMENT BENEFITS" and theme[r["cid"]] != "SOFTWARE PROCESS"]
            ck.check("4.2", "abbreviated string on claims of other themes", 132, len(ab))
            ck.check("4.2", "themes it was carried onto", 5, len({theme[r["cid"]] for r in ab}))
    ck.check("Table: instrument effects", "off-codebook (Claude / DeepSeek / GPT)", "0/0/142", "/".join(str(r[2]) for r in tbl3))
    ck.check("Table: instrument effects", "off-codebook % GPT", "12.6", tbl3[2][3])
    ck.check("Table: instrument effects", "compliant accuracy (Claude / DeepSeek / GPT)", "0.897/0.867/0.746",
             "/".join(r[5] for r in tbl3))
    write_table("instrument_effects.csv",
                ["model", "drift_pct", "off_codebook", "off_codebook_pct", "acc_all", "acc_compliant"], tbl3)

    # ---------------- FM3: reference-standard illusion ----------------
    def tier(cl):
        a, b = code["H1"][cl] == gold[cl], code["H2"][cl] == gold[cl]
        if a and b:
            return "T0"
        if a or b:
            return "T1"
        return "T3" if code["H1"][cl] == code["H2"][cl] else "T2"

    tiers = {cl: tier(cl) for cl in claims}
    ck.check("4.5", "tiers T0/T1/T2/T3", "102/5/1/5",
             "/".join(str(sum(1 for t in tiers.values() if t == x)) for x in ["T0", "T1", "T2", "T3"]))
    always_wrong = {m: {cl for cl in claims if all(canon(r["code"]) != gold[cl] for r in S[m] if r["cid"] == cl)}
                    for m in MODELS}
    resist = sorted(set.intersection(*always_wrong.values()), key=lambda x: int(x[1:]))
    ck.check("4.3", "claims wrong in every scaffolded run of all three models", 7, len(resist))
    ck.check("4.3", "of those, claims where H1/H2 also diverged", 2, sum(1 for cl in resist if tiers[cl] != "T0"))
    t3 = [cl for cl in claims if tiers[cl] == "T3"]
    pr_pos = "CI IS RELATED TO POSITIVE IMPACTS ON PULL REQUESTS LIFE-CYCLE"
    pr_neg = "CI IS RELATED TO NEGATIVE IMPACTS ON PULL REQUESTS LIFE-CYCLE"
    ck.check("4.3", "T3 claims carrying the PR positive-impacts code", 4,
             sum(1 for cl in t3 if gold[cl] == pr_pos))
    ck.check("4.3", "of those, coded NEGATIVE IMPACTS by both annotators", 3,
             sum(1 for cl in t3 if gold[cl] == pr_pos and code["H1"][cl] == pr_neg))
    c1004 = {m: {canon(r["code"]) for r in S[m] if r["cid"] == "C1004"} for m in MODELS}
    ck.check("4.3", "C1004 scaffolded: all models HUMAN CHALLENGES in every run", "yes",
             "yes" if all(v == {"CI IS ASSOCIATED WITH HUMAN CHALLENGES"} for v in c1004.values()) else "no")
    remarks = {k: [cl for cl, v in hum[k].items() if v[1]] for k in ["A1", "A2", "A3"]}
    ck.check("4.3", "unscaffolded annotators remarking on a resistant claim", 3,
             sum(1 for k in remarks if set(remarks[k]) & set(resist)))
    write_table("resistant_claims.csv", ["claim_id", "reference_code", "H1", "H2", "tier"],
                [[cl, gold[cl], code["H1"][cl], code["H2"][cl], tiers[cl]] for cl in resist])

    # ---------------- FM4: false consensus ----------------
    nondet = {}
    for m in MODELS:
        cells = varied = 0
        for l in LEVELS:
            by = defaultdict(set)
            for r in U[m][l]:
                by[r["cid"]].add(canon(r["code"]))
            cells += len(by)
            varied += sum(1 for v in by.values() if len(v) > 1)
        nondet[m] = 100 * varied / cells
    ck.check("4.4", "cells varying across runs (DeepSeek / Claude / GPT)", "0.7/3.0/16.3",
             "/".join(fmt(nondet[m], 1) for m in ["deepseek-chat", "claude-haiku-4-5", "gpt-4o-mini"]))

    def stable_wrong(rows):
        by = defaultdict(list)
        for r in rows:
            by[r["cid"]].append(canon(r["code"]))
        return [cl for cl, v in by.items() if len(set(v)) == 1 and v[0] != gold[cl]]

    sw_u = {m: stable_wrong(U[m]["L1"]) for m in MODELS}
    sw_s = {m: stable_wrong(S[m]) for m in MODELS}
    ck.check("4.4", "stable-wrong at L1 (DeepSeek / Claude / GPT)", "25/16/36",
             "/".join(str(len(sw_u[m])) for m in ["deepseek-chat", "claude-haiku-4-5", "gpt-4o-mini"]))
    ck.check("4.4", "stable-wrong scaffolded (DeepSeek / Claude / GPT)", "15/11/33",
             "/".join(str(len(sw_s[m])) for m in ["deepseek-chat", "claude-haiku-4-5", "gpt-4o-mini"]))
    ds = [r for r in U["deepseek-chat"]["L1"] if r["cid"] in sw_u["deepseek-chat"]]
    per_claim_conf = defaultdict(list)
    for r in ds:
        per_claim_conf[r["cid"]].append(r["conf"])
    mean_conf = [statistics.mean(v) for v in per_claim_conf.values()]
    ck.check("4.4", "DeepSeek stable-wrong: mean confidence", "0.728", fmt(statistics.mean(mean_conf), 3))
    ck.check("4.4", "DeepSeek stable-wrong: claims at or above 0.80", 16, sum(1 for v in mean_conf if v >= 0.8))
    c987 = [r for r in U["deepseek-chat"]["L1"] if r["cid"] == "C987"]
    ck.check("4.4", "C987 DeepSeek: same wrong code in 10 runs at 0.85", "yes",
             "yes" if len({x["code"] for x in c987}) == 1 and canon(c987[0]["code"]) != gold["C987"]
             and all(x["conf"] == 0.85 for x in c987) else "no")
    tbl4 = []
    for m in MODELS:
        b = defaultdict(lambda: [0, 0])
        for r in U[m]["L1"]:
            k = band(r["conf"])
            b[k][0] += 1
            b[k][1] += canon(r["code"]) == gold[r["cid"]]
        n = len(U[m]["L1"])
        for k in range(5):
            if b[k][0]:
                tbl4.append([m, ["[0.0,0.2)", "[0.2,0.4)", "[0.4,0.6)", "[0.6,0.8)", "[0.8,1.0]"][k],
                             fmt(100 * b[k][0] / n, 1), fmt(b[k][1] / b[k][0], 3)])
    write_table("confidence_bands_L1.csv", ["model", "band", "share_pct", "accuracy"], tbl4)
    expect4 = {"claude-haiku-4-5": "2.7/0.800 3.5/0.487 37.1/0.761 56.8/0.907",
               "deepseek-chat": "0.8/0.000 6.3/0.141 1.8/0.000 91.2/0.845",
               "gpt-4o-mini": "5.6/0.000 0.4/0.000 16.5/0.075 15.8/0.564 61.7/0.813"}
    for m in MODELS:
        ck.check("Table: confidence bands", f"bands {m}", expect4[m], " ".join(f"{r[2]}/{r[3]}" for r in tbl4 if r[0] == m))
    withheld = {m: 100 * sum(1 for r in U[m]["L1"] if r["conf"] < 0.8) / len(U[m]["L1"]) for m in MODELS}
    ck.check("4.4", "withheld at 0.8 (Claude / DeepSeek)", "43.2/8.8",
             f"{fmt(withheld[c], 1)}/{fmt(withheld['deepseek-chat'], 1)}")
    g = [r for r in U["gpt-4o-mini"]["L1"]]
    ck.check("4.4", "GPT decisions in [0.4,0.6)", 186, sum(1 for r in g if band(r["conf"]) == 2))
    ck.check("4.4", "GPT decisions at confidence exactly zero", 63, sum(1 for r in g if r["conf"] == 0))
    ck.check("4.4", "DeepSeek decisions in [0.6,0.8), correct", "20, 0",
             f"{sum(1 for r in U['deepseek-chat']['L1'] if band(r['conf']) == 3)}, "
             f"{sum(1 for r in U['deepseek-chat']['L1'] if band(r['conf']) == 3 and canon(r['code']) == gold[r['cid']])}")
    for m, exp in [(c, "3: 13.3 vs 110: 85.5"), ("gpt-4o-mini", "37.1 vs 63.6")]:
        by = defaultdict(set)
        for r in U[m]["L1"]:
            by[r["cid"]].add(canon(r["code"]))
        var = {cl for cl, v in by.items() if len(v) > 1}
        av = macc([r for r in U[m]["L1"] if r["cid"] in var])
        ast = macc([r for r in U[m]["L1"] if r["cid"] not in var])
        got = (f"{len(var)}: {fmt(100 * av, 1)} vs {113 - len(var)}: {fmt(100 * ast, 1)}" if m == c
               else f"{fmt(100 * av, 1)} vs {fmt(100 * ast, 1)}")
        ck.check("4.4", f"accuracy on varying vs stable claims ({m})", exp, got)
    confs = defaultdict(list)
    for r in U[c]["L1"]:
        confs[r["cid"]].append(r["conf"])
    mconf = {cl: statistics.mean(v) for cl, v in confs.items()}
    esc = [cl for cl in claims if mconf[cl] < 0.8]
    ck.check("4.4", "Claude sub-threshold claims: accuracy", "74.3",
             fmt(100 * macc([r for r in U[c]["L1"] if r["cid"] in esc]), 1))

    # ---------------- FM5: escalation illusion ----------------
    ck.check("3.4", "escalated / retained at 0.8", "49/64", f"{len(esc)}/{113 - len(esc)}")
    sent = {r["cid"] for r in csv.DictReader(open(os.path.join(DATA, "instruments", "sheet_escalation_H1_as_sent.csv"),
                                                 encoding="utf-8-sig"))}
    ck.check("3.4", "escalated set equals the claims on the escalation sheets", "yes",
             "yes" if set(esc) == sent else "no")
    tbl5 = []
    for th in [0.6, 0.7, 0.8, 0.9]:
        e = [cl for cl in claims if mconf[cl] < th]
        rt = [cl for cl in claims if cl not in e]
        ue = sum(1 for cl in e if tiers[cl] != "T0")
        ur = sum(1 for cl in rt if tiers[cl] != "T0")
        h1 = sum(code["H1"][cl] == gold[cl] for cl in e) / len(e)
        h2 = sum(code["H2"][cl] == gold[cl] for cl in e) / len(e)
        tbl5.append([f"c<{th}", len(e), f"{ue} ({fmt(100 * ue / len(e), 1)}%)", len(rt),
                     f"{ur} ({fmt(100 * ur / len(rt), 1)}%)", fmt(h1, 3), fmt(h2, 3)])
    write_table("escalation_composition.csv",
                ["threshold", "escalated_n", "escalated_unstable", "retained_n", "retained_unstable",
                 "H1_acc_escalated", "H2_acc_escalated"], tbl5)
    expect5 = ["7 | 4 (57.1%) | 106 | 7 (6.6%) | 0.571 | 0.714",
               "9 | 4 (44.4%) | 104 | 7 (6.7%) | 0.667 | 0.778",
               "49 | 7 (14.3%) | 64 | 4 (6.2%) | 0.878 | 0.918",
               "98 | 11 (11.2%) | 15 | 0 (0.0%) | 0.898 | 0.929"]
    for row, exp in zip(tbl5, expect5):
        ck.check("Table: escalation composition", f"row {row[0]}", exp, " | ".join(str(x) for x in row[1:]))
    rt = [cl for cl in claims if cl not in esc]
    ck.check("4.5", "retained-set accuracy H1 / H2", "0.938/0.953",
             f"{fmt(sum(code['H1'][cl] == gold[cl] for cl in rt) / len(rt), 3)}/"
             f"{fmt(sum(code['H2'][cl] == gold[cl] for cl in rt) / len(rt), 3)}")
    dis = [cl for cl in claims if code["H1"][cl] != code["H2"][cl]]
    ck.check("4.5", "inter-annotator disagreements inside escalated set", "4 of 6",
             f"{sum(1 for cl in dis if cl in esc)} of {len(dis)}")
    ue, ur = sum(1 for cl in esc if tiers[cl] != "T0"), sum(1 for cl in rt if tiers[cl] != "T0")
    ck.check("4.5", "enrichment ratio / odds ratio", "2.3/2.50",
             f"{fmt((ue / len(esc)) / (ur / len(rt)), 1)}/"
             f"{fmt((ue / (len(esc) - ue)) / (ur / (len(rt) - ur)), 2)}")
    persist = [cl for cl in claims if all(canon(r["code"]) != gold[cl] for r in U[c]["L1"] if r["cid"] == cl)]
    ck.check("4.5", "claims Claude coded wrongly in every L1 run", 18, len(persist))
    ck.check("4.5", "of those, in a human-unstable tier / T3", "6/2",
             f"{sum(1 for cl in persist if tiers[cl] != 'T0')}/{sum(1 for cl in persist if tiers[cl] == 'T3')}")
    dec = U[c]["L1"]
    r_auto = sum(1 for r in dec if r["conf"] >= 0.8) / len(dec)
    a_auto = macc([r for r in dec if r["conf"] >= 0.8])
    ck.check("4.5", "r_auto / acc_auto (decision level)", "0.568/0.907", f"{fmt(r_auto, 3)}/{fmt(a_auto, 3)}")
    r3, a3 = round(r_auto, 3), round(a_auto, 3)        # values as substituted in the paper
    bounds = [a3 * r3 + h * (1 - r3) for h in (1.0, 0.878, 0.918)]
    ck.check("4.5", "pipeline bound (unit / H1 / H2)", "0.947/0.894/0.912", "/".join(fmt(b, 3) for b in bounds))

    # ---------------- FM6: escalation round ----------------
    E = {k: list(csv.DictReader(open(os.path.join(DATA, "human", "escalation", f"escalation_{k}.csv"),
                                     encoding="utf-8-sig"))) for k in ["H1", "H2"]}
    blind_c = post_c = harm = corr = third = avail_h = model_wrong_h = 0
    rev = Counter()
    n_dec = Counter()
    forced = merits = forced_rev = merits_rev = 0
    conf_h, conf_o = [], []
    harm_by = Counter()
    for k in ["H1", "H2"]:
        for r in E[k]:
            cl = r["cid"]
            b, f, gd, mc = code[k][cl], norm(r["FINAL_CODE"]), gold[cl], norm(r["model_code"])
            avail = mc in [norm(x) for x in r["codes_available_in_theme"].split("|")]
            blind_c += b == gd
            post_c += f == gd
            n_dec[r["DECISION"]] += 1
            if r["DECISION"] == "REJECT":
                if avail:
                    merits += 1
                    merits_rev += f != b
                else:
                    forced += 1
                    forced_rev += f != b
            if f != b:
                rev[r["DECISION"]] += 1
            is_harm = b == gd and f != gd
            if is_harm:
                harm += 1
                harm_by[k] += 1
                third += f != mc
                avail_h += avail
                model_wrong_h += mc != gd
                conf_h.append(float(r["model_confidence"]))
            else:
                conf_o.append(float(r["model_confidence"]))
            corr += b != gd and f == gd
    ck.check("4.6", "decisions", 98, sum(n_dec.values()))
    ck.check("4.6", "blind / post accuracy", "0.898/0.816", f"{fmt(blind_c / 98, 3)}/{fmt(post_c / 98, 3)}")
    ck.check("4.6", "harmful / corrective revisions", "9/1", f"{harm}/{corr}")
    ck.check("4.6", "revision rate after correct / incorrect blind judgement (%)", "10.2/10.0",
             f"{fmt(100 * harm / blind_c, 1)}/{fmt(100 * corr / (98 - blind_c), 1)}")
    ck.check("4.6", "harmful revisions per annotator (H2 / H1)", "7/2", f"{harm_by['H2']}/{harm_by['H1']}")
    ck.check("4.6", "harmful revisions where the model was itself wrong", 8, model_wrong_h)
    ck.check("4.6", "accept / reject / unsure", "73/24/1",
             f"{n_dec['ACCEPT']}/{n_dec['REJECT']}/{n_dec['UNSURE']}")
    ck.check("4.6", "revision after acceptance / rejection (%)", "4.1/25.0",
             f"{fmt(100 * rev['ACCEPT'] / n_dec['ACCEPT'], 1)}/{fmt(100 * rev['REJECT'] / n_dec['REJECT'], 1)}")
    ck.check("4.6", "forced rejections", "14 of 24", f"{forced} of {forced + merits}")
    ck.check("4.6", "revision rate on merits / forced", "0.200/0.286",
             f"{fmt(merits_rev / merits, 3)}/{fmt(forced_rev / forced, 3)}")
    ck.check("4.6", "harmful revisions to a third code", "7 of 9", f"{third} of {harm}")
    ck.check("4.6", "harmful revisions involving an available code", "5 of 9", f"{avail_h} of {harm}")
    ck.check("4.6", "model confidence on harmful / other decisions", "0.711/0.683",
             f"{fmt(statistics.mean(conf_h), 3)}/{fmt(statistics.mean(conf_o), 3)}")
    ck.check("4.6", "model accuracy on the 49 escalated claims", "0.735",
             fmt(sum(norm(r["model_code"]) == gold[r["cid"]] for r in E["H1"]) / 49, 3))
    c982 = [(norm(r["DECISION"]), norm(r["FINAL_CODE"])) for k in ["H1", "H2"] for r in E[k] if r["cid"] == "C982"]
    ck.check("4.6", "C982: both reject, both record WORKLOAD REDUCTION", "yes",
             "yes" if c982 == [("REJECT", "CI IS ASSOCIATED WITH A WORKLOAD REDUCTION")] * 2 else "no")
    write_table("escalation_revisions.csv", ["quantity", "value"],
                [["blind accuracy", fmt(blind_c / 98, 3)], ["post-exposure accuracy", fmt(post_c / 98, 3)],
                 ["harmful revisions", harm], ["corrective revisions", corr],
                 ["revision after acceptance", f"{rev['ACCEPT']} of {n_dec['ACCEPT']}"],
                 ["revision after rejection", f"{rev['REJECT']} of {n_dec['REJECT']}"],
                 ["harmful revisions to a third code", third]])

    # ---------------- appendix: accuracy by context level ----------------
    write_table("accuracy_by_context_level.csv", ["model"] + LEVELS,
                [[m] + [fmt(macc(U[m][l]), 3) for l in LEVELS] for m in MODELS])

    sys.exit(0 if ck.report() else 1)


if __name__ == "__main__":
    main()
