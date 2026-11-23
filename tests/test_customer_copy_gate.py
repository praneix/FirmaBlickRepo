import importlib.util
import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"scripts/check_customer_copy.py"
spec=importlib.util.spec_from_file_location("release_copy",P)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class ReleaseCopyGateTests(unittest.TestCase):
 def test_rejects_internal_preview_and_prototype_language(self):
  sample="Editorial candidate, V4-RC2. Public pricing has not been approved. Illustrative linework."
  result=mod.issues_for_text(sample)
  self.assertIn("internal_approval",result)
  self.assertIn("prototype_label",result)
  self.assertIn("transaction_placeholder",result)
  self.assertIn("illustrative_artwork",result)
 def test_accepts_real_methodological_caveats(self):
  sample="This chart shows actual 2025 monthly means. Assumptions and uncertainty are explicit. The analysis is not a site-specific investment recommendation."
  self.assertEqual(mod.issues_for_text(sample),{})
 def test_release_stays_blocked_until_all_assets_and_approvals_clear(self):
  issues=mod.audit_release()
  self.assertTrue(any("publication_approved" in x for x in issues))
  self.assertTrue(any("editorial" in x.lower() for x in issues))
if __name__=="__main__":unittest.main()
