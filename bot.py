import sys

from bots.local_monitor_bot import LocalMonitorBot
import argparse
import logging
import os
import psutil


# Configure logging root
logging.basicConfig()

logger = logging.getLogger('bot-master')
logger.setLevel(logging.INFO)


def __get_process():
    process = min(filter(lambda proc: proc.name() == 'exefile.exe', psutil.process_iter()),
                  key=lambda proc: proc.create_time())
    return process.pid


if __name__ == '__main__':
    # Set working directory to current file dir
    os.chdir(sys.path[0])

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-m', help='Monitor character name', required=True)
    arg_parser.add_argument('-p', help='Process ID. If not specified, use first EVE Online process')

    args = arg_parser.parse_args()

    pid = args.p
    if pid:
        logger.info(f'Using provided EVE process with PID: {pid}')
    else:
        pid = __get_process()
        logger.info(f'Using first started EVE process with PID: {pid}')

    bot = LocalMonitorBot(monitor_character=args.m, process_id=pid)

    bot.run()
