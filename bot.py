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


def __get_process(is_last):
    comparator = max if is_last else min
    process = comparator(filter(lambda proc: proc.name() == 'exefile.exe', psutil.process_iter()),
                         key=lambda proc: proc.create_time())
    return process.pid


if __name__ == '__main__':
    # Set working directory to current file dir
    os.chdir(sys.path[0])

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-m', help='Monitor character name', required=True)
    arg_parser.add_argument('-p', help='Process ID. If not specified, use first EVE Online process')
    arg_parser.add_argument('-l', help='Use latest started process', action='store_true')
    arg_parser.add_argument('-q', help='Use quieter alarm but longer alarm cycle', action='store_true')

    args = arg_parser.parse_args()

    pid = args.p
    if pid:
        logger.info(f'Using provided EVE process with PID: {pid}')
    else:
        pid = __get_process(args.l)
        logger.info(f'Using {"latest" if args.l else "first"} started EVE process with PID: {pid}')

    bot = LocalMonitorBot(monitor_character=args.m, process_id=pid, use_quiet_alarm=args.q)
    logger.info('Initializing bot... This takes a few minutes so please keep your eve window open and focused')

    bot.run()
