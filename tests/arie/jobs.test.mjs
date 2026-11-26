import test from 'node:test';
import assert from 'node:assert/strict';
import {CONTRACT_VERSION, MAX_ATTEMPTS, MAX_LEASE_MS, ResearchJobs} from '../../research/arie/jobs.mjs';

function fixture(maxAttempts = 2) {
  let now = 1000;
  const jobs = new ResearchJobs({clock: () => now});
  const input = {
    id: 'job-1', commissionId: 'commission-1', idempotencyKey: 'chapter-1',
    taskKind: 'research', payload: {chapter: 1}, maxAttempts
  };
  jobs.create(input);
  return {jobs, input, setTime: value => { now = value; }};
}

const evidence = {
  eligibilityVerified: true, budgetReserved: true, regionVerified: true,
  nonproductionAuthorized: true
};

test('versioned jobs enforce scoped idempotency and protect stored data', () => {
  const {jobs, input} = fixture();
  input.payload.chapter = 2;
  const job = jobs.get(input.id);
  assert.equal(job.version, CONTRACT_VERSION);
  assert.equal(job.payload.chapter, 1);
  job.payload.chapter = 3;
  assert.equal(jobs.get(input.id).payload.chapter, 1);
  assert.throws(() => jobs.create({...input, id: 'job-2'}), /idempotency/);
  assert.throws(() => jobs.create({...input, idempotencyKey: 'other'}), /duplicate job id/);
  assert.equal(jobs.create({...input, id: 'job-2', commissionId: 'commission-2'}).state, 'queued');
  for (const maxAttempts of [0, -1, MAX_ATTEMPTS + 1, 1.5, NaN]) {
    assert.throws(() => jobs.create({...input, id: 'new', idempotencyKey: 'new', maxAttempts}), /invalid job/);
  }
  assert.throws(() => jobs.create({...input, id: 'new', idempotencyKey: ' '}), /invalid job/);
});

test('only one claimant leases and completion is accepted exactly once', () => {
  const {jobs, input} = fixture();
  const lease = jobs.claim(input.id, 'worker-a', 100);
  assert.deepEqual(lease, {jobId: input.id, owner: 'worker-a', attempt: 1});
  assert.equal(jobs.claim(input.id, 'worker-b', 100), null);
  const result = {value: 42};
  assert.deepEqual(jobs.complete(lease, result), {accepted: true});
  result.value = 99;
  assert.deepEqual(jobs.complete(lease, {value: 100}), {accepted: false});
  assert.equal(jobs.get(input.id).result.value, 42);
  assert.equal(jobs.claim(input.id, 'worker-b', 100), null);
});

test('expiry recovers a lease and fences stale owners, including the same owner', () => {
  const {jobs, input, setTime} = fixture(3);
  const first = jobs.claim(input.id, 'worker-a', 100);
  setTime(1100);
  assert.deepEqual(jobs.complete(first, 'expired'), {accepted: false});
  assert.equal(jobs.fail(first), false);
  const second = jobs.claim(input.id, 'worker-b', 100);
  assert.equal(second.attempt, 2);
  assert.deepEqual(jobs.complete(first, 'stale'), {accepted: false});
  assert.equal(jobs.canDispatch(first, evidence), false);
  setTime(1200);
  const third = jobs.claim(input.id, 'worker-a', 100);
  assert.equal(third.attempt, 3);
  assert.deepEqual(jobs.complete(first, 'stale same owner'), {accepted: false});
  assert.deepEqual(jobs.complete(second, 'stale other owner'), {accepted: false});
  assert.deepEqual(jobs.complete(third, 'accepted'), {accepted: true});
});

test('failures and expired final leases exhaust the retry budget', () => {
  const {jobs, input, setTime} = fixture();
  const first = jobs.claim(input.id, 'worker-a', 10);
  assert.equal(jobs.fail(first), true);
  assert.equal(jobs.get(input.id).state, 'queued');
  const second = jobs.claim(input.id, 'worker-b', 10);
  assert.equal(jobs.fail(second), true);
  assert.equal(jobs.get(input.id).state, 'failed');
  assert.equal(jobs.claim(input.id, 'worker-c', 10), null);

  const other = fixture(1);
  const finalLease = other.jobs.claim(other.input.id, 'worker-a', 10);
  other.setTime(1010);
  assert.equal(other.jobs.claim(other.input.id, 'worker-b', 10), null);
  assert.equal(other.jobs.get(other.input.id).state, 'failed');
  assert.deepEqual(other.jobs.complete(finalLease, 'late'), {accepted: false});
  setTime(2000);
  assert.equal(jobs.claim(input.id, 'worker-c', 10), null);
});

test('dispatch stub requires every explicit gate and a current lease', () => {
  const {jobs, input, setTime} = fixture();
  const lease = jobs.claim(input.id, 'worker', 10);
  assert.equal(jobs.canDispatch(lease, undefined), false);
  for (const key of Object.keys(evidence)) {
    assert.equal(jobs.canDispatch(lease, {...evidence, [key]: false}), false);
    assert.equal(jobs.canDispatch(lease, {...evidence, [key]: 'true'}), false);
  }
  assert.equal(jobs.canDispatch(lease, evidence), true);
  setTime(1010);
  assert.equal(jobs.canDispatch(lease, evidence), false);
});

for (const state of ['blocked', 'cancelled']) {
  test(`${state} jobs cannot claim, complete, or dispatch`, () => {
    const {jobs, input} = fixture();
    const lease = jobs.claim(input.id, 'worker', 100);
    assert.equal(jobs.stop(input.id, state), true);
    assert.equal(jobs.claim(input.id, 'other', 100), null);
    assert.equal(jobs.canDispatch(lease, evidence), false);
    assert.deepEqual(jobs.complete(lease, 'result'), {accepted: false});
    assert.equal(jobs.stop(input.id, state), false);
    assert.equal(jobs.get(input.id).state, state);
    const queued = fixture();
    assert.equal(queued.jobs.stop(queued.input.id, state), true);
    assert.equal(queued.jobs.claim(queued.input.id, 'worker', 100), null);
  });
}

test('invalid lease and clock inputs fail closed', () => {
  const {jobs, input} = fixture();
  for (const duration of [0, -1, 1.5, MAX_LEASE_MS + 1, NaN]) {
    assert.throws(() => jobs.claim(input.id, 'worker', duration), /invalid lease/);
  }
  assert.throws(() => jobs.claim(input.id, '', 1), /invalid lease/);
  assert.throws(() => jobs.stop(input.id, 'completed'), /invalid stop/);
  const badClock = new ResearchJobs({clock: () => NaN});
  assert.throws(() => badClock.create(input), /invalid clock/);
  const overflow = new ResearchJobs({clock: () => Number.MAX_SAFE_INTEGER});
  overflow.create(input);
  assert.throws(() => overflow.claim(input.id, 'worker', 1), /expiry/);
  assert.equal(overflow.get(input.id).state, 'queued');
});

test('reentrant payload cloning cannot create duplicate idempotency keys', () => {
  const {jobs, input} = fixture();
  const nested = {...input, id: 'nested', idempotencyKey: 'new-key', payload: {}};
  const payload = {
    get chapter() {
      jobs.create(nested);
      return 1;
    }
  };
  assert.throws(() => jobs.create({...nested, id: 'outer', payload}), /idempotency/);
  assert.equal(jobs.get('nested').id, 'nested');
  assert.throws(() => jobs.get('outer'), /unknown/);
});

test('reentrant result and gate getters cannot bypass lease state', () => {
  const first = fixture();
  const lease = first.jobs.claim(first.input.id, 'worker', 100);
  const result = {
    get value() {
      first.jobs.stop(first.input.id, 'cancelled');
      return 42;
    }
  };
  assert.deepEqual(first.jobs.complete(lease, result), {accepted: false});
  assert.equal(first.jobs.get(first.input.id).state, 'cancelled');

  const second = fixture();
  const otherLease = second.jobs.claim(second.input.id, 'worker', 100);
  const gates = {
    ...evidence,
    get regionVerified() {
      second.jobs.stop(second.input.id, 'blocked');
      return true;
    }
  };
  assert.equal(second.jobs.canDispatch(otherLease, gates), false);
  assert.equal(second.jobs.get(second.input.id).state, 'blocked');
});
