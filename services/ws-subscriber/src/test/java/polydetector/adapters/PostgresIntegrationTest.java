package polydetector.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.awaitility.Awaitility;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;
import polydetector.domain.entities.Spike;
import polydetector.domain.entities.WsEvent;

/** Runs against TimescaleDB with the real schema from db/init. */
@Testcontainers
class PostgresIntegrationTest {

    @Container
    static final PostgreSQLContainer<?> DB = new PostgreSQLContainer<>(
            DockerImageName.parse("docker.io/timescale/timescaledb:2.26.1-pg16").asCompatibleSubstituteFor("postgres"))
            .withCopyFileToContainer(MountableFile.forHostPath("../../db/init/001_schema.sql"),
                    "/docker-entrypoint-initdb.d/001_schema.sql");

    private static long count(String sql) throws SQLException {
        try (Connection c = DriverManager.getConnection(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword());
             Statement s = c.createStatement(); ResultSet rs = s.executeQuery(sql)) {
            rs.next();
            return rs.getLong(1);
        }
    }

    @Test
    void sinkWritesEventsAndSpikesInBackground() throws Exception {
        Instant t = Instant.parse("2026-11-10T12:00:00Z");
        try (var sink = new PostgresEventSink(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword(), 100)) {
            sink.write(new WsEvent(t, t, "last_trade_price", "0xm", "1", 70, "{\"price\":\"0.07\"}"));
            sink.write(new WsEvent(t, t, "book", "0xm", "1", 0, "{\"bids\":[]}"));
            sink.writeSpike(new Spike(t, "1", "0xm", 5000, 500));
        }
        assertEquals(2, count("SELECT count(*) FROM ws_events"));
        assertEquals(1, count("SELECT count(*) FROM spikes"));
        assertEquals(1, count("SELECT count(*) FROM ws_events WHERE payload->>'price' = '0.07'"));
    }

    @Test
    void sinkSplitsPriceChangesIntoTypedRowsAndKeepsMalformedOnesRaw() throws Exception {
        Instant t = Instant.parse("2026-11-10T13:00:00Z");
        String live = "{\"market\":\"0xpc\",\"price_changes\":["
                + "{\"asset_id\":\"a1\",\"price\":\"0.148\",\"size\":\"700\",\"side\":\"BUY\","
                + "\"best_bid\":\"0.162\",\"best_ask\":\"0.166\"},"
                + "{\"asset_id\":\"a2\",\"price\":\"0.852\",\"size\":\"0\",\"side\":\"SELL\"}]}";
        String broken = "{\"market\":\"0xbroken\",\"price_changes\":[{\"asset_id\":\"a3\",\"price\":\"x\"}]}";
        try (var sink = new PostgresEventSink(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword(), 100)) {
            sink.write(new WsEvent(t, t, "price_change", "0xpc", null, 0, live));
            sink.write(new WsEvent(t, t, "price_change", "0xbroken", null, 0, broken));
        }
        assertEquals(2, count("SELECT count(*) FROM price_changes WHERE market = '0xpc'"));
        assertEquals(1, count("SELECT count(*) FROM price_changes WHERE asset_id = 'a1' AND price = 0.148 "
                + "AND size = 700 AND side = 'BUY' AND best_bid = 0.162 AND best_ask = 0.166"));
        assertEquals(1, count("SELECT count(*) FROM price_changes WHERE asset_id = 'a2' AND best_bid IS NULL"));
        assertEquals(0, count("SELECT count(*) FROM ws_events WHERE market = '0xpc'"));
        assertEquals(1, count("SELECT count(*) FROM ws_events WHERE market = '0xbroken' "
                + "AND event_type = 'price_change'"));
    }

    @Test
    void sinkDropsWhenQueueIsFullInsteadOfBlocking() throws Exception {
        Instant t = Instant.now();
        // Wrong password: every write fails, the queue (capacity 1) fills and the rest is dropped.
        try (var sink = new PostgresEventSink(DB.getJdbcUrl(), DB.getUsername(), "wrong", 1)) {
            for (int i = 0; i < 50; i++) {
                sink.write(new WsEvent(t, t, "book", "m", "a", 0, "{}"));
            }
            Awaitility.await().atMost(Duration.ofSeconds(5)).until(() -> sink.droppedCount() >= 45);
        }
    }

    @Test
    void assetSourceReturnsTokensClosingInsideWindowOrRecentlyEnded() throws Exception {
        try (Connection c = DriverManager.getConnection(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword());
             Statement s = c.createStatement()) {
            s.execute("INSERT INTO markets (condition_id, question, end_date, closed, outcomes, token_ids) VALUES "
                    + "('soon', 'q', now() + interval '2 hours', false, '{Yes,No}', '{t1,t2}'),"
                    + "('later', 'q', now() + interval '3 days', false, '{Yes,No}', '{t3,t4}'),"
                    + "('done', 'q', now() + interval '1 hour', true, '{Yes,No}', '{t5,t6}'),"
                    + "('ended', 'q', now() - interval '1 hour', false, '{Yes,No}', '{t7,t8}'),"
                    + "('long-gone', 'q', now() - interval '10 hours', false, '{Yes,No}', '{t9,t0}')");
        }
        var source = new PostgresAssetSource(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword(), 24, 6);
        assertEquals(List.of("t1", "t2", "t7", "t8"), source.activeAssetIds());
    }
}
