import math
import serial
import struct
import threading
import time
import wave
from numpy import hanning
from numpy.fft import fft

# CONFIGURATION
points = 2048

# DON'T TOUCH
now, sleep = time.time, time.sleep
hypot = math.hypot
stop = False


def get_le(short):
    return struct.unpack('<h', short)[0]


def red(short):
    if short < 15:
        return 1.0
    if short < 50:
        return 1.0 - (short - 15.0) / 35.0
    return 0.0


def green(short):
    if short < 15:
        return short / 15.0
    if short < 200:
        return 1.0
    return 1.0 - (short - 200.0) / 824.0


def blue(short):
    if short < 15:
        return 0.0
    if short < 200:
        return (short - 15.0) / 185.0
    return 1.0


def process(wav, output):
    global stop

    # time between sample slices
    delay = points / wav.getframerate()

    # total number of samples
    nframes = wav.getnframes()

    # width of sample, in bytes
    width = wav.getnchannels() * 2

    # pre-calculate hanning window for color smoothness
    window = hanning(points)

    nextcall = now()
    for section in range(math.ceil(nframes / points)):
        if stop:
            output.write(b'\0\0\0')
            return

        frames = wav.readframes(points)

        # read little-endian sample. uses only 1 channel.
        values = [get_le(frames[i:i + 2]) for i in range(0, len(frames), width)]

        # fill with zeroes if not enough data (e.g. last slice)
        values.extend([0 for _ in range(len(values), points)])
        fourier = fft(values * window)

        r, g, b = 0.0, 0.0, 0.0
        for idx, fbin in enumerate(fourier[:len(fourier) / 2]):
            i = idx + 1

            # magnitude = sqrt of (real part squared + imaginary part squared)
            magnitude = hypot(fbin.real, fbin.imag)
            r += magnitude * red(idx)
            g += magnitude * green(idx)
            b += magnitude * blue(idx)

        # divide all values by theoretical maximum relevant value
        r, g, b = (x / float(1 << 22) for x in (r, g, b))
        max_value = max(r, g, b, 1)

        # value is a number in range [0, 1]
        # powering by 4 simulates logarithmic potentiometer values
        string = tuple(int(math.pow(x / max_value, 4) * 255) for x in (r, g, b))
        output.write(bytes(string))

        nextcall = nextcall + delay
        sleep(nextcall - now())


def main():
    global stop

    def serial_port(filename):
        return serial.Serial(filename, baudrate=9600)

    def wave_rb(filename):
        return wave.open(filename, 'rb')

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=wave_rb, required=True)
    parser.add_argument('-o', '--output', type=serial_port, required=True)

    args = parser.parse_args()

    timer = threading.Thread(target=process, kwargs={
        'wav': args.input,
        'output': args.output,
    })
    timer.start()

    try:
        while timer.is_alive():
            timer.join(1)
    except KeyboardInterrupt:
        stop = True


if __name__ == "__main__":
    main()
