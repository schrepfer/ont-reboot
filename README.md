# ont-reboot

Uses relay to reboot network device based on non-working connection.

## Usage

```
usage: ont-reboot.py [-h] [-v LEVEL] [-V] [--log-frequency LOOPS] [-p PIN]
                     [--gpio-warnings] [-m MODE]
                     [--allowable-consecutive-failures FAILURES] [-s SECONDS]
                     [--power-seconds SECONDS]
                     [--min-reboot-frequency-seconds SECONDS]
                     [--local-server-list [HOSTNAME/IP [HOSTNAME/IP ...]]]
                     [--server-list HOSTNAME/IP [HOSTNAME/IP ...]]

Uses relay to reboot network device based on non-working connection.

optional arguments:
  -h, --help            show this help message and exit
  -v LEVEL, --verbosity LEVEL
                        the logging verbosity
  -V, --version         show program's version number and exit
  --log-frequency LOOPS
                        how often to log connection stats, 0 for never
  -p PIN, --relay-pin PIN
                        the relays gpio pin (see --pin-mode to set mode)
  --gpio-warnings       should GPIO warnings be displayed
  -m MODE, --pin-mode MODE
                        the pin-mode to use when selecting pins
  --allowable-consecutive-failures FAILURES
                        number of failures to allow before rebooting relay
  -s SECONDS, --sleep-seconds SECONDS
                        number of seconds to sleep between ping checks
  --power-seconds SECONDS
                        number of seconds to keep relay off for
  --min-reboot-frequency-seconds SECONDS
                        minimum number of seconds to reboot the relay
  --local-server-list [HOSTNAME/IP [HOSTNAME/IP ...]]
                        server to ping to verify local connections
  --server-list HOSTNAME/IP [HOSTNAME/IP ...]
                        server to ping to verify remote connections
```
