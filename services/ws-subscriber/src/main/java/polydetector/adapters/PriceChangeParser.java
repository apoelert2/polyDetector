package polydetector.adapters;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import polydetector.domain.entities.PriceChange;
import polydetector.domain.entities.WsEvent;

/** Splits a raw {@code price_change} event into typed rows, one per changed asset. */
public final class PriceChangeParser {
    private PriceChangeParser() {
    }

    /**
     * Returns an empty list if the event holds no changes. Throws a RuntimeException if a required field
     * is missing or a number does not parse. The caller then keeps the raw event instead of losing it.
     */
    public static List<PriceChange> parse(WsEvent event) {
        Objects.requireNonNull(event.market(), "market");
        JsonElement changes = JsonParser.parseString(event.payload()).getAsJsonObject().get("price_changes");
        if (changes == null || !changes.isJsonArray()) {
            return List.of();
        }
        List<PriceChange> rows = new ArrayList<>();
        for (JsonElement element : changes.getAsJsonArray()) {
            JsonObject c = element.getAsJsonObject();
            rows.add(new PriceChange(event.time(), event.receivedAt(), event.market(),
                    c.get("asset_id").getAsString(), c.get("price").getAsDouble(), c.get("size").getAsDouble(),
                    c.get("side").getAsString(), optionalNumber(c, "best_bid"), optionalNumber(c, "best_ask")));
        }
        return rows;
    }

    private static Double optionalNumber(JsonObject o, String key) {
        JsonElement e = o.get(key);
        return e == null || e.isJsonNull() ? null : e.getAsDouble();
    }
}
