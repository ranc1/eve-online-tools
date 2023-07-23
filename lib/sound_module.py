import winsound


def alarm(count: int) -> None:
    frequency = 440
    duration_in_millis = 250
    for i in range(count):
        winsound.Beep(frequency, duration_in_millis)


def play_file(file_name: str) -> None:
    file_path = f'resources/{file_name}'
    winsound.PlaySound(file_path, winsound.SND_ASYNC)
