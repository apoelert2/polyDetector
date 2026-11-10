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
            DockerImageName.parse("docker.io/timescale/timescaledb:latest-pg16").asCompatibleSubstituteFor("postgres"))
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
    void assetSourceReturnsOnlyTokensClosingInsideWindow() throws Exception {
        try (Connection c = DriverManager.getConnection(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword());
             Statement s = c.createStatement()) {
            s.execute("INSERT INTO markets (condition_id, question, end_date, closed, outcomes, token_ids) VALUES "
                    + "('soon', 'q', now() + interval '2 hours', false, '{Yes,No}', '{t1,t2}'),"
                    + "('later', 'q', now() + interval '3 days', false, '{Yes,No}', '{t3,t4}'),"
                    + "('done', 'q', now() + interval '1 hour', true, '{Yes,No}', '{t5,t6}')");
        }
        var source = new PostgresAssetSource(DB.getJdbcUrl(), DB.getUsername(), DB.getPassword(), 24);
        assertEquals(List.of("t1", "t2"), source.activeAssetIds());
    }
}
