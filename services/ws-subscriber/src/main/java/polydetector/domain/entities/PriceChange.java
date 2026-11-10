package polydetector.domain.entities;

import java.time.Instant;

/**
 * One order-book change of one asset (a {@code price_change} event holds one or more of these).
 *
 * @param bestBid best buy price after the change, null if the feed did not send it
 * @param bestAsk best sell price after the change, null if the feed did not send it
 */
public record PriceChange(
        Instant time,
        Instant receivedAt,
        String market,
        String assetId,
        double price,
        double size,
        String side,
        Double bestBid,
        Double bestAsk) {
}
