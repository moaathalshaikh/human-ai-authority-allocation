#!/usr/bin/env python3
"""
Who Decides, and on What Evidence? -- replication package
=========================================================
Step 5 of 6. Scaffolded condition (all three models, L1).

The prompt is byte-identical to prompts/unscaffolded/prompt_L1.txt except the
codebook block, which is restricted to the codes of the claim's reference theme.

Usage:
    export ANTHROPIC_API_KEY=PUT_YOUR_API_KEY_HERE
    export OPENAI_API_KEY=PUT_YOUR_API_KEY_HERE
    export DEEPSEEK_API_KEY=PUT_YOUR_API_KEY_HERE
    python scripts/05_run_scaffolded.py --model claude --level L1 --dry-run
    python scripts/05_run_scaffolded.py --model claude --level L1 --runs 10

Output: data/model/scaffolded/<model>_L1.csv
"""

import json, argparse, csv, os, sys, time, re
from collections import defaultdict

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_FILE  = os.path.join(_ROOT, "data", "reference", "ci_claims_reference.json")
PROMPT_DIR = os.path.join(_ROOT, "prompts", "unscaffolded")

# ---------------------------------------------------------------------------
# API KEYS -- paste here, or set as environment variables before running.
# In Colab you can instead use:
#     from google.colab import userdata
#     os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")

# Must match Condition A exactly.
MODEL_IDS = {
    "claude":   "claude-haiku-4-5-20251001",
    "openai":   "gpt-4o-mini-2024-07-18",
    "deepseek": "deepseek-chat",
}

TEMPERATURE = 0.0
MAX_TOKENS  = 512


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def build_theme_codebooks(gold):
    themes = defaultdict(set)
    for r in gold:
        themes[r["labels"]["theme"].strip().upper()].add(
            r["labels"]["code"].strip().upper())
    return {t: sorted(c) for t, c in themes.items()}


def load_prompt_template(level):
    with open(os.path.join(PROMPT_DIR, f"prompt_{level}.txt"), encoding="utf-8") as f:
        return f.read()


def make_scaffolded_prompt(template, theme, codes):
    head_marker = "=== CODEBOOK ==="
    tail_marker = "=== DISAMBIGUATION RULES ==="
    if head_marker not in template or tail_marker not in template:
        sys.exit("ERROR: prompt file is missing the expected markers.")
    head = template.split(head_marker)[0]
    tail = tail_marker + template.split(tail_marker, 1)[1]
    codebook = (
        f"{head_marker}\n\n"
        f"The claim below belongs to the theme: {theme}\n"
        f"Assign one of the codes listed under that theme.\n\n"
        f"-- THEME: {theme} --\n"
        + "\n".join(f"- {c}" for c in codes) + "\n\n"
    )
    return head + codebook + tail


def fill_placeholders(prompt, rec):
    inp = rec["input"]
    out = prompt.replace("{claim}", inp.get("claim", ""))
    out = out.replace("{study_title}", str(inp.get("study_title", "Not reported")))
    out = out.replace("{kind}",        str(inp.get("kind", "Not reported")))
    out = out.replace("{variables}",   str(inp.get("variables", "Not reported")))
    return out


# ---------------------------------------------------------------------------
# Clients (created once, reused)
# ---------------------------------------------------------------------------
_clients = {}

def get_client(model_name):
    if model_name in _clients:
        return _clients[model_name]
    if model_name == "claude":
        from anthropic import Anthropic
        c = Anthropic(api_key=ANTHROPIC_API_KEY)
    elif model_name == "openai":
        from openai import OpenAI
        c = OpenAI(api_key=OPENAI_API_KEY)
    elif model_name == "deepseek":
        from openai import OpenAI            # DeepSeek is OpenAI-compatible
        c = OpenAI(api_key=DEEPSEEK_API_KEY,
                   base_url="https://api.deepseek.com")
    else:
        raise ValueError(model_name)
    _clients[model_name] = c
    return c


def parse_json(text):
    """Extract the JSON object. Falls back to a regex scan if the model
    wrapped the object in code fences or prose."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*?\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {"code": "", "theme": "", "confidence": None}


def call_model(model_name, prompt, retries=4):
    client   = get_client(model_name)
    model_id = MODEL_IDS[model_name]
    for attempt in range(retries):
        try:
            if model_name == "claude":
                r = client.messages.create(
                    model=model_id, max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}])
                txt = r.content[0].text
            else:
                r = client.chat.completions.create(
                    model=model_id, max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    messages=[{"role": "user", "content": prompt}])
                txt = r.choices[0].message.content
            return parse_json(txt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"    !! failed after {retries} attempts: {e}")
                return {"code": "", "theme": "", "confidence": None}
            time.sleep(2 ** attempt)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(MODEL_IDS))
    ap.add_argument("--level", default="L1", choices=["L1","L2","L3","L4","L5"])
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    gold  = json.load(open(GOLD_FILE, encoding="utf-8"))
    books = build_theme_codebooks(gold)
    tmpl  = load_prompt_template(a.level)

    print("="*60)
    print(f"  MODEL SHORT : {a.model}")
    print(f"  MODEL ID    : {MODEL_IDS[a.model]}   <-- must match Condition A")
    print(f"  TEMPERATURE : {TEMPERATURE}   MAX_TOKENS: {MAX_TOKENS}")
    print(f"  LEVEL       : {a.level}   RUNS: {a.runs}")
    print("="*60)
    print(f"claims={len(gold)}  themes={len(books)}")
    for t, c in sorted(books.items()):
        print(f"   {t:26s} {len(c)} codes")

    prepared = []
    for rec in gold:
        theme = rec["labels"]["theme"].strip().upper()
        codes = books[theme]
        p = make_scaffolded_prompt(tmpl, theme, codes)
        prepared.append((rec["paper_id"], theme, len(codes),
                         fill_placeholders(p, rec)))

    if a.dry_run:
        path = f"dryrun_{a.model}_{a.level}.txt"
        open(path, "w", encoding="utf-8").write(prepared[0][3])
        print(f"\nDRY RUN -> {path}\nOnly the codebook block should differ "
              f"from prompts/unscaffolded/prompt_{a.level}.txt")
        return

    out_path = os.path.join(_ROOT, "data", "model", "scaffolded",
                            f"{ {'claude':'claude-haiku-4-5','openai':'gpt-4o-mini','deepseek':'deepseek-chat'}[a.model] }_{a.level}.csv")
    done = set()
    if os.path.exists(out_path):                       # resume after a crash
        with open(out_path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                done.add((row["claim_id"], int(row["run"])))
        print(f"resuming: {len(done)} rows already present")

    mode = "a" if done else "w"
    with open(out_path, mode, newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if not done:
            w.writerow(["claim_id","model","model_id","level","run",
                        "predicted_code","predicted_theme",
                        "confidence","choice_set_size"])
        for run in range(1, a.runs + 1):
            t0 = time.time()
            for cid, theme, n_codes, prompt in prepared:
                if (cid, run) in done:
                    continue
                r = call_model(a.model, prompt)
                w.writerow([cid, a.model, MODEL_IDS[a.model], a.level, run,
                            (r.get("code")  or "").strip().upper(),
                            (r.get("theme") or "").strip().upper(),
                            r.get("confidence"), n_codes])
            fh.flush()
            print(f"  run {run:2d}/{a.runs} done ({time.time()-t0:.0f}s)")

    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
