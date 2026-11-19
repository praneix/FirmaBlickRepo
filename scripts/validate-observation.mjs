import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const schema = JSON.parse(readFileSync(new URL('../data-contracts/industrial-observation.v1.schema.json', import.meta.url), 'utf8'));
const registry = JSON.parse(readFileSync(new URL('../data-contracts/source-registry.v1.json', import.meta.url), 'utf8'));
const expected = new Map(registry.sectors.map(s => [s.canonical_code, s]));
const allowed = new Set(Object.keys(schema.properties));
const required = schema.required;

export function validateObservation(row) {
  const errors = [];
  if (!row || typeof row !== 'object' || Array.isArray(row)) return ['observation must be an object'];
  for (const k of required) if (!(k in row) || row[k] === undefined) errors.push('missing required: '+k);
  for (const k of Object.keys(row)) if (!allowed.has(k)) errors.push('unexpected field: '+k);
  if (errors.length) return errors;
  const prop = schema.properties;
  for (const [key, spec] of Object.entries(prop)) {
    if (!(key in row)) continue;
    const v=row[key];
    if ('const' in spec && v !== spec.const) errors.push(key+': invalid fixed value');
    if (spec.enum && !spec.enum.includes(v)) errors.push(key+': unknown value '+String(v));
    if (spec.type === 'integer' && (!Number.isInteger(v) || v < (spec.minimum ?? -Infinity) || v > (spec.maximum ?? Infinity))) errors.push(key+': invalid integer');
    if (spec.type === 'string' && (typeof v !== 'string' || v.length < (spec.minLength ?? 0))) errors.push(key+': invalid string');
    if (spec.pattern && (typeof v !== 'string' || !(new RegExp(spec.pattern).test(v)))) errors.push(key+': invalid pattern');
  }
  if (typeof row.value !== 'number' && row.value !== null) errors.push('value must be numeric or null');
  if (typeof row.value === 'number' && !Number.isFinite(row.value)) errors.push('value must be finite');
  if (row.value === null && (typeof row.missing_reason !== 'string' || !row.missing_reason.trim())) errors.push('null value requires missing_reason');
  if (row.value !== null && row.missing_reason) errors.push('non-null value must not have missing_reason');
  if (!Array.isArray(row.source_status_flags) || row.source_status_flags.some(x=>typeof x!=='string') || new Set(row.source_status_flags).size!==row.source_status_flags.length) errors.push('source_status_flags must be unique strings');
  if (!row.original_dimensions || typeof row.original_dimensions !== 'object' || Array.isArray(row.original_dimensions) || !Object.keys(row.original_dimensions).length || Object.values(row.original_dimensions).some(x=>typeof x!=='string'||!x.length)) errors.push('original_dimensions must be nonempty string dictionary');
  if (!Number.isFinite(Date.parse(row.retrieved_at)) || !/^\d{4}-\d\d-\d\dT/.test(row.retrieved_at)) errors.push('retrieved_at requires ISO UTC timestamp');
  if (row.source_release_at != null && !Number.isFinite(Date.parse(row.source_release_at))) errors.push('invalid source release timestamp');
  if (row.source_id==='destatis') {
    if (row.classification_system !== 'WZ' || row.classification_revision !== 'WZ2008') errors.push('Destatis classification conflict');
    if (!['42153-0001','42153-0002'].includes(row.dataset_id)) errors.push('Destatis table conflict');
    if (row.dataset_id==='42153-0001' && row.industry_code !== 'C') errors.push('aggregate table must map to manufacturing C');
    if (row.dataset_id==='42153-0002' && !['20','24','28','29'].includes(row.industry_code)) errors.push('division table requires selected two-digit WZ2008 code');
  } else if (row.source_id==='eurostat') {
    if (row.dataset_id!=='sts_inpr_m'||row.classification_system!=='NACE'||!['NACE_REV2','NACE_REV2_1'].includes(row.classification_revision)||!['C','C20','C24','C28','C29'].includes(row.industry_code)) errors.push('Eurostat classification/dataset conflict');
  } else errors.push('unknown source');
  if (!expected.size) errors.push('no source registry sectors');
  if (row.source_id==='destatis' && !expected.has(row.industry_code==='C'?'C':'C'+row.industry_code)) errors.push('industry not registered');
  if (row.source_id==='eurostat' && !expected.has(row.industry_code)) errors.push('industry not registered');
  if (row.observation_type==='provisional' && !row.source_status_flags.includes('provisional')) errors.push('provisional observation requires upstream source status evidence');
  if (row.observation_type==='official' && row.source_status_flags.includes('provisional')) errors.push('source provisional cannot be labelled final official');
  if (row.adjustment === 'unknown') errors.push('adjustment must be identified');
  return errors;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const errors=validateObservation(JSON.parse(readFileSync(process.argv[2], 'utf8')));
  if(errors.length) {console.error(errors.join('\n'));process.exitCode=1;}
  else console.log('Observation contract: valid');
}
