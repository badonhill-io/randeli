#
# Copyright (c) 2023 Richard Offer, All rights reserved.

import sys

from loguru import logger as LOGGER

# pylint: disable-next=unused-import
from . import cmds, librandeli, policy

config = {
    "handlers": [
        {"sink": sys.stderr, "format": "{time:HH:mm:ss} | {level: ^7} | {message}", "colorize":True, "level" : "SUCCESS" },
    ],
    "activation" : [
        ("randeli.cli", True),
        ("randeli.cmds.augment", True),
        ("randeli.cmds.bootstrap", True),
        ("randeli.cmds.config", True),
        ("randeli.cmds.inspect", True),
        ("randeli.cmds.map-fonts", True),
        ("randeli.cmds.handlers.augment.epubeventhandler", True),
        ("randeli.cmds.handlers.augment.pdfeventhandler", True),
        ("randeli.librandeli.backend.apryse", True),
        ("randeli.librandeli.backend.base", False),
        ("randeli.librandeli.backend.epub", True),
        ("randeli.librandeli.notify", False),
        ("randeli.policy.rules", False),
    ]
}

LOGGER.configure(**config)
