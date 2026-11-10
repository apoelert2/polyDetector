package polydetector.domain.usecases.ports;

import polydetector.domain.entities.Spike;
import polydetector.domain.entities.WsEvent;

/** Stores events. Must never block the caller: it runs on the WebSocket thread. */
public interface EventSinkPort {
    void write(WsEvent event);

    void writeSpike(Spike spike);
}
