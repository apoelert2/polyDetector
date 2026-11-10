package polydetector.adapters;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import polydetector.domain.usecases.ports.AssetSourcePort;

/** Reads token ids from the markets table, which the poller keeps up to date. Same range as the poller. */
public final class PostgresAssetSource implements AssetSourcePort {
    private static final String QUERY = "SELECT DISTINCT unnest(token_ids) AS id FROM markets "
            + "WHERE NOT closed AND end_date BETWEEN now() - ? * interval '1 hour' AND now() + ? * interval '1 hour' "
            + "ORDER BY id";

    private final String url;
    private final String user;
    private final String password;
    private final double windowHours;
    private final double graceHours;

    public PostgresAssetSource(String url, String user, String password, double windowHours, double graceHours) {
        this.url = url;
        this.user = user;
        this.password = password;
        this.windowHours = windowHours;
        this.graceHours = graceHours;
    }

    @Override
    public List<String> activeAssetIds() throws SQLException {
        try (Connection c = DriverManager.getConnection(url, user, password);
             PreparedStatement ps = c.prepareStatement(QUERY)) {
            ps.setDouble(1, graceHours);
            ps.setDouble(2, windowHours);
            List<String> ids = new ArrayList<>();
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    ids.add(rs.getString(1));
                }
            }
            return ids;
        }
    }
}
