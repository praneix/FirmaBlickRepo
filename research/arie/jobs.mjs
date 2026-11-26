export const CONTRACT_VERSION = 1;
export const MAX_ATTEMPTS = 10;
export const MAX_LEASE_MS = 24 * 60 * 60 * 1000;

const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const copy = value => structuredClone(value);

export class ResearchJobs {
  #jobs = new Map();
  #keys = new Map();
  #clock;

  constructor({clock}) {
    if (typeof clock !== 'function') throw new TypeError('clock is required');
    this.#clock = clock;
  }

  #now() {
    const now = this.#clock();
    if (!Number.isSafeInteger(now) || now < 0) throw new RangeError('invalid clock');
    return now;
  }

  #job(id) {
    const job = this.#jobs.get(id);
    if (!job) throw new Error('unknown job');
    return job;
  }

  #owns(job, lease, now) {
    return job.state === 'leased' && lease != null &&
      lease.jobId === job.id && lease.owner === job.leaseOwner &&
      lease.attempt === job.attemptCount && now < job.leaseExpiresAt;
  }

  create({id, commissionId, idempotencyKey, taskKind, payload, priority = 0, maxAttempts}) {
    if (![id, commissionId, idempotencyKey, taskKind].every(nonempty) ||
        !Number.isSafeInteger(priority) || !Number.isSafeInteger(maxAttempts) ||
        maxAttempts < 1 || maxAttempts > MAX_ATTEMPTS) {
      throw new TypeError('invalid job');
    }
    if (this.#jobs.has(id)) throw new Error('duplicate job id');
    const keys = this.#keys.get(commissionId);
    if (keys?.has(idempotencyKey)) throw new Error('duplicate idempotency key');
    const job = {
      version: CONTRACT_VERSION, id, commissionId, idempotencyKey, taskKind,
      payload: copy(payload), priority, state: 'queued', attemptCount: 0,
      maxAttempts, leaseOwner: null, leaseExpiresAt: null, updatedAt: this.#now()
    };
    this.#jobs.set(id, job);
    if (!keys) this.#keys.set(commissionId, new Set([idempotencyKey]));
    else keys.add(idempotencyKey);
    return copy(job);
  }

  get(id) {
    return copy(this.#job(id));
  }

  claim(id, owner, leaseMs) {
    if (!nonempty(owner) || !Number.isSafeInteger(leaseMs) ||
        leaseMs < 1 || leaseMs > MAX_LEASE_MS) throw new TypeError('invalid lease');
    const job = this.#job(id);
    const now = this.#now();
    if (job.state !== 'queued' &&
        !(job.state === 'leased' && now >= job.leaseExpiresAt)) return null;
    if (job.attemptCount >= job.maxAttempts) {
      job.state = 'failed';
      job.leaseOwner = null;
      job.leaseExpiresAt = null;
      job.updatedAt = now;
      return null;
    }
    if (!Number.isSafeInteger(now + leaseMs)) throw new RangeError('invalid lease expiry');
    job.state = 'leased';
    job.attemptCount++;
    job.leaseOwner = owner;
    job.leaseExpiresAt = now + leaseMs;
    job.updatedAt = now;
    return {jobId: id, owner, attempt: job.attemptCount};
  }

  complete(lease, result) {
    const job = this.#job(lease?.jobId);
    const now = this.#now();
    if (!this.#owns(job, lease, now)) return {accepted: false};
    const storedResult = copy(result);
    job.state = 'completed';
    job.result = storedResult;
    job.leaseOwner = null;
    job.leaseExpiresAt = null;
    job.updatedAt = now;
    return {accepted: true};
  }

  fail(lease) {
    const job = this.#job(lease?.jobId);
    const now = this.#now();
    if (!this.#owns(job, lease, now)) return false;
    job.state = job.attemptCount >= job.maxAttempts ? 'failed' : 'queued';
    job.leaseOwner = null;
    job.leaseExpiresAt = null;
    job.updatedAt = now;
    return true;
  }

  stop(id, state) {
    if (state !== 'blocked' && state !== 'cancelled') throw new TypeError('invalid stop state');
    const job = this.#job(id);
    if (job.state !== 'queued' && job.state !== 'leased') return false;
    const now = this.#now();
    job.state = state;
    job.leaseOwner = null;
    job.leaseExpiresAt = null;
    job.updatedAt = now;
    return true;
  }

  canDispatch(lease, evidence) {
    const job = this.#job(lease?.jobId);
    return this.#owns(job, lease, this.#now()) &&
      evidence?.eligibilityVerified === true &&
      evidence?.budgetReserved === true &&
      evidence?.regionVerified === true &&
      evidence?.nonproductionAuthorized === true;
  }
}
