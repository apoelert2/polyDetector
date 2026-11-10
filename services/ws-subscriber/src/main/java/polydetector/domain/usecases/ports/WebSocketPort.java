package polydetector.domain.usecases.ports;

import java.util.List;
import polydetector.domain.entities.WsEvent;

public interface WebSocketPort {
    void start(EventHandler handler);

    /** Replaces the set of subscribed assets. An empty list disconnects. */
    void subscribe(List<String> assetIds);

    void stop();

    @FunctionalInterface
    interface EventHandler {
        void onEvent(WsEvent event);
    }
}
