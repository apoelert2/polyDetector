package polydetector.adapters;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import polydetector.domain.entities.WsEvent;
import polydetector.domain.usecases.ports.WebSocketPort;

/**
 * Market channel client. Reconnects through exactly one path (onClose -> scheduleReconnect), so a long
 * outage never stacks up parallel connections.
 */
public final class PolymarketWebSocketClient implements WebSocketPort {
    private static final Logger logger = LoggerFactory.getLogger(PolymarketWebSocketClient.class);
    private static final long RECONNECT_DELAY_SEC = 5;
    private static final long PING_INTERVAL_SEC = 10; // Polymarket expects a text PING about every 10 s

    private final URI uri;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "ws-scheduler");
        t.setDaemon(true);
        return t;
    });
    private final AtomicBoolean reconnectPending = new AtomicBoolean();
    private volatile List<String> assetIds = List.of();
    private volatile EventHandler handler;
    private volatile WebSocketClient client;
    private volatile boolean running;

    public PolymarketWebSocketClient(String wsUrl) {
        this.uri = URI.create(wsUrl);
    }

    @Override
    public void start(EventHandler eventHandler) {
        this.handler = eventHandler;
        running = true;
        scheduler.scheduleAtFixedRate(this::ping, PING_INTERVAL_SEC, PING_INTERVAL_SEC, TimeUnit.SECONDS);
    }

    @Override
    public void subscribe(List<String> ids) {
        List<String> next = List.copyOf(ids);
        List<String> previous = assetIds;
        if (next.equals(previous)) {
            return;
        }
        assetIds = next;
        logger.info("Subscription changed: {} assets", next.size());
        WebSocketClient current = client;
        if (next.isEmpty()) {
            if (current != null) {
                current.close(); // onClose does not reconnect while the set is empty
            }
        } else if (current != null && current.isOpen()) {
            // Change the subscription on the open connection: no reconnect, no blind gap.
            updateMessages(previous, next).forEach(current::send);
        } else if (current == null || current.isClosed()) {
            scheduleReconnect(0);
        }
        // else: still connecting; onOpen subscribes to the current set.
    }

    /** Subscribe/unsubscribe messages that turn {@code previous} into {@code next}. */
    static List<String> updateMessages(List<String> previous, List<String> next) {
        Set<String> before = new HashSet<>(previous);
        Set<String> after = new HashSet<>(next);
        List<String> added = next.stream().filter(id -> !before.contains(id)).toList();
        List<String> removed = previous.stream().filter(id -> !after.contains(id)).toList();
        List<String> messages = new ArrayList<>();
        if (!added.isEmpty()) {
            messages.add(message(added, "operation", "subscribe"));
        }
        if (!removed.isEmpty()) {
            messages.add(message(removed, "operation", "unsubscribe"));
        }
        return messages;
    }

    private static String message(List<String> ids, String key, String value) {
        JsonArray array = new JsonArray();
        ids.forEach(array::add);
        JsonObject msg = new JsonObject();
        msg.add("assets_ids", array);
        msg.addProperty(key, value);
        return msg.toString();
    }

    @Override
    public void stop() {
        running = false;
        scheduler.shutdownNow();
        WebSocketClient current = client;
        if (current != null) {
            current.close();
        }
    }

    private void ping() {
        WebSocketClient current = client;
        if (current != null && current.isOpen()) {
            current.send("PING");
        }
    }

    private void scheduleReconnect(long delaySec) {
        if (!running || assetIds.isEmpty() || !reconnectPending.compareAndSet(false, true)) {
            return;
        }
        scheduler.schedule(() -> {
            reconnectPending.set(false);
            if (running && !assetIds.isEmpty()) {
                client = newClient();
                client.connect();
            }
        }, delaySec, TimeUnit.SECONDS);
    }

    private void sendSubscription(WebSocketClient ws) {
        List<String> ids = assetIds;
        ws.send(message(ids, "type", "market"));
        logger.info("Subscribed to {} assets", ids.size());
    }

    private WebSocketClient newClient() {
        return new WebSocketClient(uri) {
            @Override
            public void onOpen(ServerHandshake handshake) {
                logger.info("WebSocket connected");
                sendSubscription(this);
            }

            @Override
            public void onMessage(String raw) {
                if ("PONG".equals(raw)) {
                    return;
                }
                try {
                    for (WsEvent event : WsEventMapper.fromJson(raw, Instant.now())) {
                        handler.onEvent(event);
                    }
                } catch (RuntimeException e) {
                    logger.error("Failed to handle ws message: {}", e.getMessage());
                }
            }

            @Override
            public void onClose(int code, String reason, boolean remote) {
                logger.warn("WebSocket closed: code={}, reason={}, remote={}", code, reason, remote);
                scheduleReconnect(RECONNECT_DELAY_SEC);
            }

            @Override
            public void onError(Exception ex) {
                logger.error("WebSocket error: {}", ex.getMessage());
            }
        };
    }
}
