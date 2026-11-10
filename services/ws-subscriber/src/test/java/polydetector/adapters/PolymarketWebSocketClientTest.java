package polydetector.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class PolymarketWebSocketClientTest {

    @Test
    void updateSubscribesAddedAndUnsubscribesRemoved() {
        List<String> messages = PolymarketWebSocketClient.updateMessages(List.of("a", "b"), List.of("b", "c"));
        assertEquals(List.of(
                "{\"assets_ids\":[\"c\"],\"operation\":\"subscribe\"}",
                "{\"assets_ids\":[\"a\"],\"operation\":\"unsubscribe\"}"), messages);
    }

    @Test
    void reorderedSameSetSendsNothing() {
        assertTrue(PolymarketWebSocketClient.updateMessages(List.of("a", "b"), List.of("b", "a")).isEmpty());
    }
}
