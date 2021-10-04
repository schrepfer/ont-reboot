#!/usr/bin/python3

"""Uses relay to reboot network device based on non-working connection."""


from RPi import GPIO

import argparse
import enum
import logging
import os
import pprint
import random
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
      '-p', '--relay-pin',
      type=int,
      default=4,
      metavar='PIN',
      help='the relays gpio pin (see --pin-mode)',
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
      '--consecutive-failures',
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
      default=5.0,
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
      help='server to ping to verify connection',
    )
  parser.add_argument(
      '--server-list',
      type=str,
      nargs='+',
      default=['www.google.com', '4.2.2.1'],
      metavar='HOSTNAME/IP',
      help='server to ping to verify connection',
    )

  args = parser.parse_args()
  checkFlags(parser, args)
  return args


def checkFlags(parser, args):
  # See: http://docs.python.org/3/library/argparse.html#exiting-methods
  return


def checkConnection(server):
  logging.debug('Checking server: %s', server)
  cmd = ['ping', '-c1', server]
  ret = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  if ret == 0:
    logging.debug('Connection to %r OK', server)
    return True

  logging.warning('Connection to %r FAILED', server)
  return False


def checkConnections(server_list):
  return any(checkConnection(server) for server in server_list)


def main(args):
  GPIO.setwarnings(args.gpio_warnings)
  GPIO.setmode(getattr(GPIO, args.pin_mode))

  logging.info('Args:\n%s', pprint.pformat(dict(args.__dict__.items()), indent=1))

  GPIO.setup(args.relay_pin, GPIO.OUT, initial=GPIO.HIGH)

  last_reboot = 0
  last_connection = 0
  state_count = 0
  previous_state = None

  try:
    while True:
      remote_state = checkConnections(args.server_list)
      logging.debug('remote_state = %s', remote_state)

      # State is considered OK if remote connection works, or the local network is down.
      state = remote_state
      if not state and args.local_server_list:
        logging.info('All remote connections failed. Checking local..')
        local_state = checkConnections(args.local_server_list)
        logging.debug('local_state = %s', local_state)
        logging.info('Local connections %s', 'OK' if local_state else 'FAILED')
        state = not local_state

      logging.debug('state = %s', state)

      if state is previous_state:
        state_count += 1
      else:
        state_count = 0

      logging.debug('state_count = %d', state_count)

      if state:
        last_connection = time.time()

      else:
        if state_count > args.consecutive_failures and (
            time.time() - last_reboot >= args.min_reboot_frequency_seconds):
          logging.info('Rebooting the relay (pin %d) device.', args.relay_pin)
          GPIO.output(args.relay_pin, GPIO.LOW)
          time.sleep(args.power_seconds)
          GPIO.output(args.relay_pin, GPIO.HIGH)
          last_reboot = time.time()

      logging.debug('last_connection = %s', last_connection)
      logging.debug('last_reboot = %s', last_reboot)

      previous_state = state

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
