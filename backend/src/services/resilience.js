/**
 * MAESTRO - Production Resilience Layer (Node.js)
 *
 * Provides:
 *   • CircuitBreaker — prevents cascading failures to the Python agent service
 *   • retryWithBackoff — exponential backoff + jitter for transient HTTP errors
 *   • Structured request logging
 */

// ─── Circuit Breaker ────────────────────────────────────────────────────

const STATES = Object.freeze({
  CLOSED: 'CLOSED',       // normal
  OPEN: 'OPEN',           // failing → reject fast
  HALF_OPEN: 'HALF_OPEN', // probing → allow one request
});

class CircuitBreaker {
  /**
   * @param {Object} opts
   * @param {string} opts.name - Label for logs
   * @param {number} opts.failureThreshold - Consecutive failures before opening
   * @param {number} opts.recoveryTimeoutMs - Ms to wait before half-open probe
   */
  constructor({ name = 'default', failureThreshold = 3, recoveryTimeoutMs = 60_000 } = {}) {
    this.name = name;
    this.failureThreshold = failureThreshold;
    this.recoveryTimeoutMs = recoveryTimeoutMs;

    this._state = STATES.CLOSED;
    this._failureCount = 0;
    this._lastFailureTime = 0;
    this._lastError = null;
  }

  get state() {
    if (
      this._state === STATES.OPEN &&
      Date.now() - this._lastFailureTime >= this.recoveryTimeoutMs
    ) {
      this._state = STATES.HALF_OPEN;
      console.log(`[circuit:${this.name}] → HALF_OPEN (probing)`);
    }
    return this._state;
  }

  get isOpen() {
    return this.state === STATES.OPEN;
  }

  recordSuccess() {
    if (this._state !== STATES.CLOSED) {
      console.log(`[circuit:${this.name}] → CLOSED (recovered)`);
    }
    this._failureCount = 0;
    this._lastError = null;
    this._state = STATES.CLOSED;
  }

  recordFailure(error) {
    this._failureCount += 1;
    this._lastFailureTime = Date.now();
    this._lastError = error.message || String(error);
    if (this._failureCount >= this.failureThreshold) {
      this._state = STATES.OPEN;
      console.warn(
        `[circuit:${this.name}] → OPEN after ${this._failureCount} failures: ${this._lastError}`
      );
    }
  }

  /** @returns {{ name: string, state: string, failureCount: number, lastError: string|null }} */
  toHealth() {
    return {
      name: this.name,
      state: this.state,
      failureCount: this._failureCount,
      lastError: this._lastError,
    };
  }
}

// ─── Retry with Exponential Backoff ─────────────────────────────────────

/**
 * Retry an async function with exponential backoff + jitter.
 *
 * @param {Function} fn - Async function to call
 * @param {Object} opts
 * @param {number} opts.maxAttempts - Total attempts (default 3)
 * @param {number} opts.baseDelayMs - Initial delay (default 1000)
 * @param {number} opts.maxDelayMs - Cap on delay (default 30000)
 * @param {CircuitBreaker} [opts.circuit] - Optional circuit breaker
 * @returns {Promise<*>} - Result of fn()
 */
async function retryWithBackoff(fn, { maxAttempts = 3, baseDelayMs = 1000, maxDelayMs = 30000, circuit = null } = {}) {
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    // Circuit check
    if (circuit?.isOpen) {
      throw new Error(`Circuit '${circuit.name}' is OPEN — call rejected`);
    }

    try {
      const result = await fn();
      circuit?.recordSuccess();
      return result;
    } catch (err) {
      lastError = err;
      circuit?.recordFailure(err);

      if (attempt === maxAttempts) break;

      // Retryable? Only retry on 5xx, timeout, or network errors
      const status = err.response?.status;
      const isRetryable = !status || status >= 500 || status === 429;
      if (!isRetryable) break;

      const delay = Math.min(baseDelayMs * 2 ** (attempt - 1), maxDelayMs);
      const jitter = Math.random() * delay * 0.3;
      const totalDelay = delay + jitter;

      console.warn(
        `[retry] Attempt ${attempt}/${maxAttempts} failed: ${err.message}. Retrying in ${Math.round(totalDelay)}ms`
      );
      await new Promise(r => setTimeout(r, totalDelay));
    }
  }

  throw lastError;
}

// ─── Singleton Circuits ─────────────────────────────────────────────────

const agentServiceCircuit = new CircuitBreaker({
  name: 'agent-service',
  failureThreshold: 3,
  recoveryTimeoutMs: 60_000,
});

module.exports = {
  CircuitBreaker,
  retryWithBackoff,
  agentServiceCircuit,
};
