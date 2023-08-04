import logging
import time

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
        self.last_local_visible = time.time()

    def run(self, ui_tree: UiTree):
        local_chat = self.__get_local_chat(ui_tree.chat_windows)
        current_time = time.time()

        if local_chat and local_chat.user_list:
            hostiles = list(filter(self.__is_hostile, local_chat.user_list))
            if len(hostiles) > 0:
                if self.previous_hostiles != hostiles:
                    self.previous_hostiles = hostiles
                    self.consecutive_alarm_count = 0

                if self.consecutive_alarm_count < 10:
                    if self.consecutive_alarm_count < 1:
                        logger.info(f'Hostiles: {", ".join([user.name for user in hostiles])}.')
                    sound.play_file('classic_alarm.wav')
                    self.consecutive_alarm_count += 1
            elif self.previous_hostiles:
                logger.info('System clear.')
                self.consecutive_alarm_count = 0
                self.previous_hostiles = []

            self.last_local_visible = current_time
        elif current_time - self.last_local_visible < 30:
            logger.warning('Local chat not found!')
        else:
            sound.play_file('classic_alarm.wav')
            logger.error(f'Local chat not found! Last chat found: {time.ctime(self.last_local_visible)} PST')

    def __is_hostile(self, user: ChatUserEntity):
        if user.name == self.monitor_character:
            return False
        else:
            standing = user.standing
            return not standing or not any(pattern in standing.lower() for pattern in self.good_standing_pattern)

    @staticmethod
    def __get_local_chat(chat_windows: list[ChatWindow]) -> ChatWindow:
        local_chat = [chat for chat in chat_windows if chat.name.endswith('_local')]
        return local_chat[0] if local_chat else None
