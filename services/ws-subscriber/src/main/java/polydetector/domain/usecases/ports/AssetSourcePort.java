package polydetector.domain.usecases.ports;

import java.util.List;

/** Token ids of the markets that close within the watch window. */
public interface AssetSourcePort {
    List<String> activeAssetIds() throws Exception;
}
