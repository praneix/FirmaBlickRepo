import json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"product/contracts/commercial-v1-offer.v1.json"
class ContractSafetyTests(unittest.TestCase):
 def setUp(self):self.d=json.loads(P.read_text(encoding="utf-8"))
 def test_release_is_fully_closed(self):
  for x in ("commercial_scope_approval","publication_approved","production_authorized","pricing_approved","legal_approved","checkout_enabled","forecast_approved"):
   self.assertIs(self.d[x],False,x)
 def test_one_real_first_sku(self):
  self.assertEqual(self.d["offer"]["sku"],"FB-ENERGY-DE-2026-01")
  self.assertTrue(self.d["offer"]["sample"]["free"])
  self.assertTrue(self.d["offer"]["sample"]["download_without_registration"])
  self.assertTrue(self.d["offer"]["full_report"]["protected_delivery"])
  self.assertTrue(self.d["offer"]["full_report"]["access_requires_verified_order"])
 def test_customer_contract_and_decisions(self):
  self.assertEqual(len(self.d["positioning"]["customer_segments"]),3)
  self.assertEqual({x["id"] for x in self.d["open_owner_decisions"]},{"SCOPE","PRICE","PAYMENTS","LEGAL","GO_LIVE"})
  statuses={x["id"]:x["status"] for x in self.d["open_owner_decisions"]}
  self.assertEqual(statuses["SCOPE"],"PROVISIONAL_AWAITING_FINAL_APPROVAL")
  self.assertEqual(statuses["PRICE"],"PROVISIONAL_AWAITING_FINAL_APPROVAL")
  for key in ("PAYMENTS","LEGAL","GO_LIVE"):
   self.assertEqual(statuses[key],"AWAITING")
  p=self.d["owner_provisional_direction"]
  self.assertEqual(p["approval_state"],"PROVISIONAL_NOT_APPROVED")
  self.assertEqual(p["launch_scope_option"],"A")
  self.assertEqual(p["pricing_eur_ex_tax"],149)
  self.assertEqual(p["primary_buyer_segment_id"],"cfo")
  self.assertEqual(self.d["positioning"]["primary_buyer_segment_id"],"cfo")
  self.assertEqual(self.d["positioning"]["buyer_priority_status"],"PROVISIONAL_OWNER_PREFERENCE")
  self.assertTrue(self.d["release_scope_options"]["A"]["owner_approval_required"])
  self.assertTrue(self.d["release_scope_options"]["B"]["owner_approval_required"])
 def test_evidence_separation(self):
  d=self.d["verified_data_policy"]
  self.assertEqual(set(d["five_sectors"]),{"C","C20","C24","C28","C29"})
  self.assertEqual(d["source"],"Destatis GENESIS")
  self.assertEqual(d["forecast_status"],"BLOCKED_PENDING_INDEPENDENT_REVIEW")
  self.assertTrue(d["do_not_mix_real_and_synthetic"])
 def test_checkout_blocked(self):
  self.assertEqual(self.d["commercial_choices"]["price_status"],"PROVISIONAL_OWNER_PREFERENCE_REQUIRES_FINAL_APPROVAL")
  checkout=[x for x in self.d["digital_customer_journey"] if x["step"]=="checkout"][0]
  self.assertEqual(checkout["status"],"DISABLED_UNTIL_PRICE_LEGAL_PROVIDER_APPROVAL")
if __name__=="__main__":unittest.main()
