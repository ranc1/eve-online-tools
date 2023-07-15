import logging

import lib.sound_module as sound
from models.data_models import UiTree, ChatWindow, ChatUserEntity

logger = logging.getLogger('local-monitor-bots')
logger.setLevel(logging.INFO)


class LocalMonitorBot:
    def __init__(self, config: dict):
        self.monitor_character = config['Character']
        self.good_standing_pattern = config['GoodStandingPattern']
        self.consecutive_alarm_count = 0
        self.previous_hostiles = []

    def run(self, ui_tree: UiTree):
        local_chat = self.__get_local_chat(ui_tree.chat_windows)

        if local_chat:
            hostiles = list(filter(self.__is_hostile, local_chat.user_list))
            if len(hostiles) > 0:
                if self.previous_hostiles == hostiles:
                    self.consecutive_alarm_count += 1
                else:
                    self.previous_hostiles = hostiles
                    self.consecutive_alarm_count = 0

                if self.consecutive_alarm_count < 10:
                    sound.play_file('classic_alarm.wav')
                    if self.consecutive_alarm_count < 1:
                        logger.warning(f'{hostiles}.')
            else:
                self.consecutive_alarm_count = 0
        else:
            raise RuntimeError('local chat not found!')

    def __is_hostile(self, user: ChatUserEntity):
        if user.name == self.monitor_character:
            return False
        else:
            standing = user.standing
            return not standing or not any(pattern in standing.lower() for pattern in self.good_standing_pattern)

    @staticmethod
    def __get_local_chat(chat_windows: list[ChatWindow]) -> ChatWindow:
        local_chat = list(filter(lambda chat: chat.name.endswith('_local'), chat_windows))
        return local_chat[0] if local_chat else None
