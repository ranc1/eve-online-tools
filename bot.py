import argparse
import importlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid

import lib.sound_module as sound
import lib.user_interface_parser as parser
import lib.win_process as win_process
from lib.user_interface_parser import UiTree

CHARACTER_NAME_KEY = 'CharacterName'
PROCESS_ID_KEY = 'ProcessId'
BOTS_KEY = 'Bots'

# Configure logging root
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')

logger = logging.getLogger('bot-master')
logger.setLevel(logging.INFO)


def __get_process_id(profile: dict) -> int:
    if PROCESS_ID_KEY in profile:
        pid = profile[PROCESS_ID_KEY]
        logger.info(f'Using provided EVE process with PID: {pid}')
    elif CHARACTER_NAME_KEY in profile:
        character_name = profile[CHARACTER_NAME_KEY]
        pid = win_process.get_game_process_id(character_name)
        logger.info(f'Using EVE client window for character: {character_name}. PID: {pid}')
    else:
        raise RuntimeError(
            f'Cannot determine game process ID. Profile does not contain key {PROCESS_ID_KEY} or {CHARACTER_NAME_KEY}.')

    return pid


def __read_ui_tree(pid: int, output_file: str, root_address=None) -> UiTree:
    os.makedirs('tmp', exist_ok=True)

    read_mem_command = '"mem_reader/read-memory-64-bit.exe" read-memory-eve-online'
    command = f'{read_mem_command} --remove-other-dict-entries --pid {pid} --output-file {output_file}'
    if root_address:
        command += f' --root-address {root_address}'
    else:
        logger.info('Detecting UI tree root might take a few minutes...')

    current_attempts = 0
    max_attempts = 2
    mem_read_process = None
    while current_attempts < max_attempts:
        current_attempts += 1
        try:
            mem_read_process = subprocess.run(command, shell=True, capture_output=True, text=True)
            mem_read_process.check_returncode()

            return parser.parse_memory_read_to_ui_tree(output_file)
        except subprocess.CalledProcessError as ex:
            if current_attempts == max_attempts:
                logger.error(f'Failed to run memory reader: {mem_read_process.stderr}')
                raise ex
            else:
                time.sleep(1)


def __initialize_bots(profile: dict) -> list:
    bots_in_config = []
    for bot_name, bot_config in profile.get(BOTS_KEY, {}).items():
        [module_name, class_name] = bot_name.split('.')
        bot_class = getattr(importlib.import_module(f'plugins.bots.{module_name}'), class_name)
        bots_in_config.append(bot_class(bot_config))

    if not bots_in_config:
        raise RuntimeError('No bot is configured!')

    return bots_in_config


def __get_command_arguments() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-c', help='Client profile file name', required=True)
    arg_parser.add_argument('-d', help='Save memory read to tmp/ folder when failure occurs', action='store_true')

    return arg_parser.parse_args()


def __read_profile() -> dict:
    profile_path = f'plugins/profiles/{args.c}.json'
    with open(profile_path, encoding='utf-8') as f:
        return json.load(f)


if __name__ == '__main__':
    # Set working directory to current file dir
    os.chdir(sys.path[0])

    args = __get_command_arguments()
    client_profile = __read_profile()
    process_id = __get_process_id(client_profile)
    bots = __initialize_bots(client_profile)
    debug_mode = args.d
    if debug_mode:
        logger.info('Debug mode enabled: Memory read will be saved if failure occurs.')

    ui_tree_root_address = None
    mem_read_output_file = f'tmp/mem-read-{uuid.uuid5(uuid.NAMESPACE_URL, args.c)}.json'
    last_success_time = time.time()

    logger.info(f'Starting bots: {[type(bot).__name__ for bot in bots]}...')
    while True:
        all_bots_succeeded = True

        if time.time() - last_success_time > 30:
            sound.alarm(3)
            logger.warning(f'Monitor is down. Last scan: {time.ctime(last_success_time)} PST')

        try:
            ui_tree = __read_ui_tree(process_id, mem_read_output_file, ui_tree_root_address)
            if not ui_tree_root_address:
                ui_tree_root_address = ui_tree.root_address
                logger.info(f'Successfully found UI tree root: {ui_tree_root_address}. Bots running...')

            for bot in bots:
                try:
                    bot.run(ui_tree)
                except Exception as e:
                    logger.warning(f'Bot: {type(bot).__name__} failed execution: {str(e)}')
                    all_bots_succeeded = False
                    if debug_mode:
                        shutil.copy2(mem_read_output_file, f'tmp/debug-{time.time()}.json')

            if all_bots_succeeded:
                last_success_time = time.time()
        except (Exception,):
            logger.exception('Bot execution failed!')
            if debug_mode:
                shutil.copy2(mem_read_output_file, f'tmp/debug-{time.time()}.json')

        time.sleep(3)
