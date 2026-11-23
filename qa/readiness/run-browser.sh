#!/bin/sh
mkdir -p /evidence/browser
: > /evidence/browser/failures.txt
run_suite(){
 name=$(basename "$1" .cjs)
 if timeout 130 node "$1" >"/evidence/browser/$name.log" 2>&1; then echo "PASS $name"; else echo "FAIL $name"; tail -n 8 "/evidence/browser/$name.log"; echo "$name" >> /evidence/browser/failures.txt; fi
}
export NODE_OPTIONS='--require /qa/browser-preload.cjs'
export RECOVERY_ISOLATED_QA=1
export QA_SOCKET_API_URL=http://backend:8001
export ICON_QA_URL=http://crm.localhost
export EVIDENCE_DIR=/evidence
for file in /audit/tests/*.cjs; do
 case "$file" in *location-select.cjs|*category-icon-picker-live.cjs|*destination-sessions-live.cjs|*shipping-subsidy-live.cjs|*tcc-live-flow.cjs|*product-editor-live.cjs) continue;; esac
 while [ "$(jobs -p | wc -l)" -ge 3 ]; do sleep 1; done
 run_suite "$file" &
done
wait
test ! -s /evidence/browser/failures.txt
