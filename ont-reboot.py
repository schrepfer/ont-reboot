#!/usr/bin/python3

"""Uses relay to reboot network device based on non-working connection."""


from RPi import GPIO

import argparse
import collections
import datetime
import enum
import logging
import os
import pprint
import random
import signal
import subprocess
import sys
import time


def defineFlags():
  parser = argparse.ArgumentParser(description=__doc__)
  # See: http://docs.python.org/3/library/argparse.html
  parser.add_argument(
      '-v', '--verbosity',
      action='store',
      default=20,
      type=int,
      help='the logging verbosity',
      metavar='LEVEL',
  )
  parser.add_argument(
      '-V', '--version',
      action='version',
      version='relay version 0.1',
  )
  parser.add_argument(
      '--log-frequency',
      type=int,
      default=100,
      metavar='LOOPS',
      help='how often to log connection stats, 0 for never',
    )
  parser.add_argument(
      '-p', '--relay-pin',
      type=int,
      default=4,
      metavar='PIN',
      help='the relays gpio pin (see --pin-mode to set mode)',
    )
  parser.add_argument(
      '--gpio-warnings',
      default=False,
      action='store_true',
      help='should GPIO warnings be displayed',
    )
  parser.add_argument(
      '-m', '--pin-mode',
      type=str,
      default='BCM',
      metavar='MODE',
      choices=['BCM', 'BOARD'],
      help='the pin-mode to use when selecting pins',
    )
  parser.add_argument(
      '--allowable-consecutive-failures',
      type=int,
      default=2,
      metavar='FAILURES',
      help='number of failures to allow before rebooting relay',
    )
  parser.add_argument(
      '-s', '--sleep-seconds',
      type=float,
      default=45.0,
      metavar='SECONDS',
      help='number of seconds to sleep between ping checks',
    )
  parser.add_argument(
      '--power-seconds',
      type=float,
      default=60.0,
      metavar='SECONDS',
      help='number of seconds to keep relay off for',
    )
  parser.add_argument(
      '--min-reboot-frequency-seconds',
      type=float,
      default=240.0,
      metavar='SECONDS',
      help='minimum number of seconds to reboot the relay',
    )
  parser.add_argument(
      '--local-server-list',
      type=str,
      nargs='*',
      default=['10.20.0.1', '10.20.0.50'],
      metavar='HOSTNAME/IP',
      help='server to ping to verify local connections',
    )
  parser.add_argument(
      '--server-list',
      type=str,
      nargs='+',
      default=['www.google.com', '4.2.2.1'],
      metavar='HOSTNAME/IP',
      help='server to ping to verify remote connections',
    )

  args = parser.parse_args()
  checkFlags(parser, args)
  return args


def checkFlags(parser, args):
  # See: http://docs.python.org/3/library/argparse.html#exiting-methods
  return


connections = collections.defaultdict(lambda: collections.defaultdict(int))
start_time = datetime.datetime.now()
last_reboots = []
last_connection = None
state_counts = collections.defaultdict(int)
loop = 0


def logInfo(*unused, now=None):
  if now is None:
    now = datetime.datetime.now()
  global connections, start_time, last_reboots, last_connection, state_counts
  logging.info(
      'loop %s:\n%s', loop,
      pprint.pformat({
        'state counts': {str(k): v for k, v in state_counts.items()},
        'last connection': str(last_connection),
        'reboots': [str(x) for x in last_reboots],
        'reboots count': len(last_reboots),
        'runtime': str(now - start_time),
        'connections': {k: {'exit({0})'.format(kk): vv for kk, vv in v.items()} for k, v in connections.items()},
      }, indent=1))


def checkConnection(server):
  logging.debug('Checking server: %s', server)
  cmd = ['ping', '-c1', server]
  ret = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  connections[server][ret] += 1

  if ret == 0:
    logging.debug('Connection to %r OK', server)
    return True

  logging.warning('Connection to %r FAILED', server)
  return False


def checkConnections(server_list):
  return any(checkConnection(server) for server in server_list)


class State(enum.Enum):
  UNKNOWN = 0
  REMOTE_DOWN = 1
  LOCAL_DOWN = 2
  UP = 3


def main(args):
  logging.info('Args:\n%s', pprint.pformat(dict(args.__dict__.items()), indent=1))

  GPIO.setwarnings(args.gpio_warnings)
  GPIO.setmode(getattr(GPIO, args.pin_mode))
  GPIO.setup(args.relay_pin, GPIO.OUT, initial=GPIO.HIGH)

  signal.signal(signal.SIGUSR1, logInfo)

  global last_reboots, last_connection, state_counts, loop

  state_count = 0
  previous_state = None
  last_reboot = None
  rebooted = False

  try:
    while True:
      now = datetime.datetime.now()

      if checkConnections(args.server_list):
        state = State.UP
      else:
        state = State.REMOTE_DOWN

      # State is considered OK if remote connection works, or the local network is down.
      if state == State.REMOTE_DOWN and args.local_server_list:
        if not checkConnections(args.local_server_list):
          state = State.LOCAL_DOWN

      logging.debug('state = %s', state)

      if state is previous_state:
        state_count += 1
      else:
        state_count = 0

      logging.debug('state_count = %d', state_count)

      state_counts[state] += 1

      logging.debug('state_counts = %s', {str(k): v for k, v in state_counts.items()})

      if state == state.UP:
        last_connection = now
        if rebooted:
          logging.info('Connection restored.')
          rebooted = False


      elif state == state.REMOTE_DOWN:
        logging.warning('All remote connections down.')
        if state_count > args.allowable_consecutive_failures and (
            not last_reboot or
            (now - last_reboot).total_seconds() >= args.min_reboot_frequency_seconds):
          logging.info('Rebooting the relay (pin %d) device.', args.relay_pin)
          GPIO.output(args.relay_pin, GPIO.LOW)
          time.sleep(args.power_seconds)
          GPIO.output(args.relay_pin, GPIO.HIGH)
          last_reboot = now
          last_reboots.append(last_reboot)
          rebooted = True

      logging.debug('last_connection = %s', last_connection)
      logging.debug('last_reboot = %s', last_reboot)

      previous_state = state

      loop += 1

      if args.log_frequency and not loop % args.log_frequency:
        logInfo(now=now)

      logging.debug('Sleeping for %0.2fs', args.sleep_seconds)
      time.sleep(args.sleep_seconds)

  finally:
    GPIO.cleanup()

  return os.EX_OK


if __name__ == '__main__':
  a = defineFlags()
  logging.basicConfig(
      level=a.verbosity,
      datefmt='%Y/%m/%d %H:%M:%S',
      format='%(filename)s: %(levelname)s: %(message)s')
  sys.exit(main(a))
