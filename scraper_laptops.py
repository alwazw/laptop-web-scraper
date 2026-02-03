# Compatibility shim - forward imports to `scripts.scraper_laptops`
import importlib, sys
_mod = importlib.import_module('scripts.scraper_laptops')
# Replace this module in sys.modules with the real module so assignments like
# `module.DB_PATH = ...` affect the underlying module as expected by tests.
sys.modules[__name__] = _mod