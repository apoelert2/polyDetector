package polydetector.domain.usecases;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import polydetector.domain.SpikeDetector;
import polydetector.domain.entities.Spike;
import polydetector.domain.entities.WsEvent;
import polydetector.domain.usecases.ports.AssetSourcePort;
import polydetector.domain.usecases.ports.EventSinkPort;
import polydetector.domain.usecases.ports.WebSocketPort;

@ExtendWith(MockitoExtension.class)
class SubscribeToMarketTest {
    private static final Instant T = Instant.parse("2026-11-10T12:00:00Z");

    @Mock
    private WebSocketPort webSocket;
    @Mock
    private AssetSourcePort assets;
    @Mock
    private EventSinkPort sink;

    private SubscribeToMarket useCase;

    @BeforeEach
    void setUp() {
        useCase = new SubscribeToMarket(webSocket, assets, sink, new SpikeDetector(5, 60, 5, 1000));
    }

    private static WsEvent trade(double notional) {
        return new WsEvent(T, T, "last_trade_price", "m", "a", notional, "{}");
    }

    @Test
    void startSubscribesToActiveAssets() throws Exception {
        when(assets.activeAssetIds()).thenReturn(List.of("1", "2"));
        useCase.start();
        verify(webSocket).start(any());
        verify(webSocket).subscribe(List.of("1", "2"));
    }

    @Test
    void failingAssetSourceKeepsCurrentSubscription() throws Exception {
        when(assets.activeAssetIds()).thenThrow(new IllegalStateException("db down"));
        useCase.refreshAssets();
        verify(webSocket, never()).subscribe(any());
    }

    @Test
    void everyEventIsStored() {
        WsEvent book = new WsEvent(T, T, "book", "m", "a", 0, "{}");
        useCase.onEvent(book);
        verify(sink).write(book);
        verify(sink, never()).writeSpike(any());
    }

    @Test
    void bigTradeIsStoredAsSpike() {
        useCase.onEvent(new WsEvent(T.minusSeconds(3600), T, "book", "m", "a", 0, "{}")); // observed for 1 h
        WsEvent big = trade(5000);
        useCase.onEvent(big);
        verify(sink).writeSpike(any(Spike.class));
        verify(sink).write(big);
    }
}
