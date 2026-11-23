import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'site/research/germany-industrial-energy-decision-report-2026/energy-2025-monthly.json'
SOURCE=ROOT/'research/energy/data/smard_2025_verified_hourly_summary.json'
class EnergyHeroOriginalData(unittest.TestCase):
 def test_exact_monthly_values_match_archived_source(self):
  public=json.loads(PUBLIC.read_text())
  source=json.loads(SOURCE.read_text())
  self.assertEqual(public['publication_state'],'protected_preview_only')
  self.assertEqual(public['geography'],'DE-LU')
  self.assertEqual(public['unit'],'EUR/MWh')
  self.assertEqual(public['source_raw_git_blob_sha'],source['source_blob_sha'])
  self.assertEqual(public['source_url'],source['source_url'])
  self.assertEqual(public['annual_time_weighted_mean_eur_mwh'],source['time_weighted_average_eur_mwh'])
  self.assertEqual(len(public['months']),12)
  for item,(period,original) in zip(public['months'],sorted(source['monthly'].items())):
   self.assertEqual(item['period'],period)
   self.assertEqual(item['mean_eur_mwh'],original['average'])
   self.assertEqual(item['hours'],original['hours'])
  self.assertEqual(sum(x['hours'] for x in public['months']),8760)
if __name__=='__main__':unittest.main()
