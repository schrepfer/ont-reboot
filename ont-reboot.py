#!/usr/bin/python3

### BEGIN INIT INFO
# Provides:          relay.py
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Raspberry PI program.
# Description:
### END INIT INFO

"""Uses relay to reboot network device based on poor connection."""


from RPi import GPIO

import argparse
import enum
import logging
import os
import random
import subprocess
import sys
import time

RELAY = 4

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY, GPIO.OUT, initial=GPIO.HIGH)


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
      help='the relays gpio pin',
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
  logging.info("Checking server: %s", server)
  cmd = ['ping', '-c1', server]
  ret = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  if ret == 0:
    logging.info("Connection OK")
    return True

  logging.warning("Connection FAILED")
  return False


def checkConnections(server_list):
  return any(checkConnection(server) for server in server_list)


def main(args):
  last_reboot = 0
  last_connection = 0
  state_count = 0
  previous_state = None

  try:
    while True:
      current_state = checkConnections(args.server_list)

      logging.debug("current_state = %s", current_state)

      if current_state is previous_state:
        state_count += 1
      else:
        state_count = 0

      logging.debug("state_count = %d", state_count)

      if current_state:
        last_connection = time.time()

      else:
        if state_count and state_count > 1 and (
            time.time() - last_reboot >= args.min_reboot_frequency_seconds):
          logging.info("Rebooting the relay device.")
          GPIO.output(RELAY, GPIO.LOW)
          time.sleep(args.power_seconds)
          GPIO.output(RELAY, GPIO.HIGH)
          last_reboot = time.time()

      logging.debug("last_connection = %s", last_connection)
      logging.debug("last_reboot = %s", last_reboot)

      previous_state = current_state

      logging.info("Sleeping for %0.2fs", args.sleep_seconds)

      time.sleep(args.sleep_seconds)

  finally:
    GPIO.cleanup()

  return os.EX_OK


if __name__ == '__main__':
  a = defineFlags()
  logging.basicConfig(
      level=a.verbosity,
      datefmt='%Y/%m/%d %H:%M:%S',
      format='%(levelname)s: %(message)s')
  sys.exit(main(a))
