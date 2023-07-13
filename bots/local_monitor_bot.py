import logging

import lib.sound_module as sound

GOOD_STANDING_PATTERN = [
        'good standing',
        'excellent standing',
        'is in your',
        '所属',
        '良好',
        '優良']

logger = logging.getLogger('local-monitor-bots')
logger.setLevel(logging.INFO)


class LocalMonitorBot:
    def __init__(self, config: dict):
        self.monitor_character = config['character']
        self.consecutive_alarm_count = 0
        self.previous_hostiles = []

    def run(self, ui_tree):
        local_chat = self.__get_local_chat(ui_tree.chat_windows)

        if local_chat:
            hostiles = list(filter(self.__is_hostile, local_chat['userlist']))
            if len(hostiles) > 0:
                if self.previous_hostiles == hostiles:
                    self.consecutive_alarm_count += 1
                else:
                    self.previous_hostiles = hostiles
                    self.consecutive_alarm_count = 0

                logger.warning(f'{hostiles}. Consecutive alarms: {self.consecutive_alarm_count}')
                if self.consecutive_alarm_count < 30:
                    sound.alarm(2)
            else:
                self.consecutive_alarm_count = 0
        else:
            raise RuntimeError('local chat not found!')

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
