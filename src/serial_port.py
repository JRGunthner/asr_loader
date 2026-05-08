import serial


"""Adapter da pyserial para desacoplar a camada de protocolo."""
class SerialPort(object):

    def __init__(self, port, baudrate, timeout):
        self._serial = serial.Serial(port, baudrate, timeout=timeout)

    @property
    def port(self):
        return self._serial.port

    @property
    def baudrate(self):
        return self._serial.baudrate

    @baudrate.setter
    def baudrate(self, value):
        self._serial.baudrate = value

    def read(self, size):
        return self._serial.read(size)

    def write(self, data):
        return self._serial.write(data)

    def close(self):
        self._serial.close()

    def set_dtr(self, state):
        if hasattr(self._serial, "setDTR"):
            getattr(self._serial, "setDTR")(state)
        else:
            self._serial.dtr = state

    def set_rts(self, state):
        if hasattr(self._serial, "setRTS"):
            getattr(self._serial, "setRTS")(state)
        else:
            self._serial.rts = state

    def flush_input(self):
        if hasattr(self._serial, "reset_input_buffer"):
            self._serial.reset_input_buffer()
        elif hasattr(self._serial, "flushInput"):
            getattr(self._serial, "flushInput")()

    def flush_output(self):
        if hasattr(self._serial, "reset_output_buffer"):
            self._serial.reset_output_buffer()
        elif hasattr(self._serial, "flushOutput"):
            getattr(self._serial, "flushOutput")()
