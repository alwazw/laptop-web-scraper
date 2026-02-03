# Compatibility shim - forward imports to `scripts.db_setup`
import importlib, sys
_mod = importlib.import_module('scripts.db_setup')
sys.modules[__name__] = _mod