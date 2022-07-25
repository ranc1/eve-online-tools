import math
import struct

import pyaudio

BITRATE = 44100
p = pyaudio.PyAudio()


def __get_wave_data(frequency, length):
    num_frames = int(BITRATE * length)
    remainder_frames = num_frames % BITRATE

    wave_data = []

    for i in range(num_frames):
        a = BITRATE / frequency
        b = i / a
        c = b * math.pi
        d = math.sin(c) * 32767
        e = int(d)
        wave_data.append(e)

    for i in range(remainder_frames):
        wave_data.append(0)

    num_bytes = str(len(wave_data))
    wave_data = struct.pack(num_bytes + 'h', *wave_data)

    return wave_data


def play(frequency, length):
    frames = __get_wave_data(frequency, length)
    stream = p.open(format=pyaudio.paInt16, channels=2, rate=BITRATE, output=True)
    stream.write(frames)
    stream.stop_stream()
    stream.close()
