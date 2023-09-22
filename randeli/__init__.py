
from . import cmds

from . import librandeli
from . import policy

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "datefmt": "%m/%d/%Y %I:%M:%S %p",
    "formatters": {
        "cli": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-6s %(name)14s | %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "devel": {
            "format": "%(asctime)s.%(msecs)03d %(funcName)s() %(filename)s:%(lineno)d  | %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "trace": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-6s %(name)14s | %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "cli": {
            "class": "logging.StreamHandler",
            "formatter": "cli",
            "stream"  : "ext://sys.stdout"
        },
        "devel": {
            "class": "logging.StreamHandler",
            "formatter": "devel",
            "stream"  : "ext://sys.stdout"
        },
        "trace": {
            "class": "logging.StreamHandler",
            "formatter": "trace",
            "stream"  : "ext://sys.stdout"
        },
    },
    "loggers": {
        "": {
            "level": "ERROR",
            "handlers": [ "cli" ]
        },
        "r": {
            "level": "DEBUG",
            "handlers": [ "cli" ],
            'propagate': True,
        },
        "r.cli": {
            "level": "DETAIL",
            "handlers": [ "cli" ],
            'propagate': False,
        },
        "r.cli.inspect": {
            "level": "INFO",
            "handlers": [ "cli" ],
            'propagate': False,
        },
        "r.l": {
            "level": "INFO",
            "handlers": [ "cli" ],
            'propagate': False,
        },
        "d.devel": {
            "level": "INFO",
            "handlers": [ "devel" ],
            'propagate': False,
        },
        "d.trace": {
            "level": "INFO",
            "handlers": [ "trace" ],
            'propagate': False,
        },       
    },
}

