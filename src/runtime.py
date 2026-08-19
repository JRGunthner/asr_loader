import json
from datetime import datetime
from pathlib import Path

from .constantes import BAUD_DEFAULT, TIMEOUT_DEFAULT


class RuntimeConfig(object):
    def __init__(self, verbose=False, com_timeout=TIMEOUT_DEFAULT, apaga_eeprom=True,
                 baud=BAUD_DEFAULT, portas_disponiveis=None, auto_boot=True,
                 boot_reset_delay=0.1, boot_release_delay=0.1, log_file=None, trace_json=None,
                 v8=False):
        self.verbose = verbose
        self.com_timeout = com_timeout
        self.apaga_eeprom = apaga_eeprom
        self.baud = baud
        self.portas_disponiveis = list(portas_disponiveis or [])
        self.auto_boot = auto_boot
        self.boot_reset_delay = boot_reset_delay
        self.boot_release_delay = boot_release_delay
        self.log_file = log_file
        self.trace_json = trace_json
        self.v8 = v8
        self._log_handle = None
        self._trace_handle = None
        if log_file is not None:
            log_path = Path(log_file)
            if log_path.parent != Path(''):
                log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_handle = log_path.open('a', encoding='utf-8')
            self.log('--- inicio do log ---')
        if trace_json is not None:
            trace_path = Path(trace_json)
            if trace_path.parent != Path(''):
                trace_path.parent.mkdir(parents=True, exist_ok=True)
            self._trace_handle = trace_path.open('a', encoding='utf-8')
            self.trace('trace_start')

    def log(self, mensagem):
        if self._log_handle is None:
            return
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        self._log_handle.write('[%s] %s\n' % (timestamp, mensagem))
        self._log_handle.flush()

    def close_log(self):
        if self._log_handle is not None:
            self.log('--- fim do log ---')
            self._log_handle.close()
            self._log_handle = None

    def trace(self, event, **campos):
        if self._trace_handle is None:
            return
        registro = {
            'timestamp': datetime.now().isoformat(timespec='milliseconds'),
            'event': event,
        }
        registro.update(campos)
        self._trace_handle.write(json.dumps(registro, ensure_ascii=False, default=str) + '\n')
        self._trace_handle.flush()

    def close_trace(self):
        if self._trace_handle is not None:
            self.trace('trace_end')
            self._trace_handle.close()
            self._trace_handle = None
