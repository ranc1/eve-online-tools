from lib.user_interface_parser import UiTree
import lib.sound_module as sound
import logging

logger = logging.getLogger('drone-ratting-helper')
logger.setLevel(logging.INFO)


class DroneRattingHelper:
    def __init__(self, config: dict):
        self.overview_key = config['OverviewColumn']
        self.targets_to_alarm = [target.lower() for target in config['TargetsToAlarm']]
        self.consecutive_found = 0

    def run(self, ui_tree: UiTree):
        overview = ui_tree.overview

        if overview:
            lowercase_entries = [entry[self.overview_key].lower() for entry in overview if self.overview_key in entry]

            if not lowercase_entries:
                raise RuntimeError(f'Column: {self.overview_key} is not visible on Overview window.')

            alarm_targets = [target for target in self.targets_to_alarm if target in lowercase_entries]
            if alarm_targets:
                self.consecutive_found += 1
                if self.consecutive_found <= 2:
                    logger.info(f'Found watching targets: {alarm_targets}')
                    sound.play_file('short_alarm.wav')
            else:
                if self.consecutive_found != 0:
                    self.consecutive_found = 0
