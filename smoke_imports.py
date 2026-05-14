import importlib
mods = [
    'src.core.state',
    'src.core.simulator',
    'src.core.estimator',
    'src.core.model',
    'src.core.controller',
]
for m in mods:
    mod = importlib.import_module(m)
    print('Imported', m, '->', getattr(mod, '__name__', None))
