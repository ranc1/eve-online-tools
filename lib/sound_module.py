import winsound


def alarm(count):
    frequency = 440
    duration_in_millis = 250
    for i in range(count):
        winsound.Beep(frequency, duration_in_millis)