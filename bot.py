import argparse
import importlib
import json
import logging
import os
import subprocess
import sys
import time
import uuid

import psutil

import lib.sound_module as sound
import lib.user_interface_parser as parser
from lib.user_interface_parser import UiTree

# Configure logging root
logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')

logger = logging.getLogger('bot-master')
logger.setLevel(logging.INFO)


def __get_process(is_last: bool) -> int:
    comparator = max if is_last else min
    process = comparator(filter(lambda proc: proc.name() == 'exefile.exe', psutil.process_iter()),
                         key=lambda proc: proc.create_time())
    return process.pid


def __read_ui_tree(pid: int, output_file: str, root_address=None) -> UiTree:
    os.makedirs('tmp', exist_ok=True)

    read_mem_command = '"mem_reader/read-memory-64-bit.exe" read-memory-eve-online'
    command = f'{read_mem_command} --remove-other-dict-entries --pid {pid} --output-file {output_file}'
    if root_address:
        command += f' --root-address {root_address}'

    mem_read_process = None
    try:
        mem_read_process = subprocess.run(command, shell=True, capture_output=True, text=True)
        mem_read_process.check_returncode()

        return parser.parse_memory_read_to_ui_tree(output_file)
    except subprocess.CalledProcessError as ex:
        logger.error(f'Failed to run memory reader: {mem_read_process.stderr}')
        raise ex


def __initialize_bots(bot_config: dict) -> list:
    bots_in_config = []
    for bot_name, bot_config in bot_config.items():
        [module_name, class_name] = bot_name.split('.')
        bot_class = getattr(importlib.import_module(f'bots.{module_name}'), class_name)
        bots_in_config.append(bot_class(bot_config))

    return bots_in_config


if __name__ == '__main__':
    # Set working directory to current file dir
    os.chdir(sys.path[0])

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-c', help='Bot configuration file name', required=True)
    arg_parser.add_argument('-p', help='Process ID. If not specified, use first EVE Online process')
    arg_parser.add_argument('-l', help='Use latest started process', action='store_true')

    args = arg_parser.parse_args()

    process_id = args.p
    if process_id:
        logger.info(f'Using provided EVE process with PID: {process_id}')
    else:
        process_id = __get_process(args.l)
        logger.info(f'Using {"latest" if args.l else "first"} started EVE process with PID: {process_id}')

    ui_tree_root_address = None
    mem_read_output_file = f'tmp/mem-read-{uuid.uuid5(uuid.NAMESPACE_URL, args.c)}.json'

    config_file_path = f'config/{args.c}.json'
    with open(config_file_path) as f:
        config = json.load(f)

    bots = __initialize_bots(config)

    if not bots:
        raise RuntimeError('No bot is configured!')

    logger.info(f'Starting bots: {[type(bot).__name__ for bot in bots]}...')

    logger.info('Detecting UI tree root might take a few minutes...')
    last_success_time = time.time()
    while True:
        all_bots_succeeded = True

        if time.time() - last_success_time > 30:
            sound.alarm(3)
            logger.warning(f'Monitor is down. Last scan: {time.ctime(last_success_time)} PST')

        try:
            ui_tree = __read_ui_tree(process_id, mem_read_output_file, ui_tree_root_address)
            if not ui_tree_root_address:
                ui_tree_root_address = ui_tree.root_address
                logger.info(f'Detected UI tree root: {ui_tree_root_address}.')

            for bot in bots:
                try:
                    bot.run(ui_tree)
                except Exception as e:
                    logger.warning(f'Bot: {type(bot).__name__} failed execution: {str(e)}')
                    all_bots_succeeded = False

            if all_bots_succeeded:
                last_success_time = time.time()
        except (Exception,):
            logger.exception('Bot execution failed!')

        time.sleep(3)
