/**
 * Retry utility for handling API rate limiting and transient failures.
 * 
 * Implements exponential backoff with jitter for optimal retry behavior.
 */

import { AxiosError, AxiosResponse } from 'axios';

interface RetryOptions {
  maxAttempts?: number;
  initialDelay?: number;
  maxDelay?: number;
  factor?: number;
  jitter?: boolean;
  retryCondition?: (error: AxiosError) => boolean;
  onRetry?: (error: AxiosError, attempt: number) => void;
}

const DEFAULT_OPTIONS: Required<RetryOptions> = {
  maxAttempts: 3,
  initialDelay: 1000,
  maxDelay: 30000,
  factor: 2,
  jitter: true,
  retryCondition: (error) => {
    // Retry on rate limit (429) or server errors (5xx)
    if (!error.response) return true; // Network errors
    const status = error.response.status;
    return status === 429 || (status >= 500 && status < 600);
  },
  onRetry: (error, attempt) => {
    console.log(`[Retry] Attempt ${attempt} after error:`, error.message);
  },
};

/**
 * Calculate delay with exponential backoff and optional jitter
 */
function calculateDelay(
  attempt: number,
  initialDelay: number,
  factor: number,
  maxDelay: number,
  jitter: boolean
): number {
  // Exponential backoff: delay = initialDelay * (factor ^ attempt)
  const exponentialDelay = initialDelay * Math.pow(factor, attempt - 1);
  const delay = Math.min(exponentialDelay, maxDelay);

  if (jitter) {
    // Add random jitter (±25% of delay)
    const jitterRange = delay * 0.25;
    const jitterValue = Math.random() * jitterRange * 2 - jitterRange;
    return Math.max(0, delay + jitterValue);
  }

  return delay;
}

/**
 * Extract retry delay from rate limit headers
 */
function getRetryAfterDelay(response: AxiosResponse): number | null {
  const retryAfter = response.headers['retry-after'];
  if (!retryAfter) return null;

  // If it's a number, it's delay in seconds
  const seconds = parseInt(retryAfter, 10);
  if (!isNaN(seconds)) {
    return seconds * 1000; // Convert to milliseconds
  }

  // If it's a date, calculate delay
  const retryDate = new Date(retryAfter);
  if (!isNaN(retryDate.getTime())) {
    const delay = retryDate.getTime() - Date.now();
    return delay > 0 ? delay : null;
  }

  return null;
}

/**
 * Sleep for the specified duration
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry a function with exponential backoff
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  options?: RetryOptions
): Promise<T> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= opts.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      // Check if this is an Axios error
      if (error instanceof Error && 'isAxiosError' in error) {
        const axiosError = error as AxiosError;

        // Check if we should retry
        if (!opts.retryCondition(axiosError)) {
          throw error;
        }

        // Last attempt, throw the error
        if (attempt === opts.maxAttempts) {
          throw error;
        }

        // Call retry callback
        opts.onRetry(axiosError, attempt);

        // Calculate delay
        let delay = calculateDelay(
          attempt,
          opts.initialDelay,
          opts.factor,
          opts.maxDelay,
          opts.jitter
        );

        // Use Retry-After header if available (for 429 responses)
        if (axiosError.response?.status === 429) {
          const retryAfterDelay = getRetryAfterDelay(axiosError.response);
          if (retryAfterDelay !== null) {
            delay = retryAfterDelay;
          }
        }

        // Wait before retrying
        await sleep(delay);
      } else {
        // Not an Axios error, don't retry
        throw error;
      }
    }
  }

  // Should never reach here, but TypeScript needs this
  throw lastError || new Error('Retry failed');
}

/**
 * Create an Axios interceptor for automatic retries
 */
export function createRetryInterceptor(options?: RetryOptions) {
  return {
    fulfilled: (response: AxiosResponse) => response,
    rejected: async (error: AxiosError) => {
      const config = error.config;
      
      // Don't retry if no config or if already retried
      if (!config || (config as any).__retryCount >= (options?.maxAttempts || DEFAULT_OPTIONS.maxAttempts)) {
        return Promise.reject(error);
      }

      // Initialize retry count
      (config as any).__retryCount = (config as any).__retryCount || 0;
      (config as any).__retryCount++;

      // Apply retry logic
      const opts = { ...DEFAULT_OPTIONS, ...options };
      
      // Check retry condition
      if (!opts.retryCondition(error)) {
        return Promise.reject(error);
      }

      // Call retry callback
      opts.onRetry(error, (config as any).__retryCount);

      // Calculate delay
      let delay = calculateDelay(
        (config as any).__retryCount,
        opts.initialDelay,
        opts.factor,
        opts.maxDelay,
        opts.jitter
      );

      // Use Retry-After header if available
      if (error.response?.status === 429) {
        const retryAfterDelay = getRetryAfterDelay(error.response);
        if (retryAfterDelay !== null) {
          delay = retryAfterDelay;
        }
      }

      // Wait and retry
      await sleep(delay);
      
      // Retry the request
      return error.config ? axios.request(error.config) : Promise.reject(error);
    },
  };
}

// Rate limit tracking for client-side throttling
interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: Date;
}

class RateLimitTracker {
  private limits: Map<string, RateLimitInfo> = new Map();

  updateFromResponse(endpoint: string, response: AxiosResponse): void {
    const limit = parseInt(response.headers['x-ratelimit-limit'] || '0', 10);
    const remaining = parseInt(response.headers['x-ratelimit-remaining'] || '0', 10);
    const reset = parseInt(response.headers['x-ratelimit-reset'] || '0', 10);

    if (limit > 0) {
      this.limits.set(endpoint, {
        limit,
        remaining,
        reset: new Date(reset * 1000),
      });
    }
  }

  shouldThrottle(endpoint: string): boolean {
    const info = this.limits.get(endpoint);
    if (!info) return false;

    // If we're at 20% or less of our limit, start throttling
    return info.remaining <= info.limit * 0.2;
  }

  getThrottleDelay(endpoint: string): number {
    const info = this.limits.get(endpoint);
    if (!info || info.remaining > 0) return 0;

    // Calculate time until reset
    const now = new Date();
    const resetTime = info.reset.getTime() - now.getTime();
    
    // Add some buffer
    return Math.max(0, resetTime + 1000);
  }
}

export const rateLimitTracker = new RateLimitTracker();

// Import axios at the end to avoid circular dependency
import axios from 'axios';