"""
EV Node — placeholder for EV Stack / node framework integration.

The full ev-node implementation lives in the external evstack/ev-node repo
and integrates through adapters. This file provides a local stub for
import compatibility.
"""


class EVNode:
    """Stub for the EV node framework adapter."""

    def __init__(self, host="127.0.0.1", port=5050):
        self.host = host
        self.port = port
        self.connected = False

    def ping(self):
        return {"status": "stub", "message": "EVNode stub — connect evstack/ev-node for full functionality"}
