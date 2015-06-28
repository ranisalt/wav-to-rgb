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
pow, sqrt = math.pow, math.sqrt


def get_le(bs):
    return struct.unpack('<h', bs)[0]


def red(bs):
    if bs < 15:
        return 1.0
    if bs < 50:
        return 1.0 - (bs - 15.0) / 35.0
    return 0.0


def green(bs):
    if bs < 15:
        return bs / 15.0
    if bs < 200:
        return 1.0
    return 1.0 - (bs - 200.0) / 824.0


def blue(bs):
    if bs < 15:
        return 0.0
    if bs < 200:
        return (bs - 15.0) / 185.0
    return 1.0


def process(wav, output):
    channels = wav.getnchannels()
    delay = points / wav.getframerate()
    nframes = wav.getnframes()
    window = hanning(points)

    nextcall = now()
    for i in range(math.ceil(nframes / points)):
        frames = wav.readframes(points)
        values = [get_le(frames[i:i + 2]) for i in range(0, len(frames), 2 * channels)]
        values.extend([0 for _ in range(len(values), points)])
        fourier = fft(values * window)

        r, g, b = 0.0, 0.0, 0.0
        for idx, bin in enumerate(fourier[:len(fourier) / 2]):
            i = idx + 1
            magnitude = sqrt(pow(bin.real, 2) + pow(bin.imag, 2))
            #print("%f" % (magnitude, ))
            r += magnitude * red(i)
            g += magnitude * green(i)
            b += magnitude * blue(i)

        r, g, b = map(lambda x: x / 1000000000.0, (r, g, b))
        maxv = max(r, g, b, 1)
        ref = lambda x: str(chr(int(x / maxv * 255))).encode()

        output.write(ref(r))
        output.write(ref(g))
        output.write(ref(b))

        #print("%d %d %d" % tuple(map(lambda x: x / maxv * 255, (r, g, b))))

        nextcall = nextcall + delay
        #sleepdelay = nextcall - now()
        sleep(nextcall - now())
        #sleep(sleepdelay)


def main():
    """def file_wb(filename):
        return open(filename, 'wb')"""

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
    timer.join()


if __name__ == "__main__":
    main()
