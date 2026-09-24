"""Refresh incompatible imports retained by a running Streamlit process."""
import importlib
from threading import RLock

_lock = RLock()


def load_scan_service():
    with _lock:
        import discovery
        import indicators
        import markets
        import scan_service
        # Streamlit can rerun app.py while an older helper remains in sys.modules.
        # Refresh dependencies before rebinding the service's imported functions.
        if (getattr(discovery, 'MARKET_API_VERSION', None) != 1 or
                getattr(scan_service, 'SCAN_API_VERSION', None) != 2):
            importlib.invalidate_caches()
            for module in (discovery, indicators, markets, scan_service):
                importlib.reload(module)
        if (getattr(discovery, 'MARKET_API_VERSION', None) != 1 or
                getattr(scan_service, 'SCAN_API_VERSION', None) != 2):
            raise RuntimeError('Deployment files are from different versions. Update the complete repository and reboot the Streamlit app.')
        return scan_service
