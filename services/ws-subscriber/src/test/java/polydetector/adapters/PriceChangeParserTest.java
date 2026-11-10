package polydetector.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import polydetector.domain.entities.PriceChange;
import polydetector.domain.entities.WsEvent;

/** Payload copied from the live market channel (shortened). */
class PriceChangeParserTest {
    private static final Instant T = Instant.parse("2026-11-10T12:00:00Z");
    private static final String LIVE = "{\"market\":\"0xa09e\",\"price_changes\":["
            + "{\"asset_id\":\"9230\",\"price\":\"0.148\",\"size\":\"700\",\"side\":\"BUY\",\"hash\":\"858a\","
            + "\"best_bid\":\"0.162\",\"best_ask\":\"0.166\"},"
            + "{\"asset_id\":\"5460\",\"price\":\"0.852\",\"size\":\"0\",\"side\":\"SELL\",\"hash\":\"b9eb\"}],"
            + "\"timestamp\":\"1794306526639\",\"event_type\":\"price_change\"}";

    private static WsEvent event(String market, String payload) {
        return new WsEvent(T, T, "price_change", market, null, 0, payload);
    }

    @Test
    void oneRowPerChangedAssetWithTypedValues() {
        List<PriceChange> rows = PriceChangeParser.parse(event("0xa09e", LIVE));
        assertEquals(2, rows.size());
        PriceChange first = rows.get(0);
        assertEquals("0xa09e", first.market());
        assertEquals("9230", first.assetId());
        assertEquals(0.148, first.price(), 1e-12);
        assertEquals(700.0, first.size(), 1e-12);
        assertEquals("BUY", first.side());
        assertEquals(0.162, first.bestBid());
        assertEquals(0.166, first.bestAsk());
        assertEquals(T, first.time());
    }

    @Test
    void missingBestBidAndAskBecomeNull() {
        PriceChange second = PriceChangeParser.parse(event("0xa09e", LIVE)).get(1);
        assertNull(second.bestBid());
        assertNull(second.bestAsk());
        assertEquals(0.0, second.size());
    }

    @Test
    void eventWithoutChangesGivesNoRows() {
        assertTrue(PriceChangeParser.parse(event("0xa09e", "{\"event_type\":\"price_change\"}")).isEmpty());
    }

    @Test
    void malformedEventsThrowSoTheyCanBeKeptRaw() {
        assertThrows(RuntimeException.class, () -> PriceChangeParser.parse(event("0xa09e",
                "{\"price_changes\":[{\"asset_id\":\"1\",\"price\":\"abc\",\"size\":\"1\",\"side\":\"BUY\"}]}")));
        assertThrows(RuntimeException.class, () -> PriceChangeParser.parse(event("0xa09e",
                "{\"price_changes\":[{\"asset_id\":\"1\",\"size\":\"1\",\"side\":\"BUY\"}]}")));
        assertThrows(RuntimeException.class, () -> PriceChangeParser.parse(event(null, LIVE)));
    }
}
