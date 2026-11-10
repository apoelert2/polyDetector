package polydetector.domain;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import polydetector.domain.entities.Spike;

class SpikeDetectorTest {
    private static final Instant T0 = Instant.parse("2026-11-10T12:00:00Z");

    private static Instant minute(int m) {
        return T0.plusSeconds(60L * m);
    }

    /** window 5 min, history 60 min, 5x, at least 1000 notional. */
    private final SpikeDetector detector = new SpikeDetector(5, 60, 5, 1000);

    private void steadyTrading(String asset, int fromMinute, int toMinute, double perMinute) {
        for (int m = fromMinute; m <= toMinute; m++) {
            assertFalse(detector.observe(asset, "m", perMinute, minute(m)).isPresent(), "no spike at minute " + m);
        }
    }

    @Test
    void steadyVolumeIsNoSpike() {
        steadyTrading("a", 0, 180, 500);
    }

    @Test
    void burstAboveFactorAndMinimumIsSpike() {
        steadyTrading("a", 0, 59, 100); // baseline 500 per 5-minute window
        Optional<Spike> spike = detector.observe("a", "m", 3000, minute(60));
        assertTrue(spike.isPresent());
        assertEquals(3400, spike.get().windowNotional(), 1e-9); // minutes 56..59 (4 x 100) + 3000
        assertEquals(500, spike.get().baselineNotional(), 1e-9);
    }

    @Test
    void burstBelowMinimumNotionalIsNoSpike() {
        steadyTrading("a", 0, 59, 1);
        assertFalse(detector.observe("a", "m", 900, minute(60)).isPresent());
    }

    @Test
    void cooldownGivesOneAlertPerWindow() {
        steadyTrading("a", 0, 59, 100);
        assertTrue(detector.observe("a", "m", 5000, minute(60)).isPresent());
        assertFalse(detector.observe("a", "m", 5000, minute(61)).isPresent());
        assertFalse(detector.observe("a", "m", 5000, minute(64)).isPresent());
    }

    @Test
    void noSpikeDuringWarmUpAfterStart() {
        assertFalse(detector.observe("a", "m", 0, minute(0)).isPresent());
        assertFalse(detector.observe("a", "m", 50_000, minute(30)).isPresent());
    }

    @Test
    void quietAssetWithSuddenBigTradeIsSpike() {
        detector.observe("a", "m", 0, minute(0)); // book event on subscribe starts the observation
        assertTrue(detector.observe("a", "m", 2000, minute(60)).isPresent());
    }

    @Test
    void assetsAreIndependent() {
        steadyTrading("a", 0, 59, 1000);
        detector.observe("b", "m", 0, minute(0));
        assertTrue(detector.observe("b", "m", 2000, minute(60)).isPresent());
        assertFalse(detector.observe("a", "m", 2000, minute(60)).isPresent());
    }

    @Test
    void lateEventOlderThanHistoryIsIgnored() {
        detector.observe("a", "m", 10, minute(0));
        detector.observe("a", "m", 10, minute(200));
        assertFalse(detector.observe("a", "m", 1_000_000, minute(100)).isPresent());
    }
}
