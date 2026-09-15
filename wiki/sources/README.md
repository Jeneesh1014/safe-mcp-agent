# raw_docs/

Mock enterprise documents fed into OpenKB's compile step.

These files are **checked into git** — they are source material, not generated
output. Keep them small and text-based so the compile step stays fast on a
local model.

## Files

| File | Description |
|---|---|
| `employee_handbook.txt` | HR policies, data handling rules, conduct guidelines |
| `infosec_policy.txt` | Security controls, classification levels, incident response |
| `support_runbook.txt` | Customer support procedures, escalation paths, data rules |

## OpenKB compile step (run once, Week 1)

```bash
cd reference_system/data
openkb init          # creates .openkb/config.yaml — edit model before running
# Edit .openkb/config.yaml: set model: ollama/llama3.2 (or whatever you have pulled)
openkb compile raw_docs/ --output wiki/
```

The compiled `wiki/` directory is **gitignored** — it's regenerated from
`raw_docs/` and should not be committed as state.

If compile quality is rough on a local model, simplify the source docs
rather than switching to a paid API. $0 cost is a hard constraint.
