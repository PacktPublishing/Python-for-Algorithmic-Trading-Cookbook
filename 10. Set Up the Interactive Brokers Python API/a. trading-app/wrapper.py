from ibapi.wrapper import EWrapper


class IBWrapper(EWrapper):
    def __init__(self):
        EWrapper.__init__(self)
        self.nextValidOrderId = None
