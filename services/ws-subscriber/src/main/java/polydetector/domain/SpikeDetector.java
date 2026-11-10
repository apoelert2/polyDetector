package polydetector.domain;

import java.time.Instant;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import polydetector.domain.entities.Spike;

/**
 * Finds volume spikes per asset with one-minute buckets.
 *
 * <p>Spike: notional of the last {@code windowMinutes} is at least {@code minNotional} and at least
 * {@code factor} times what the rest of the last {@code historyMinutes} traded per window.
 * Uses event time, not the wall clock, so the same code can replay stored events for backtests.
 */
public final class SpikeDetector {
    private final int windowMinutes;
    private final int historyMinutes;
    private final double factor;
    private final double minNotional;
    private final Map<String, AssetState> states = new HashMap<>();

    public SpikeDetector(int windowMinutes, int historyMinutes, double factor, double minNotional) {
        if (windowMinutes < 1 || historyMinutes <= windowMinutes) {
            throw new IllegalArgumentException("need 1 <= windowMinutes < historyMinutes");
        }
        this.windowMinutes = windowMinutes;
        this.historyMinutes = historyMinutes;
        this.factor = factor;
        this.minNotional = minNotional;
    }

    /**
     * Feed every event of an asset (notional 0 for non-trades). The first event starts the observation,
     * so a quiet asset counts as "observed with zero volume", not as "unknown".
     */
    public synchronized Optional<Spike> observe(String assetId, String market, double notional, Instant time) {
        long minute = time.getEpochSecond() / 60;
        AssetState state = states.computeIfAbsent(assetId, k -> new AssetState(historyMinutes, minute));
        if (!state.add(minute, notional) || minute < state.cooldownUntil) {
            return Optional.empty();
        }
        if (minute - state.firstMinute < historyMinutes - 1) {
            // Warm-up: without a full history the baseline is too low, and every asset would "spike" after a restart.
            return Optional.empty();
        }
        double window = state.sum(minute - windowMinutes + 1, minute);
        double history = state.sum(minute - historyMinutes + 1, minute - windowMinutes);
        double baseline = history * windowMinutes / (historyMinutes - windowMinutes);
        if (window >= minNotional && window >= factor * baseline) {
            state.cooldownUntil = minute + windowMinutes; // one alert per window, not one per trade
            return Optional.of(new Spike(time, assetId, market, window, baseline));
        }
        return Optional.empty();
    }

    /** Ring buffer of minute buckets. */
    private static final class AssetState {
        private final double[] notional;
        private final long[] bucketMinute;
        private final long firstMinute;
        private long latestMinute = Long.MIN_VALUE;
        private long cooldownUntil = Long.MIN_VALUE;

        AssetState(int size, long firstMinute) {
            this.firstMinute = firstMinute;
            notional = new double[size];
            bucketMinute = new long[size];
            Arrays.fill(bucketMinute, Long.MIN_VALUE);
        }

        /** Returns false for events older than the ring (late events must not overwrite newer buckets). */
        boolean add(long minute, double value) {
            if (latestMinute != Long.MIN_VALUE && minute <= latestMinute - notional.length) {
                return false;
            }
            int i = (int) Math.floorMod(minute, (long) notional.length);
            if (bucketMinute[i] != minute) {
                bucketMinute[i] = minute;
                notional[i] = 0;
            }
            notional[i] += value;
            latestMinute = Math.max(latestMinute, minute);
            return true;
        }

        double sum(long fromMinute, long toMinute) {
            double total = 0;
            for (long m = fromMinute; m <= toMinute; m++) {
                int i = (int) Math.floorMod(m, (long) notional.length);
                if (bucketMinute[i] == m) {
                    total += notional[i];
                }
            }
            return total;
        }
    }
}
