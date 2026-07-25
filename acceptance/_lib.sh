#!/usr/bin/env bash
set -u

# Shared helpers for user journey acceptance tests.
# Source this at the top of each journey-N.sh.

VAULT="${PAPERFORGE_TEST_VAULT:-D:/L/Med/test}"
PYTHON="${PAPERFORGE_PYTHON:-python}"

PASS=0
FAIL=0

assert() {
    local desc="$1"
    local cmd="$2"
    if eval "$cmd" 2>/dev/null; then
        echo "  PASS $desc"
        ((PASS++))
    else
        echo "  FAIL $desc"
        ((FAIL++))
    fi
}

summary() {
    echo ""
    echo "---"
    echo "$PASS passed, $FAIL failed"
    return "$FAIL"
}

run_paperforge() {
    "$PYTHON" -m paperforge --vault "$VAULT" "$@"
}

pyassert() {
    local desc="$1"
    local code="$2"
    shift 2
    if "$PYTHON" -c "$code" "$@"; then
        echo "  PASS $desc"
        ((PASS++))
    else
        echo "  FAIL $desc"
        ((FAIL++))
    fi
}
