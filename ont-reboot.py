#!/usr/bin/python3

"""Uses relay to reboot network device based on non-working connection."""

import argparse
import collections
import datetime
import enum
import logging
import lgpio
import os
import pprint
import signal
import subprocess
import sys
import time

from gpiozero import OutputDevice


def define_flags():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
      '-v', '--verbosity',
      default=20,
      type=int,
      help='Logging verbosity (e.g., 10 for DEBUG, 20 for INFO)',
  )
  parser.add_argument(
      '--log-frequency',
      type=int,
      default=100,
      help='How often to log connection stats, 0 for never',
  )
  parser.add_argument(
      '-p', '--relay-pin',
      type=int,
      default=4,
      help='The relay GPIO pin (BCM numbering)',
  )
  parser.add_argument(
      '--allowable-consecutive-failures',
      type=int,
      default=2,
      help='Number of failures allowed before rebooting',
  )
  parser.add_argument(
      '-s', '--sleep-seconds',
      type=float,
      default=45.0,
      help='Seconds to sleep between ping checks',
  )
  parser.add_argument(
      '--power-seconds',
      type=float,
      default=60.0,
      help='Seconds to keep relay off during reboot',
  )
  parser.add_argument(
      '--min-reboot-frequency-seconds',
      type=float,
      default=240.0,
      help='Minimum time between consecutive reboots',
  )
  parser.add_argument(
      '--local-server-list',
      type=str,
      nargs='*',
      default=['10.20.0.1', '10.20.0.50'],
      help='Servers to verify local network health',
  )
  parser.add_argument(
      '--server-list',
      type=str,
      nargs='+',
      default=['www.google.com', '4.2.2.1'],
      help='Servers to verify remote internet health',
  )

  args = parser.parse_args()
  check_flags(parser, args)
  return args

def check_flags(parser: argparse.ArgumentParser,
                args: argparse.Namespace) -> None:
  # See: http://docs.python.org/3/library/argparse.html#exiting-methods
  return None


class State(enum.Enum):
  UNKNOWN = 0
  REMOTE_DOWN = 1
  LOCAL_DOWN = 2
  UP = 3


class RelayController:
  def __init__(self, args, relay):
    self.args = args
    self.relay = relay
    self.connections = collections.defaultdict(lambda: collections.defaultdict(int))
    self.start_time = datetime.datetime.now()
    self.last_reboots = []
    self.last_connection = None
    self.state_counts = collections.defaultdict(int)
    self.loop_count = 0

  def log_stats(self, *unused, now=None):
    if now is None:
      now = datetime.datetime.now()

    stats = {
      'state_counts': {str(k.name): v for k, v in self.state_counts.items()},
      'last_connection': str(self.last_connection),
      'reboots': [str(x) for x in self.last_reboots],
      'reboots_count': len(self.last_reboots),
      'runtime': str(now - self.start_time),
      'connections': {
        k: {f'exit({kk})': vv for kk, vv in v.items()} 
        for k, v in self.connections.items()
      },
    }
    logging.info('Loop %s:\n%s', self.loop_count, pprint.pformat(stats, indent=1))

  def check_connection(self, server):
    logging.debug('Checking server: %s', server)
    # -c1: 1 packet, -W2: 2 second timeout
    cmd = ['ping', '-c', '1', '-W', '2', server]

    try:
      result = subprocess.run(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True
      )
      ret = result.returncode
    except Exception as e:
      logging.error('Ping command failed: %s', e)
      ret = -1

    self.connections[server][ret] += 1

    if ret == 0:
      logging.debug('Connection to %r OK', server)
      return True

    logging.warning('Connection to %r FAILED', server)
    return False

  def check_connections(self, server_list):
      return any(self.check_connection(server) for server in server_list)

  def run(self):
    logging.info('Args:\n%s', pprint.pformat(dict(self.args.__dict__.items()), indent=1))

    # Register signal for manual status dumps
    signal.signal(signal.SIGUSR1, self.log_stats)

    state_count = 0
    previous_state = None
    last_reboot_time = None
    reboot_in_progress = False

    try:
      while True:
        now = datetime.datetime.now()

        if self.check_connections(self.args.server_list):
          state = State.UP
        else:
          state = State.REMOTE_DOWN

        # If remote is down, check if local is also down
        if state == State.REMOTE_DOWN and self.args.local_server_list:
          if not self.check_connections(self.args.local_server_list):
            state = State.LOCAL_DOWN

        logging.debug('Current state: %s', state.name)

        if state == previous_state:
          state_count += 1
        else:
          state_count = 0

        self.state_counts[state] += 1
        previous_state = state

        if state == State.UP:
          self.last_connection = now
          if reboot_in_progress:
            logging.info('Connection restored after reboot.')
            reboot_in_progress = False

        elif state == State.REMOTE_DOWN:
          logging.warning('Remote connections failing (consecutive: %d)', state_count)

          can_reboot = (
            not last_reboot_time or 
            (now - last_reboot_time).total_seconds() >= self.args.min_reboot_frequency_seconds
          )

          if state_count >= self.args.allowable_consecutive_failures and can_reboot:
            logging.info('Triggering reboot on pin %d', self.args.relay_pin)

            # gpiozero: .off() cuts the circuit, .on() restores it
            self.relay.off() 
            time.sleep(self.args.power_seconds)
            self.relay.on()
            last_reboot_time = now
            self.last_reboots.append(last_reboot_time)
            reboot_in_progress = True

        self.loop_count += 1

        if self.args.log_frequency and (self.loop_count % self.args.log_frequency == 0):
          self.log_stats(now=now)

        logging.debug('Sleeping for %0.2fs', self.args.sleep_seconds)
        time.sleep(self.args.sleep_seconds)

    except KeyboardInterrupt:
      logging.info('Script interrupted by user.')
    finally:
      # gpiozero handles cleanup automatically, but we can be explicit
      self.relay.close()

def main(args: argparse.Namespace) -> int:
  try:
    relay = OutputDevice(args.relay_pin, active_high=False, initial_value=False)
  except lgpio.error as e:
    logging.error(f'Error: {e}')
    return os.EX_UNAVAILABLE
  controller = RelayController(a, relay)
  controller.run()
  return os.EX_OK

if __name__ == '__main__':
  a = define_flags()
  logging.basicConfig(
    level=a.verbosity,
    datefmt='%Y/%m/%d %H:%M:%S',
    format='[%(asctime)s] %(levelname)s: %(message)s'
  )
  sys.exit(main(a))
