package polydetector.adapters;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Types;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import polydetector.domain.entities.PriceChange;
import polydetector.domain.entities.Spike;
import polydetector.domain.entities.WsEvent;
import polydetector.domain.usecases.ports.EventSinkPort;

/**
 * Queues events in memory and writes them in batches on its own thread, so the WebSocket thread never
 * waits for the database. If the DB is down, batches are retried and the queue buffers; only when the
 * queue is full are events dropped (counted and logged).
 *
 * <p>{@code price_change} events (99.7 % of the feed) are split into typed rows in {@code price_changes}.
 * Everything else, and any price_change that cannot be split, is stored raw in {@code ws_events}.
 */
public final class PostgresEventSink implements EventSinkPort, AutoCloseable {
    private static final Logger logger = LoggerFactory.getLogger(PostgresEventSink.class);
    private static final int BATCH_SIZE = 1000;
    private static final String PRICE_CHANGE = "price_change";
    private static final String INSERT_EVENT = "INSERT INTO ws_events "
            + "(time, received_at, event_type, market, asset_id, payload) VALUES (?, ?, ?, ?, ?, ?::jsonb)";
    private static final String INSERT_PRICE_CHANGE = "INSERT INTO price_changes "
            + "(time, received_at, market, asset_id, price, size, side, best_bid, best_ask) "
            + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
    private static final String INSERT_SPIKE = "INSERT INTO spikes "
            + "(time, asset_id, market, window_notional, baseline_notional) VALUES (?, ?, ?, ?, ?)";

    private final String url;
    private final String user;
    private final String password;
    private final BlockingQueue<Object> queue;
    private final AtomicLong dropped = new AtomicLong();
    private final AtomicLong unparsable = new AtomicLong();
    private final Thread writer;
    private volatile boolean running = true;
    private Connection connection;

    public PostgresEventSink(String url, String user, String password, int capacity) {
        this.url = url;
        this.user = user;
        this.password = password;
        this.queue = new ArrayBlockingQueue<>(capacity);
        this.writer = new Thread(this::run, "db-writer");
        writer.setDaemon(true);
        writer.start();
    }

    @Override
    public void write(WsEvent event) {
        offer(event);
    }

    @Override
    public void writeSpike(Spike spike) {
        offer(spike);
    }

    public long droppedCount() {
        return dropped.get();
    }

    private void offer(Object item) {
        if (!queue.offer(item)) {
            long n = dropped.incrementAndGet();
            if (n % 1000 == 1) {
                logger.warn("DB queue full, dropped {} events so far", n);
            }
        }
    }

    private void run() {
        List<Object> batch = new ArrayList<>(BATCH_SIZE);
        while (running || !queue.isEmpty() || !batch.isEmpty()) {
            try {
                if (batch.isEmpty()) {
                    Object first = queue.poll(1, TimeUnit.SECONDS);
                    if (first == null) {
                        continue;
                    }
                    batch.add(first);
                    queue.drainTo(batch, BATCH_SIZE - 1);
                }
                writeBatch(batch);
                batch.clear();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (RuntimeException e) {
                // Unexpected bug in one batch: drop it rather than let the writer thread die silently.
                closeConnection();
                logger.error("Dropping batch of {} after unexpected error", batch.size(), e);
                batch.clear();
            } catch (SQLException e) {
                closeConnection();
                String state = e.getSQLState();
                if (state != null && (state.startsWith("22") || state.startsWith("23"))) {
                    // Data or constraint error: retrying the same batch would block the queue forever.
                    logger.error("Dropping batch of {} with invalid data: {}", batch.size(), e.getMessage());
                    batch.clear();
                } else {
                    logger.error("DB write failed, retrying batch of {}: {}", batch.size(), e.getMessage());
                    sleepQuietly();
                }
            }
        }
        closeConnection();
    }

    private void writeBatch(List<Object> batch) throws SQLException {
        if (connection == null) {
            connection = DriverManager.getConnection(url, user, password);
            connection.setAutoCommit(false);
        }
        try (PreparedStatement events = connection.prepareStatement(INSERT_EVENT);
             PreparedStatement changes = connection.prepareStatement(INSERT_PRICE_CHANGE);
             PreparedStatement spikes = connection.prepareStatement(INSERT_SPIKE)) {
            for (Object item : batch) {
                if (item instanceof WsEvent e) {
                    List<PriceChange> rows = PRICE_CHANGE.equals(e.eventType()) ? split(e) : List.of();
                    if (rows.isEmpty()) {
                        addRaw(events, e);
                    } else {
                        for (PriceChange row : rows) {
                            addChange(changes, row);
                        }
                    }
                } else if (item instanceof Spike s) {
                    spikes.setObject(1, utc(s.time()));
                    spikes.setString(2, s.assetId());
                    spikes.setString(3, s.market());
                    spikes.setDouble(4, s.windowNotional());
                    spikes.setDouble(5, s.baselineNotional());
                    spikes.addBatch();
                }
            }
            events.executeBatch();
            changes.executeBatch();
            spikes.executeBatch();
            connection.commit();
        }
    }

    /** Typed rows for a price_change event, or none if it is malformed (it is then kept raw, not lost). */
    private List<PriceChange> split(WsEvent event) {
        try {
            return PriceChangeParser.parse(event);
        } catch (RuntimeException e) {
            long n = unparsable.incrementAndGet();
            if (n % 1000 == 1) {
                logger.warn("price_change not split, stored raw ({} so far): {}", n, e.toString());
            }
            return List.of();
        }
    }

    private static void addRaw(PreparedStatement events, WsEvent e) throws SQLException {
        events.setObject(1, utc(e.time()));
        events.setObject(2, utc(e.receivedAt()));
        events.setString(3, e.eventType());
        events.setString(4, e.market());
        events.setString(5, e.assetId());
        events.setString(6, e.payload());
        events.addBatch();
    }

    private static void addChange(PreparedStatement changes, PriceChange c) throws SQLException {
        changes.setObject(1, utc(c.time()));
        changes.setObject(2, utc(c.receivedAt()));
        changes.setString(3, c.market());
        changes.setString(4, c.assetId());
        changes.setDouble(5, c.price());
        changes.setDouble(6, c.size());
        changes.setString(7, c.side());
        setNullableDouble(changes, 8, c.bestBid());
        setNullableDouble(changes, 9, c.bestAsk());
        changes.addBatch();
    }

    private static void setNullableDouble(PreparedStatement ps, int index, Double value) throws SQLException {
        if (value == null) {
            ps.setNull(index, Types.DOUBLE);
        } else {
            ps.setDouble(index, value);
        }
    }

    private static OffsetDateTime utc(Instant t) {
        return OffsetDateTime.ofInstant(t, ZoneOffset.UTC);
    }

    private void closeConnection() {
        if (connection != null) {
            try {
                connection.close();
            } catch (SQLException ignored) {
                // already broken; a new one is opened on the next batch
            }
            connection = null;
        }
    }

    private static void sleepQuietly() {
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    /** Flushes what is queued, waiting at most 10 s (the DB may be down at shutdown). */
    @Override
    public void close() throws InterruptedException {
        running = false;
        writer.join(10_000);
    }
}
