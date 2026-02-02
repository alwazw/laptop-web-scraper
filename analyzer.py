# Compatibility shim - forward imports to `scripts.analyzer`
import importlib, sys
_mod = importlib.import_module('scripts.analyzer')
sys.modules[__name__] = _mod