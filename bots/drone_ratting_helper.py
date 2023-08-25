import logging
import time

import lib.sound_module as sound
from models.data_models import UiTree, OverviewEntry, ShipUI

logger = logging.getLogger('drone-ratting-helper')
logger.setLevel(logging.INFO)


class DroneRattingHelper:
    def __init__(self, config: dict):
        self.overview_key = config['OverviewColumn']
        self.drones_idle_text = config['DronesIdleText'].lower()
        self.hp_alarm_type = config['HpAlarmType'].lower()
        self.hp_alarm_threshold = config['HpAlarmThreshold']
        self.targets_to_alarm = config['TargetsToAlarm']
        self.target_found_alarm = config.get('TargetFoundAlarmFile', None)
        self.hp_alarm = config.get('HpAlarmFile', None)
        self.idle_alarm = config.get('IdleAlarmFile', None)
        self.consecutive_found_target = 0
        self.consecutive_idle_alarm = 0
        self.consecutive_hp_alarm = 0
        self.last_drone_active_time = time.time()
        self.last_drone_in_bay_time = time.time()
        self.consecutive_column_not_found = 0

    def run(self, ui_tree: UiTree):
        overview = ui_tree.overview

        if overview:
            # Target monitor alarm
            alarm_targets = self.__found_watching_target(overview)
            if alarm_targets:
                if self.consecutive_found_target < 2:
                    logger.info(f'Found watching targets: {alarm_targets}')
                    if self.target_found_alarm:
                        sound.play_file(self.target_found_alarm)
                    self.consecutive_found_target += 1
            elif self.consecutive_found_target != 0:
                self.consecutive_found_target = 0

            # Drone idle alarm
            drones_in_space = ui_tree.drones.in_space
            current_time = time.time()
            if drones_in_space:
                if all(self.drones_idle_text in drone.text.lower() for drone in drones_in_space):
                    if (current_time - self.last_drone_active_time > 20 and
                            current_time - self.last_drone_in_bay_time > 120 and self.consecutive_idle_alarm < 1):
                        if self.idle_alarm:
                            sound.play_file(self.idle_alarm)
                        logger.info('Ratter is idle...')
                        self.consecutive_idle_alarm += 1
                else:
                    self.consecutive_idle_alarm = 0
                    self.last_drone_active_time = current_time
            else:
                self.last_drone_in_bay_time = current_time

            # Low HP alarm
            if ui_tree.ship_ui and self.__hp_alarm(overview, ship_ui=ui_tree.ship_ui):
                if self.consecutive_hp_alarm < 3 and self.hp_alarm:
                    sound.play_file(self.hp_alarm)
                    self.consecutive_hp_alarm += 1
            else:
                self.consecutive_hp_alarm = 0

    def __found_watching_target(self, overview: list[OverviewEntry]) -> list[str]:
        entries = [entry.info[self.overview_key] for entry in overview if self.overview_key in entry.info]

        if not entries:
            # Overview entries may take time to load, if not found in 3 consecutive runs, raise error.
            if self.consecutive_column_not_found < 2:
                self.consecutive_column_not_found += 1
            else:
                self.consecutive_column_not_found = 0
                raise RuntimeError(f'Column: {self.overview_key} is not visible on Overview window.')

        return [entry for entry in entries if any(target.lower() in entry.lower() for target in self.targets_to_alarm)]

    def __hp_alarm(self, overview: list[OverviewEntry], ship_ui: ShipUI) -> bool:
        being_attacked = any(entry for entry in overview if entry.indicators.attacking_me)
        if not being_attacked or not ship_ui.hp_percentages:
            should_alarm = False
        else:
            should_alarm = getattr(ship_ui.hp_percentages, self.hp_alarm_type) < self.hp_alarm_threshold

        return should_alarm
