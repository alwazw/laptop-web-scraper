# Compatibility shim - forward imports to `scripts.scraper_components`
import importlib, sys
_mod = importlib.import_module('scripts.scraper_components')
sys.modules[__name__] = _mod