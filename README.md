# ont-reboot

Uses relay to reboot network device based on non-working connection.

## Usage

```
usage: ont-reboot.py [-h] [-v VERBOSITY] [--log-frequency LOG_FREQUENCY] [-p RELAY_PIN]
                     [--allowable-consecutive-failures ALLOWABLE_CONSECUTIVE_FAILURES]
                     [-s SLEEP_SECONDS]
                     [--power-seconds POWER_SECONDS]
                     [--min-reboot-frequency-seconds MIN_REBOOT_FREQUENCY_SECONDS]
                     [--local-server-list [LOCAL_SERVER_LIST ...]]
                     [--server-list SERVER_LIST [SERVER_LIST ...]]

Uses relay to reboot network device based on non-working connection.

options:
  -h, --help            show this help message and exit
  -v VERBOSITY, --verbosity VERBOSITY
                        Logging verbosity (e.g., 10 for DEBUG, 20 for INFO)
  --log-frequency LOG_FREQUENCY
                        How often to log connection stats, 0 for never
  -p RELAY_PIN, --relay-pin RELAY_PIN
                        The relay GPIO pin (BCM numbering)
  --allowable-consecutive-failures ALLOWABLE_CONSECUTIVE_FAILURES
                        Number of failures allowed before rebooting
  -s SLEEP_SECONDS, --sleep-seconds SLEEP_SECONDS
                        Seconds to sleep between ping checks
  --power-seconds POWER_SECONDS
                        Seconds to keep relay off during reboot
  --min-reboot-frequency-seconds MIN_REBOOT_FREQUENCY_SECONDS
                        Minimum time between consecutive reboots
  --local-server-list [LOCAL_SERVER_LIST ...]
                        Servers to verify local network health
  --server-list SERVER_LIST [SERVER_LIST ...]
                        Servers to verify remote internet health
```
