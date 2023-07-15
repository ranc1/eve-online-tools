import time

from models.data_models import UiTree
import lib.sound_module as sound
import logging

logger = logging.getLogger('drone-ratting-helper')
logger.setLevel(logging.INFO)


class DroneRattingHelper:
    def __init__(self, config: dict):
        self.overview_key = config['OverviewColumn']
        self.drones_idle_text = config['DronesIdleText'].lower()
        self.targets_to_alarm = [target.lower() for target in config['TargetsToAlarm']]
        self.consecutive_found_target = 0
        self.consecutive_idle_alarm = 0
        self.last_drone_active_time = time.time()
        self.last_drone_in_bay_time = time.time()

    def run(self, ui_tree: UiTree):
        overview = ui_tree.overview

        if overview:
            lowercase_entries = [entry.info[self.overview_key].lower()
                                 for entry in overview if self.overview_key in entry.info]

            if not lowercase_entries:
                raise RuntimeError(f'Column: {self.overview_key} is not visible on Overview window.')

            alarm_targets = [target for target in self.targets_to_alarm if target in lowercase_entries]
            if alarm_targets:
                if self.consecutive_found_target < 2:
                    logger.info(f'Found watching targets: {alarm_targets}')
                    sound.play_file('short_alarm.wav')
                    self.consecutive_found_target += 1
            else:
                if self.consecutive_found_target != 0:
                    self.consecutive_found_target = 0

            drones_in_space = ui_tree.drones.in_space
            current_time = time.time()
            if drones_in_space:
                if all([self.drones_idle_text in drone.text.lower() for drone in drones_in_space]):
                    if (current_time - self.last_drone_active_time > 20 and
                            current_time - self.last_drone_in_bay_time > 120 and self.consecutive_idle_alarm < 1):
                        logger.info('Ratter is idle...')
                        sound.play_file('dog_bark.wav')
                        self.consecutive_idle_alarm += 1
                else:
                    self.consecutive_idle_alarm = 0
                    self.last_drone_active_time = current_time
            else:
                self.last_drone_in_bay_time = current_time
