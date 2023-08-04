import win32api
import win32con
import win32gui
import win32process


def get_game_process_id(character_name: str) -> int:
    """
    Get EVE game client PID from the application window. The window title has the format: EVE - <character_name>
    :param character_name: Game character name.
    :return: EVE game client PID.
    """
    def call_back(hwnd, context):
        text: str = win32gui.GetWindowText(hwnd)
        if text == f'EVE - {character_name}':
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
            process_name: str = win32process.GetModuleFileNameEx(handle, 0)
            if process_name.endswith('exefile.exe'):
                context.append(pid)

    result = []
    win32gui.EnumWindows(call_back, result)

    if len(result) != 1:
        raise RuntimeError(f'Expecting exactly one game client PID for character {character_name}, found: {result}')

    return result[0]
