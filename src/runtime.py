from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT


class RuntimeConfig(object):
    def __init__(self, verbose=False, com_timeout=TIMEOUT_DEFAULT, apaga_eeprom=True,
                 baud=BAUD_DEFAULT, portas_disponiveis=None):
        self.verbose = verbose
        self.com_timeout = com_timeout
        self.apaga_eeprom = apaga_eeprom
        self.baud = baud
        self.portas_disponiveis = list(portas_disponiveis or [])

