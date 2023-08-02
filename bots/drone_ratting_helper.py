import time

from models.data_models import UiTree, OverviewEntry, ShipUI
import lib.sound_module as sound
import logging

logger = logging.getLogger('drone-ratting-helper')
logger.setLevel(logging.INFO)


class DroneRattingHelper:
    def __init__(self, config: dict):
        self.overview_key = config['OverviewColumn']
        self.drones_idle_text = config['DronesIdleText'].lower()
        self.hp_alarm_type = config['HpAlarmType'].lower()
        self.hp_alarm_threshold = config['HpAlarmThreshold']
        self.targets_to_alarm = [target.lower() for target in config['TargetsToAlarm']]
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
                    sound.play_file('short_alarm.wav')
                    self.consecutive_found_target += 1
            else:
                if self.consecutive_found_target != 0:
                    self.consecutive_found_target = 0

            # Drone idle alarm
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

            # Low HP alarm
            if ui_tree.ship_ui and self.__hp_alarm(overview, ship_ui=ui_tree.ship_ui):
                if self.consecutive_hp_alarm < 3:
                    sound.play_file('hp_alarm.wav')
                    self.consecutive_hp_alarm += 1
            else:
                self.consecutive_hp_alarm = 0

    def __found_watching_target(self, overview: list[OverviewEntry]) -> list[str]:
        lowercase_entries = [entry.info[self.overview_key].lower()
                             for entry in overview if self.overview_key in entry.info]

        if not lowercase_entries:
            # Overview entries may take time to load, if not found in 2 consecutive runs, raise error.
            if self.consecutive_found_target < 1:
                self.consecutive_found_target += 1
            else:
                self.consecutive_found_target = 0
                raise RuntimeError(f'Column: {self.overview_key} is not visible on Overview window.')

        return [target for target in self.targets_to_alarm if target in lowercase_entries]

    def __hp_alarm(self, overview: list[OverviewEntry], ship_ui: ShipUI) -> bool:
        being_attacked = any([entry for entry in overview if entry.indicators.attacking_me])
        if not being_attacked or not ship_ui.hp_percentages:
            should_alarm = False
        else:
            should_alarm = getattr(ship_ui.hp_percentages, self.hp_alarm_type) < self.hp_alarm_threshold

        return should_alarm
