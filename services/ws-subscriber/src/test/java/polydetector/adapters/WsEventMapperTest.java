package polydetector.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonSyntaxException;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import polydetector.domain.entities.WsEvent;

/** Payloads copied from the live market channel (shortened). */
class WsEventMapperTest {
    private static final Instant NOW = Instant.parse("2026-11-10T12:00:00Z");

    @Test
    void lastTradePriceCarriesNotionalAndEventTime() {
        String json = "{\"market\":\"0x7238\",\"asset_id\":\"4286\",\"price\":\"0.07\",\"size\":\"1000\","
                + "\"fee_rate_bps\":\"0\",\"side\":\"BUY\",\"timestamp\":\"1794306552690\","
                + "\"event_type\":\"last_trade_price\",\"transaction_hash\":\"0x75a5\"}";
        WsEvent e = WsEventMapper.fromJson(json, NOW).get(0);
        assertEquals("last_trade_price", e.eventType());
        assertEquals("0x7238", e.market());
        assertEquals("4286", e.assetId());
        assertEquals(70.0, e.tradeNotional(), 1e-9);
        assertEquals(Instant.ofEpochMilli(1794306552690L), e.time());
        assertEquals(NOW, e.receivedAt());
        assertTrue(e.payload().contains("\"transaction_hash\":\"0x75a5\""));
    }

    @Test
    void priceChangeHasNoAssetAndNoNotional() {
        String json = "{\"market\":\"0xa09e\",\"price_changes\":[{\"asset_id\":\"9230\",\"price\":\"0.148\"}],"
                + "\"timestamp\":\"1794306526639\",\"event_type\":\"price_change\"}";
        WsEvent e = WsEventMapper.fromJson(json, NOW).get(0);
        assertNull(e.assetId());
        assertEquals(0.0, e.tradeNotional());
    }

    @Test
    void arrayOfBookEventsGivesOneEventEach() {
        String json = "[{\"event_type\":\"book\",\"asset_id\":\"1\",\"timestamp\":\"1\",\"bids\":[]},"
                + "{\"event_type\":\"book\",\"asset_id\":\"2\",\"timestamp\":\"2\",\"bids\":[]}]";
        List<WsEvent> events = WsEventMapper.fromJson(json, NOW);
        assertEquals(2, events.size());
    }

    @Test
    void objectsWithoutEventTypeAreSkipped() {
        assertTrue(WsEventMapper.fromJson("[{\"foo\":1}, 3]", NOW).isEmpty());
    }

    @Test
    void invalidJsonThrows() {
        assertThrows(JsonSyntaxException.class, () -> WsEventMapper.fromJson("{invalid", NOW));
    }
}
