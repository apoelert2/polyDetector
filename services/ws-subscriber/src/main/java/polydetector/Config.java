package polydetector;

import java.util.Map;

/** Settings from the environment. The password never appears in toString (and so never in logs). */
public record Config(
        String wsUrl,
        String dbUrl,
        String dbUser,
        String dbPassword,
        double windowHours,
        double graceHours,
        int spikeWindowMinutes,
        int spikeHistoryMinutes,
        double spikeFactor,
        double spikeMinNotional,
        int assetRefreshSeconds) {

    public static Config fromEnv(Map<String, String> env) {
        String host = env.getOrDefault("TIMESCALE_HOST", "localhost");
        String port = env.getOrDefault("TIMESCALE_PORT", "5432");
        return new Config(
                env.getOrDefault("WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market"),
                "jdbc:postgresql://" + host + ":" + port + "/" + required(env, "TIMESCALE_DB"),
                required(env, "TIMESCALE_USER"),
                required(env, "TIMESCALE_PASS"),
                Double.parseDouble(env.getOrDefault("CLOSING_WINDOW_HOURS", "24")),
                Double.parseDouble(env.getOrDefault("CLOSING_GRACE_HOURS", "6")),
                Integer.parseInt(env.getOrDefault("SPIKE_WINDOW_MINUTES", "5")),
                Integer.parseInt(env.getOrDefault("SPIKE_HISTORY_MINUTES", "60")),
                Double.parseDouble(env.getOrDefault("SPIKE_FACTOR", "5")),
                Double.parseDouble(env.getOrDefault("SPIKE_MIN_NOTIONAL", "1000")),
                Integer.parseInt(env.getOrDefault("ASSET_REFRESH_SECONDS", "60")));
    }

    private static String required(Map<String, String> env, String key) {
        String value = env.get(key);
        if (value == null || value.isEmpty()) {
            throw new IllegalStateException("Environment variable " + key + " is not set");
        }
        return value;
    }

    @Override
    public String toString() {
        return "Config[wsUrl=" + wsUrl + ", dbUrl=" + dbUrl + ", dbUser=" + dbUser + ", dbPassword=***"
                + ", windowHours=" + windowHours + ", graceHours=" + graceHours
                + ", spikeWindowMinutes=" + spikeWindowMinutes
                + ", spikeHistoryMinutes=" + spikeHistoryMinutes + ", spikeFactor=" + spikeFactor
                + ", spikeMinNotional=" + spikeMinNotional + ", assetRefreshSeconds=" + assetRefreshSeconds + "]";
    }
}
