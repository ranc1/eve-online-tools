import lib.user_interface_parser as parser
import os
import subprocess
import time
import winsound
import logging
import uuid


GOOD_STANDING_PATTERN = [
        'good standing',
        'excellent standing',
        'is in your',
        '所属',
        '良好',
        '優良']
LOUD_ALARM_FILE = './resources/structure_warning.wav'

logger = logging.getLogger('local-monitor-bots')
logger.setLevel(logging.INFO)


class LocalMonitorBot:
    def __init__(self, monitor_character, process_id, use_quiet_alarm):
        self.monitor_character = monitor_character
        self.pid = process_id
        self.use_quiet_alarm = use_quiet_alarm
        self.alarm_cycle_count = 30 if use_quiet_alarm else 10 
        self.monitor_down_alarm_second = 30;
        self.last_success_time = time.time()
        self.mem_read_output_file = f'tmp/mem-read-{uuid.uuid5(uuid.NAMESPACE_URL, self.monitor_character)}.json'

    def run(self):
        os.makedirs('tmp', exist_ok=True)
        root_memory_address_set = False
        consecutive_alarm_count = 0
        previous_hostiles = []

        command = f'"mem_reader/read-memory-64-bit.exe" read-memory-eve-online --pid {self.pid} --output-file {self.mem_read_output_file}'

        while True:
            if time.time() - self.last_success_time > self.monitor_down_alarm_second:
                self.__sound_alarm()
                logger.warning(f'Monitor is down. Last scan: {time.ctime(self.last_success_time)} PST')

            try:
                mem_read_process = subprocess.run(command, shell=True)
                mem_read_process.check_returncode()

                ui_tree = parser.parse_memory_read_to_ui_tree(self.mem_read_output_file)
                if not root_memory_address_set:
                    command += f' --root-address {parser.get_root_memory_address(ui_tree)}'
                    root_memory_address_set = True

                chat_windows = parser.parse_chat_windows(ui_tree)
                local_chat = self.__get_local_chat(chat_windows)

                if local_chat:
                    hostiles = list(filter(self.__is_hostile, local_chat['userlist']))
                    if len(hostiles) > 0:
                        if previous_hostiles == hostiles:
                            consecutive_alarm_count += 1
                        else:
                            previous_hostiles = hostiles
                            consecutive_alarm_count = 0

                        logger.warning(f'{hostiles}. Consecutive alarms: {consecutive_alarm_count}')
                        if consecutive_alarm_count < self.alarm_cycle_count:
                            self.__sound_alarm()
                    else:
                        consecutive_alarm_count = 0

                    self.last_success_time = time.time()
                else:
                    logger.warning('local chat not found!')
            except Exception as e:
                logger.warning('Monitor task failed!', e)

            time.sleep(3)

    def __is_hostile(self, user):
        if user['name'] == self.monitor_character:
            return False
        else:
            standing = user['standing']
            return not standing or not any(pattern in standing.lower() for pattern in GOOD_STANDING_PATTERN)

    def __sound_alarm(self):
        if self.use_quiet_alarm:
            self.__sound_quiet_alarm(2)
        else:
            self.__sound_loud_alarm()

    @staticmethod
    def __get_local_chat(chat_windows):
        local_chat = list(filter(lambda chat: chat['name'].endswith('_local'), chat_windows))
        return local_chat[0] if local_chat else None

    @staticmethod
    def __sound_quiet_alarm(count):
        frequency = 440
        duration_in_millis = 250
        for i in range(count):
            winsound.Beep(frequency, duration_in_millis)

    @staticmethod
    def __sound_loud_alarm():
        winsound.PlaySound(LOUD_ALARM_FILE, 1)
