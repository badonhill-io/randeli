import inspect
import logging
import time

_logger = logging.getLogger("d.trace")

def tracer(f):
    def t(*args, **kwargs):
        name = f.__qualname__
        if f.__name__ == "__call__":
            name = name.replace(".__call__", "")

        _logger.notice(f"-> {name}()")

        arg_index = 0
        if "self" in inspect.signature(t).parameters:
            arg_index = 1

        _logger.detail(f"++ {name}{list(args[arg_index:])},{kwargs}")

        start = time.time()
        original_result = f(*args, **kwargs)
        end = time.time()
        elapsed = (end - start) * 1000.0

        _logger.info(f"<- {name}() {elapsed= :.3f} ms")
        _logger.detail(f"-- {name}() = {original_result}")

        return original_result

    return t

