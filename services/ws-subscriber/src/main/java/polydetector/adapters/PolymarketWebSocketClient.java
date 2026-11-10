package polydetector.adapters;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.net.URI;
import java.time.Instant;
import java.util.List;
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
        if (next.equals(assetIds)) {
            return;
        }
        assetIds = next;
        logger.info("Subscription changed: {} assets", next.size());
        WebSocketClient current = client;
        if (current == null) {
            scheduleReconnect(0);
        } else {
            current.close(); // onClose reconnects with the new set, or stays closed if it is empty
        }
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
        JsonArray ids = new JsonArray();
        assetIds.forEach(ids::add);
        JsonObject msg = new JsonObject();
        msg.add("assets_ids", ids);
        msg.addProperty("type", "market");
        ws.send(msg.toString());
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
