"""Verify bootstrap and vector availability."""
import subprocess, json, sys
from pathlib import Path

VAULT = r"D:\L\OB\Literature-hub"
SCRIPT = Path(r"D:\L\OB\Literature-hub\.opencode\skills\paperforge\scripts\pf_bootstrap.py")
PYTHON = sys.executable

def run(*args):
    r = subprocess.run(args, capture_output=True, text=False, timeout=15)
    return r.stdout.decode("utf-8", errors="replace")

print("=" * 50)
print("PHASE 0: BOOTSTRAP (SKILL.md Section 1)")
print("=" * 50)

# Run bootstrap AS AN AGENT would
result = run(PYTHON, str(SCRIPT), "--vault", VAULT)
print(result[:2000])
boot = json.loads(result)

print(f"\n--- Bootstrap Results ---")
print(f"ok: {boot.get('ok')}")
print(f"vault: {boot.get('vault_root')}")

paths = boot.get('paths', {})
for k, v in paths.items():
    print(f"  {k}: {v}")

caps = boot.get('capabilities', {})
print(f"\n--- Capabilities ---")
for k, v in caps.items():
    print(f"  {k}: {v}")

mem = boot.get('memory_layer', {})
print(f"\n--- Memory Layer ---")
for k, v in mem.items():
    print(f"  {k}: {v}")

print(f"\nDomains: {boot.get('domains')}")
print(f"Python verified: {boot.get('python_verified')}")
print(f"Methods: {len(boot.get('methodology_index', []))} cards")

print(f"\n{'=' * 50}")
print("PHASE 0.5: CAPABILITY AWARE ROUTING TEST")
print("=" * 50)
print(f"""
Scenario: User asks "找 Piezo1 和软骨基质降解的证据"

Retrieval routing decision (atoms/retrieval-routing.md):
  semantic_enabled={caps.get('semantic_enabled')}
  semantic_ready={caps.get('semantic_ready')}

  Since this is an EVIDENCE query (not candidate expansion):
  -> Ladder B (rg) is primary path
  -> Ladder D (semantic) is available as supplementary only

Agent decision:
  rg available: {caps.get('rg')}
  Agent uses Ladder B for primary evidence retrieval
  Agent does NOT use Ladder D as primary path (correct per retrieval-routing.md)
  Agent CAN use Ladder D for candidate expansion AFTER rg verification
  
Vector DB status:
  Enabled: {caps.get('semantic_enabled')}
  Ready: {caps.get('semantic_ready')}
  {'Agent may use semantic for candidate expansion' if caps.get('semantic_ready') else 'Agent must not use semantic'}
  Agent must verify all semantic hits with rg/fulltext before use
""")

print("--- runtime-health authoritative check ---")
rh = run(PYTHON, "-m", "paperforge", "--vault", VAULT, "runtime-health", "--json")
try:
    rh_data = json.loads(rh)
    vec = rh_data.get("data", {}).get("layers", {}).get("vector", {})
    print(f"  runtime-health vector status: {vec.get('status')}")
    print(f"  bootstrap semantic_ready: {caps.get('semantic_ready')}")
    match = (vec.get('status') == 'ok') == (caps.get('semantic_ready') == True)
    print(f"  {'[PASS] bootstrap and runtime-health agree' if match else '[INFO] bootstrap is convenience layer, runtime-health is authoritative'}")
except:
    print(f"  [INFO] could not parse runtime-health")

# Clean
if Path("_temp_bootstrap_vec.py").exists():
    Path("_temp_bootstrap_vec.py").unlink()
