package polydetector.adapters;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import polydetector.domain.usecases.ports.AssetSourcePort;

/** Reads token ids from the markets table, which the poller keeps up to date. */
public final class PostgresAssetSource implements AssetSourcePort {
    private static final String QUERY = "SELECT DISTINCT unnest(token_ids) AS id FROM markets "
            + "WHERE NOT closed AND end_date BETWEEN now() AND now() + ? * interval '1 hour' ORDER BY id";

    private final String url;
    private final String user;
    private final String password;
    private final double windowHours;

    public PostgresAssetSource(String url, String user, String password, double windowHours) {
        this.url = url;
        this.user = user;
        this.password = password;
        this.windowHours = windowHours;
    }

    @Override
    public List<String> activeAssetIds() throws SQLException {
        try (Connection c = DriverManager.getConnection(url, user, password);
             PreparedStatement ps = c.prepareStatement(QUERY)) {
            ps.setDouble(1, windowHours);
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
