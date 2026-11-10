package polydetector;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import polydetector.adapters.PolymarketWebSocketClient;
import polydetector.adapters.PostgresAssetSource;
import polydetector.adapters.PostgresEventSink;
import polydetector.domain.SpikeDetector;
import polydetector.domain.usecases.SubscribeToMarket;

/** Composition root. */
public final class Application {
    private static final Logger logger = LoggerFactory.getLogger(Application.class);
    private static final int QUEUE_CAPACITY = 200_000;

    private Application() {
    }

    public static void main(String[] args) throws InterruptedException {
        Config config = Config.fromEnv(System.getenv());
        logger.info("Starting ws-subscriber: {}", config);

        var sink = new PostgresEventSink(config.dbUrl(), config.dbUser(), config.dbPassword(), QUEUE_CAPACITY);
        var useCase = new SubscribeToMarket(
                new PolymarketWebSocketClient(config.wsUrl()),
                new PostgresAssetSource(config.dbUrl(), config.dbUser(), config.dbPassword(), config.windowHours(),
                        config.graceHours()),
                sink,
                new SpikeDetector(config.spikeWindowMinutes(), config.spikeHistoryMinutes(), config.spikeFactor(),
                        config.spikeMinNotional()));

        ScheduledExecutorService refresher = Executors.newSingleThreadScheduledExecutor();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutdown signal received");
            refresher.shutdownNow();
            useCase.stop();
            try {
                sink.close();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }));

        useCase.start();
        refresher.scheduleAtFixedRate(useCase::refreshAssets, config.assetRefreshSeconds(),
                config.assetRefreshSeconds(), TimeUnit.SECONDS);
        Thread.currentThread().join(); // all work runs on the WebSocket, scheduler and db-writer threads
    }
}
