package polydetector;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;

class ConfigTest {
    private static final String SECRET = "s3cr3t-value";

    @Test
    void passwordNeverInToString() {
        Config c = Config.fromEnv(Map.of("TIMESCALE_DB", "db", "TIMESCALE_USER", "u", "TIMESCALE_PASS", SECRET));
        assertEquals(SECRET, c.dbPassword());
        assertFalse(c.toString().contains(SECRET));
        assertTrue(c.toString().contains("dbPassword=***"));
    }

    @Test
    void missingPasswordFailsFast() {
        var e = assertThrows(IllegalStateException.class,
                () -> Config.fromEnv(Map.of("TIMESCALE_DB", "db", "TIMESCALE_USER", "u")));
        assertTrue(e.getMessage().contains("TIMESCALE_PASS"));
    }
}
