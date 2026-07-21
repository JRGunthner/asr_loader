from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT


class RuntimeConfig(object):
    def __init__(self, verbose=False, com_timeout=TIMEOUT_DEFAULT, apaga_eeprom=True,
                 baud=BAUD_DEFAULT, portas_disponiveis=None, auto_boot=True,
                 boot_reset_delay=0.1, boot_release_delay=0.1):
        self.verbose = verbose
        self.com_timeout = com_timeout
        self.apaga_eeprom = apaga_eeprom
        self.baud = baud
        self.portas_disponiveis = list(portas_disponiveis or [])
        self.auto_boot = auto_boot
        self.boot_reset_delay = boot_reset_delay
        self.boot_release_delay = boot_release_delay
