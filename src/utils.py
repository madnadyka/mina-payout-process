import configparser
import colorlog
import logging
import decimal
import datetime


def init_logger():
    global logger
    if logger is None:
        logger = colorlog.getLogger('log')
        log_level = logging.INFO
        try:
            if config['LOG']["log_level"] == "debug": log_level = logging.DEBUG
            if config['LOG']["log_level"] == "info": log_level = logging.INFO
            if config['LOG']["log_level"] == "warning": log_level = logging.WARNING
            if config['LOG']["log_level"] == "error": log_level = logging.ERROR
        except:
            pass
        logger.setLevel(log_level)
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        formatter = colorlog.ColoredFormatter('%(log_color)s%(asctime)s %(levelname)s: %(message)s (%(module)s:%(lineno)d)')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

logger = None
init_logger()

def init_config():
    global config
    config_file = "../config/config.conf"
    config = configparser.ConfigParser()
    config.read(config_file)

config = None
init_config()


# These functions are not used but indicate how the values retrieved from the API are determined

def timed_weighting(ledger, global_slot_start, slots_per_epoch):
    """Takes in a staking ledger and determines the timed factor for the account"""
    if not ledger["timing"]:
        # Untimed for full epoch so we have the maximum weighting of 1
        return 1
    else:
        # This is timed at the end of the epoch so we always return 0
        if ledger["timing"]["timed_epoch_end"]:
            return 0
        else:
            # This must be timed for only a portion of the epoch
            timed_end = ledger["timing"]["untimed_slot"]
            global_slot_end = global_slot_start + slots_per_epoch

            return ((global_slot_end - timed_end) / slots_per_epoch)


def calculate_end_slot_timed_balance(timing):

    if timing["vesting_period"] == 0 or timing["vesting_increment"] == 0:
        # Then everything vests at once and just cliff time?
        vested_height_global_slot = int(timing["cliff_time"])
    else:
        vested_height_global_slot = int(timing["cliff_time"]) + (
            (int(timing["initial_minimum_balance"]) -
             int(timing["cliff_amount"])) /
            int(timing["vesting_increment"])) * int(timing["vesting_period"])

    return int(vested_height_global_slot)

def float_to_string(number, precision=9):
    return '{0:.{prec}f}'.format(
        decimal.Context(prec=100).create_decimal(str(number)),
        prec=precision,
    ).rstrip('0').rstrip('.') or '0'


def write_to_file(data_string: str, file_name: str, mode: str = "w"):
    with open(file_name, mode) as some_file:
        some_file.write(data_string + "\n")

def time_to_timestamp(value):
    if value is None:
        return ''
    else:
        time_timestamp = int(datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").timestamp())
    return time_timestamp