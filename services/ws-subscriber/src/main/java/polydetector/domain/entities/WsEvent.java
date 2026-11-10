package polydetector.domain.entities;

import java.time.Instant;

/**
 * One event from the Polymarket market channel.
 *
 * @param time          event time from Polymarket
 * @param receivedAt    our clock when the message arrived
 * @param tradeNotional price * size for last_trade_price events, otherwise 0
 * @param payload       the raw event JSON
 */
public record WsEvent(
        Instant time,
        Instant receivedAt,
        String eventType,
        String market,
        String assetId,
        double tradeNotional,
        String payload) {
}
