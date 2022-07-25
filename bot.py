import lib.user_interface_parser as parser
import os
import subprocess
import time
import lib.beep_player as beep_player
import logging
import argparse
import psutil


GOOD_STANDING_PATTERN = ['good standing', 'excellent standing', 'is in your']
MEM_READ_OUTPUT_FILE = 'tmp/mem_read.json'

logging.basicConfig()
logger = logging.getLogger('eve-online-bots')
logger.setLevel(logging.INFO)


class LocalMonitorBot:
    def __init__(self, monitor_character):
        self.monitor_character = monitor_character
        pid = self.__get_process()
        logger.info(f'Using first started EVE process with PID: {pid}')
        self.pid = pid
        self.last_success_time = time.time()

    def run(self):
        os.makedirs('tmp', exist_ok=True)
        root_memory_address_set = False
        consecutive_alarm_count = 0
        previous_hostiles = []

        command = f'"mem_reader/read-memory-64-bit.exe" read-memory-eve-online --pid {self.pid} --output-file {MEM_READ_OUTPUT_FILE}'

        while True:
            if time.time() - self.last_success_time > 30:
                self.__sound_alarm(3)
                logger.warning(f'Monitor is down. Last scan: {time.ctime(self.last_success_time)} PST')

            try:
                mem_read_process = subprocess.run(command, shell=True)
                mem_read_process.check_returncode()

                ui_tree = parser.parse_memory_read_to_ui_tree(MEM_READ_OUTPUT_FILE)
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
                        if consecutive_alarm_count < 30:
                            self.__sound_alarm(2)
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

    @staticmethod
    def __get_local_chat(chat_windows):
        local_chat = list(filter(lambda chat: chat['name'].endswith('_local'), chat_windows))
        return local_chat[0] if local_chat else None

    @staticmethod
    def __sound_alarm(count):
        frequency = 440
        duration_in_millis = 250
        for i in range(count):
            beep_player.play(frequency, duration_in_millis / 1000)

    @staticmethod
    def __get_process():
        process = min(filter(lambda proc: proc.name() == 'exefile.exe', psutil.process_iter()),
                      key=lambda proc: proc.create_time())
        return process.pid


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-m', help='Monitor character name', required=True)

    args = arg_parser.parse_args()

    bot = LocalMonitorBot(monitor_character=args.m)

    bot.run()
