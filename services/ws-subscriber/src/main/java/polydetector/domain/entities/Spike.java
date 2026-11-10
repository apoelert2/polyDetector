package polydetector.domain.entities;

import java.time.Instant;

/** Traded notional in the recent window is far above the expected amount for one window. */
public record Spike(Instant time, String assetId, String market, double windowNotional, double baselineNotional) {
}
