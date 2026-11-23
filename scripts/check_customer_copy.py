#!/usr/bin/env python3
"""Fail-closed release copy audit. Run with --release before any public launch."""
import argparse
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ENERGY=ROOT/"site/research/germany-industrial-energy-decision-report-2026/index.html"
CONTRACT=ROOT/"product/contracts/commercial-v1-offer.v1.json"
# Only non-client-facing operational review language. Do not flag legitimate
# research limitations, uncertainty, methodological caveats or source dates.
PROHIBITED={
 "internal_approval":r"editorial (?:candidate|preview|review)|publication (?:approval|pending)|owner (?:release|approval)",
 "prototype_label":r"\bV\d+-RC\d+\b|\bresearch candidate\b|\bformat in review\b",
 "transaction_placeholder":r"no orders are being accepted|price, purchase and customer delivery are awaiting|public pricing has not been approved",
 "review_workflow":r"rights and editorial approval pending|licensing, refunds and fulfilment terms are not yet final",
 "illustrative_artwork":r"illustrative linework|no market values plotted",
}

def issues_for_text(text):
 return {name:re.findall(pattern,text,re.I) for name,pattern in PROHIBITED.items() if re.search(pattern,text,re.I)}

def audit_release():
 d=json.loads(CONTRACT.read_text(encoding="utf-8"))
 issues=[]
 for flag in ("commercial_scope_approval","pricing_approved","publication_approved","legal_approved","production_authorized","checkout_enabled"):
  if d.get(flag) is not True:issues.append("Release gate false: "+flag)
 for name,matches in issues_for_text(ENERGY.read_text(encoding="utf-8")).items():
  issues.append(f"Client-facing Energy page contains {name}: {matches[:4]}")
 # PDF content, receipts, emails and checkout assets must be audited against
 # the exact immutable release manifest by the separate publication pipeline.
 if not d.get("owner_product_freeze"):issues.append("Missing frozen product specification")
 return issues

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--release",action="store_true",required=True,help="Fail unless final client-facing copy and all release flags are approved")
 p.parse_args()
 issues=audit_release()
 for issue in issues:print("BLOCK:",issue)
 if issues:raise SystemExit(1)
 print("PASS: customer-facing copy and commercial release flags")
