""" API do łączenia modułów backendowych z frontem GUI. 
    Po implementacji modułów należy zamienić atrapy z pliku stubs.py na docelowe moduły.
    Gdy moduł jest gotowy, należy go zaimportować i podstawić w funkcji create_backend().
"""

# import funkcji budującej backend z hookami oraz atrap testowych
from contracts  import Backend
from stubs      import NullControl, NullEngine, NullGeometry


def create_backend(demo=False) -> Backend:
    if demo:  # program testowy
        from demo_backend import create_demo_backend
        return create_demo_backend()

    geometry    = NullGeometry()           
    engine      = NullEngine()               
    control     = NullControl()             
    return Backend(geometry, engine, control)