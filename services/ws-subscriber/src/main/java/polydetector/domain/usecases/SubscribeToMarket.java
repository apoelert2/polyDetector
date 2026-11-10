package polydetector.domain.usecases;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import polydetector.domain.SpikeDetector;
import polydetector.domain.entities.WsEvent;
import polydetector.domain.usecases.ports.AssetSourcePort;
import polydetector.domain.usecases.ports.EventSinkPort;
import polydetector.domain.usecases.ports.WebSocketPort;

public class SubscribeToMarket {
    private static final Logger logger = LoggerFactory.getLogger(SubscribeToMarket.class);

    private final WebSocketPort webSocket;
    private final AssetSourcePort assets;
    private final EventSinkPort sink;
    private final SpikeDetector detector;

    public SubscribeToMarket(WebSocketPort webSocket, AssetSourcePort assets, EventSinkPort sink,
                             SpikeDetector detector) {
        this.webSocket = webSocket;
        this.assets = assets;
        this.sink = sink;
        this.detector = detector;
    }

    public void start() {
        webSocket.start(this::onEvent);
        refreshAssets();
        logger.info("WebSocket subscriber started");
    }

    /** Called periodically: follows markets entering and leaving the watch window. */
    public void refreshAssets() {
        try {
            webSocket.subscribe(assets.activeAssetIds());
        } catch (Exception e) {
            logger.error("Failed to load active assets, keeping current subscription: {}", e.getMessage());
        }
    }

    void onEvent(WsEvent event) {
        // Detection first: it is the latency-critical part; storage is queued.
        if (event.assetId() != null) {
            detector.observe(event.assetId(), event.market(), event.tradeNotional(), event.time())
                    .ifPresent(spike -> {
                        logger.warn("SPIKE asset={} market={} window={} baseline={}", spike.assetId(),
                                spike.market(), spike.windowNotional(), spike.baselineNotional());
                        sink.writeSpike(spike);
                    });
        }
        sink.write(event);
    }

    public void stop() {
        webSocket.stop();
        logger.info("WebSocket subscriber stopped");
    }
}
