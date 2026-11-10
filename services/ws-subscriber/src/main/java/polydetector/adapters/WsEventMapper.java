package polydetector.adapters;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import polydetector.domain.entities.WsEvent;

/** Maps market-channel JSON (one object or an array of objects) to events. */
public final class WsEventMapper {
    static final String LAST_TRADE_PRICE = "last_trade_price";

    private WsEventMapper() {
    }

    public static List<WsEvent> fromJson(String rawJson, Instant receivedAt) {
        JsonElement root = JsonParser.parseString(rawJson);
        Iterable<JsonElement> items = root.isJsonArray() ? root.getAsJsonArray() : List.of(root);
        List<WsEvent> events = new ArrayList<>();
        for (JsonElement item : items) {
            if (!item.isJsonObject()) {
                continue;
            }
            JsonObject o = item.getAsJsonObject();
            String type = text(o, "event_type");
            if (type == null) {
                continue;
            }
            String ts = text(o, "timestamp");
            Instant time = ts == null ? receivedAt : Instant.ofEpochMilli(Long.parseLong(ts));
            double notional = LAST_TRADE_PRICE.equals(type) ? number(o, "price") * number(o, "size") : 0;
            events.add(new WsEvent(time, receivedAt, type, text(o, "market"), text(o, "asset_id"), notional,
                    o.toString()));
        }
        return events;
    }

    private static String text(JsonObject o, String key) {
        JsonElement e = o.get(key);
        return e == null || e.isJsonNull() ? null : e.getAsString();
    }

    private static double number(JsonObject o, String key) {
        String s = text(o, key);
        return s == null ? 0 : Double.parseDouble(s);
    }
}
