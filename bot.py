import sys

from bots.local_monitor_bot import LocalMonitorBot
import argparse
import logging
import os


# Configure logging root
logging.basicConfig()


if __name__ == '__main__':
    # Set working directory to current file dir
    os.chdir(sys.path[0])

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument('-m', help='Monitor character name', required=True)

    args = arg_parser.parse_args()

    bot = LocalMonitorBot(monitor_character=args.m)

    bot.run()
