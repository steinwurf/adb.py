#! /usr/bin/env python
# encoding: utf-8

import argparse
import subprocess
import threading
import time
import os
import re

BUTTONS = {
    "soft_right": 2,
    "home": 3,
    "back": 4,
    "call": 5,
    "endcall": 6,
    "0": 7,
    "1": 8,
    "2": 9,
    "3": 10,
    "4": 11,
    "5": 12,
    "6": 13,
    "7": 14,
    "8": 15,
    "9": 16,
    "star": 17,
    "pound": 18,
    "dpad_up": 19,
    "dpad_down": 20,
    "dpad_left": 21,
    "dpad_right": 22,
    "dpad_center": 23,
    "volume_up": 24,
    "volume_down": 25,
    "power": 26,
    "camera": 27,
    "clear": 28,
    "a": 29,
    "b": 30,
    "c": 31,
    "d": 32,
    "e": 33,
    "f": 34,
    "g": 35,
    "h": 36,
    "i": 37,
    "j": 38,
    "k": 39,
    "l": 40,
    "m": 41,
    "n": 42,
    "o": 43,
    "p": 44,
    "q": 45,
    "r": 46,
    "s": 47,
    "t": 48,
    "u": 49,
    "v": 50,
    "w": 51,
    "x": 52,
    "y": 53,
    "z": 54,
    "comma": 55,
    "period": 56,
    "alt_left": 57,
    "alt_right": 58,
    "shift_left": 59,
    "shift_right": 60,
    "tab": 61,
    "space": 62,
    "sym": 63,
    "explorer": 64,
    "envelope": 65,
    "enter": 66,
    "del": 67,
    "grave": 68,
    "minus": 69,
    "equals": 70,
    "left_bracket": 71,
    "right_bracket": 72,
    "backslash": 73,
    "semicolon": 74,
    "apostrophe": 75,
    "slash": 76,
    "at": 77,
    "num": 78,
    "headsethook": 79,
    "focus": 80,
    "plus": 81,
    "menu": 82,
    "notification": 83,
    "search": 84
}


class Command(object):
    """Wrapper for Popen which supports a timeout."""

    def __init__(self, cmd, timeout):
        """initialize command."""
        super(Command, self).__init__()
        self.cmd = cmd
        self.timeout = timeout
        self.process = None
        self.result = None

    def run(self):
        """Run command."""
        def target():
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            self.result = self.process.communicate()
        thread = threading.Thread(
            target=target,
            name=" ".join(self.cmd))
        thread.start()
        thread.join(self.timeout)
        if thread.is_alive():
            print("Error: '{}' took too long.".format(
                " ".join(self.cmd)))
            self.process.terminate()
            thread.join()
        if self.result:
            return (
                self.result[0],
                self.result[1],
                self.process.returncode)
        else:
            return (None, None, None)


class ADB(object):
    """docstring for ADB."""

    def __init__(self, adb, threads, specific_devices):
        """initialize ADB."""
        super(ADB, self).__init__()
        self.adb = adb
        self.cmd_semaphore = threading.BoundedSemaphore(value=threads)
        self.print_mutex = threading.Lock()
        self.__run([self.adb, 'start-server'])
        self.specific_devices = specific_devices

    def __run(self, cmd, timeout=20, print_cmd=False):
        stdout = None
        stderr = None
        returncode = None
        try:
            self.cmd_semaphore.acquire()
            if print_cmd:
                self.__print(" ".join(cmd))

            command = Command(cmd, timeout)
            stdout, stderr, returncode = command.run()

        except Exception as e:
            self.__print("Error: ".format(e.message, " ".join(cmd)))
        finally:
            if print_cmd and stdout:
                self.__print(stdout.strip())
            if print_cmd and stderr:
                self.__print(stderr.strip())
            self.cmd_semaphore.release()

            return stdout, stderr, returncode

    def __print(self, message):
        self.print_mutex.acquire()
        print(message)
        self.print_mutex.release()

    def __get_devices(self):
        outputs, _, _ = self.__run([self.adb, 'devices'])
        if not outputs:
            return []

        outputs = [i for i in outputs.split('\n')[1:] if i]
        devices = {}
        for output in outputs:
            output = output.split()
            device_id = output[0]
            if device_id == '????????????':
                print('device with insufficient permissions found.')
                continue
            if output[1] == 'unauthorized':
                print('unauthorized device found.')
                continue
            if self.specific_devices:
                if device_id not in self.specific_devices:
                    continue
            devices[device_id] = {'handle': device_id}
        return devices

    def __get_prop(self, handle, prop):
        cmd = [self.adb, '-s', handle, 'shell',
               'getprop', prop]
        result, _, _ = self.__run(cmd)
        if not result:
            return ""
        return result.strip()

    def __version(self, handle):
        version_string = self.__get_prop(handle, 'ro.build.version.release')
        if version_string == "7.0":
            version_string = "7.0.0"
        version_split = version_string.split('.')
        if len(version_split) != 3:
            return (0, 0, 0)

        major, minor, patch = version_split
        return (int(major), int(minor), int(patch))

    def __ip(self, handle):
        return self.__get_prop(handle, 'dhcp.wlan0.ipaddress')

    def __serial(self, handle):
        return self.__get_prop(handle, 'ro.serialno')

    def __brand(self, handle):
        return self.__get_prop(handle, 'ro.product.brand')

    def __model(self, handle):
        return self.__get_prop(handle, 'ro.product.model')

    def __is_wifi_off(self, handle):
        return self.__get_prop(handle, 'init.svc.dhcpcd_wlan0') == 'stopped'

    def __battery(self, handle):
        cmd = [self.adb, '-s', handle, 'shell',
               'cat', '/sys/class/power_supply/battery/capacity']
        result, _, _ = self.__run(cmd)

        if not result or 'No such file or directory' in result:
            return "-"

        return result.strip()

    def __is_screen_locked(self, handle):
        cmd = [self.adb, '-s', handle, 'shell', 'dumpsys statusbar']
        output, _, _ = self.__run(cmd)
        if not output:
            return True
        output = output.strip()
        result = 'mDisabled=0x1e00000' in output
        result |= 'mDisabled1=0x3200000' in output
        return result

    def __is_screen_on(self, handle):
        cmd = [self.adb, '-s', handle, 'shell', 'dumpsys power']
        output, _, _ = self.__run(cmd)

        if not output:
            return False

        output = output.strip()
        result = 'mScreenOn=true' in output or \
                 'SCREEN_ON_BIT' in output or \
                 'Display Power: state=ON' in output

        return result

    def __screen_size(self, handle):
        version = self.__version(handle)
        if version[0] <= 4 and version[1] < 3:
            cmd = [self.adb, '-s', handle, 'shell', 'dumpsys window windows']
            output, stderr, _ = self.__run(cmd)
            result = re.search("Display: init=(\d+)x(\d+)", output)
            if result is None:
                return (0, 0)
            width = int(result.group(1))
            height = int(result.group(2))
            return (width, height)

        cmd = [self.adb, '-s', handle, 'shell', 'wm size']
        output, stderr, _ = self.__run(cmd)
        result = re.search("Physical size: (\d+)x(\d+)", output)
        if result is None:
            return (0, 0)
        width = int(result.group(1))
        height = int(result.group(2))
        return (width, height)

    def __orientation(self, handle):
        # Returns None or 0, 1, 2, or 3.
        # 0 is potrait
        # 1 is landscape
        # 2 is potrait top down
        # 3 is landscape top down

        # This seems to fail occasionally, try a few time if we fail.
        tries = 0
        orientation = None
        while orientation is None and tries < 10:
            tries += 1
            cmd = [self.adb, '-s', handle, 'shell', 'dumpsys input']
            output, stderr, _ = self.__run(cmd)
            for line in output.splitlines():
                if 'SurfaceOrientation' in line:
                    orientation = int(line[-1])
                    break
            else:
                time.sleep(1)

        if not orientation:
            print("Error: Unable to find SurfaceOrientation, "
                  "I'm guessing landscape.")
            return 1

        return orientation

    def __push(self, handle, local, remote):
        cmd = [self.adb, '-s', handle, 'push', local, remote]
        self.__run(cmd)

    def __install(self, handle, apk):
        apk = os.path.abspath(apk)
        cmd = [self.adb, '-s', handle, 'install', '-r', apk]
        return self.__run(cmd, timeout=40)

    def __running(self, handle, package_name):
        cmd = [self.adb, '-s', handle, 'shell', 'ps']
        output, _, _ = self.__run(cmd)
        return (handle, any(
            [line.endswith(package_name) for line in output.splitlines()]))

    def __is_off(self, handle):
        # adb is set to unsecure when the table is off.
        # It's unknown if this can happen in other situations.
        is_adb_secure = self.__get_prop(handle, 'ro.adb.secure')
        return is_adb_secure == '0'

    def __has(self, handle, package_name):
        cmd = [self.adb, '-s', handle, 'shell', 'pm list packages']
        output, _, _ = self.__run(cmd)

        result = any(
            [line.endswith(package_name) for line in output.splitlines()])

        return (handle, result)

    def __uninstall(self, handle, package_name):
        cmd = [self.adb, '-s', handle, 'uninstall', package_name]
        self.__run(cmd, print_cmd=True)

    def __stop(self, handle, package_name):
        cmd = [self.adb, '-s', handle, 'shell',
               'am', 'force-stop', package_name]
        self.__run(cmd)

    def __start(self, handle, package_name, activity='MainActivity',
                action=None, data_string=None, parameters={}):
        cmd = [self.adb, '-s', handle, 'shell', 'am', 'start', '-n']

        cmd.append('{package_name}/.{activity}'.format(
            package_name=package_name, activity=activity))

        if data_string is not None:
            cmd.append('-d {data_string}'.format(data_string=data_string))

        if action is not None:
            cmd.append('-a {action}'.format(action=action))

        for parameter in parameters:
            cmd.append('-e {key} {value}'.format(
                key=parameter, value=parameters[parameter]))

        self.__run(cmd)

    def __press(self, handle, button):
        key_id = str(BUTTONS[button])
        cmd = [self.adb, '-s', handle, 'shell', 'input', 'keyevent', key_id]
        self.__run(cmd)

    def __shutdown(self, handle):
        cmd = [self.adb, '-s', handle, 'shell', 'reboot', '-p']
        self.__run(cmd)

    def __reboot(self, handle):
        cmd = [self.adb, '-s', handle, 'shell', 'reboot']
        self.__run(cmd)

    def __turn_on(self, handle):
        if self.__is_off(handle):
            self.__reboot(handle)

    def __turn_screen(self, handle, turn):
        screen = self.__is_screen_on(handle)
        if screen != turn:
            self.__press(handle, 'power')

    def __unlock(self, handle):
        self.__turn_screen(handle, True)

        model = self.__model(handle)
        if model in ["LG-E460", "SM-T555"]:
            self.__swipe(handle, (100, 400), (300, 400))
            return

        if model == "T1-A21L":
            _from = None
            _to = None
            orientation = self.__orientation(handle)

            if orientation in [0, 2]:
                # Potrait
                _from = (400, 640)
                _to = (800, 640)
            elif orientation in [1, 3]:
                # Landscape
                _from = (100, 400)
                _to = (1270, 400)
            else:
                print("ERROR, unable to get orientation!")
                print(orientation)

            self.__swipe(handle, _from, _to)
            return

        if model == "Nexus 4":
            self.__swipe(handle, (300, 700), (300, 300))
            return

        # Try with menu button
        self.__press(handle, 'menu')

    def __tap(self, handle, location):
        x, y = 0, 1
        cmd = [self.adb, '-s', handle, 'shell',
               'input', 'tap', str(location[x]), str(location[y])]
        self.__run(cmd)

    def __swipe(self, handle, start, end):
        x, y = 0, 1
        startx = start[x]
        starty = start[y]
        endx = end[x]
        endy = end[y]
        cmd = [self.adb, '-s', handle, 'shell',
               'input', 'swipe',
               str(startx), str(starty),
               str(endx), str(endy)]

        if self.__model(handle) != "LG-E460":
            # duration in ms.
            duration = 500
            cmd += [str(duration)]

        self.__run(cmd)

    def __multithreaded_cmd(self, cmd, **kwargs):
        devices = self.__get_devices()
        threads = []
        results = []

        class FuncThread(threading.Thread):
            def __init__(self, target, **kwargs):
                self._target = target
                self._kwargs = kwargs
                self.result = None
                threading.Thread.__init__(self)

            def run(self):
                self.result = self._target(**self._kwargs)

            def join(self):
                threading.Thread.join(self)
                return self.result
        print("running on {} devices.".format(len(devices)))
        for d in devices:
            t = FuncThread(target=cmd, handle=devices[d]["handle"], **kwargs)
            t.start()
            threads.append(t)

        for thread in threads:
            results.append(thread.join())

        return results

    def list_quick(self):
        """List the devices quickly."""
        devices = self.__get_devices()
        if not devices:
            print("No devices detected.")
            return

        for d in devices:
            print(d)
        print("-" * 20)
        print("total: {:3} device(s)".format(len(devices)))

    def list(self):
        """List the devices."""
        devices = self.__get_devices()
        if not devices:
            print("No devices detected.")
            return

        longest_line = 0
        for d in sorted(devices.keys()):
            handle = devices[d]['handle']
            devices[d]['version'] = "{}.{}.{}".format(*self.__version(handle))
            devices[d]['brand'] = self.__brand(handle)
            devices[d]['model'] = self.__model(handle)
            devices[d]['battery'] = self.__battery(handle)

            if self.__is_off(devices[d]['handle']):
                devices[d]['state'] = 'device off'
            else:
                screen_on = self.__is_screen_on(handle)
                devices[d]['state'] = \
                    'screen on' if screen_on else 'screen off'
            m = "{id:20} " \
                "{brand:10} " \
                "{model:12} " \
                "{version:6} " \
                "{battery:>3} % " \
                "{state:3}".format(id=d, **devices[d])
            print(m)
            longest_line = max(longest_line, len(m))
        lower_line = ("total: {:%s} device(s)" % (longest_line - 17)).format(
            len(devices))
        print("-" * len(lower_line))
        print(lower_line)

    def tap(self, location):
        """Tao on the screen."""
        self.__multithreaded_cmd(self.__tap, location=location)

    def swipe(self, start, end):
        """Swipe between two points."""
        self.__multithreaded_cmd(self.__swipe, start=start, end=end)

    def press(self, button):
        """Press a button."""
        self.__multithreaded_cmd(self.__press, button=button)

    def turn_screen(self, turn):
        """Turn the screen."""
        self.__multithreaded_cmd(self.__turn_screen, turn=turn)

    def install(self, apk):
        """Install apk."""
        def cmd(handle, apk):
            result = self.__install(handle, apk)
            stdout = result[0].splitlines()
            if stdout:
                self.__print(stdout[-1])
            else:
                print(result[1])
        self.__multithreaded_cmd(cmd, apk=apk)

    def uninstall(self, package_name):
        """Uninstall package."""
        self.__multithreaded_cmd(self.__uninstall, package_name=package_name)

    def has(self, package_name):
        """Check if package is installed."""
        state = self.__multithreaded_cmd(self.__has, package_name=package_name)
        _id, has = 0, 1
        result = [device[has] for device in state]
        if all(result):
            print("All the {} devices have {} installed.".format(
                len(result), package_name))
            return
        print("{}/{} devices does not have {} installed:".format(
            result.count(False),
            len(result),
            package_name))
        for device in state:
            if not device[has]:
                print("  {}".format(device[_id]))

    def running(self, package_name):
        """Check if application is running."""
        state = self.__multithreaded_cmd(
            self.__running, package_name=package_name)
        _id, running = 0, 1
        result = [device[running] for device in state]
        if all(result):
            print("All {} devices are running {}.".format(
                len(result), package_name))
            return
        print("{}/{} devices are not running {}:".format(
            result.count(False),
            len(result),
            package_name))
        for device in state:
            if not device[running]:
                print("  {}".format(device[_id]))

    def start(self, package_name, activity='MainActivity', action=None,
              data_string=None, parameters={}):
        """Start application."""
        self.__multithreaded_cmd(
            self.__start, package_name=package_name, activity=activity,
            action=action, data_string=data_string, parameters=parameters)

    def stop(self, package_name):
        """Stop application."""
        self.__multithreaded_cmd(self.__stop, package_name=package_name)

    def restart(self, package_name):
        """Restart application."""
        def cmd(handle, package_name):
            self.__stop(handle, package_name=package_name)
            self.__start(handle, package_name=package_name)

        self.__multithreaded_cmd(cmd, package_name=package_name)

    def shutdown(self):
        """Shutdown device."""
        self.__multithreaded_cmd(self.__shutdown)

    def turn_on(self):
        """Turn device on."""
        self.__multithreaded_cmd(self.__turn_on)

    def reboot(self):
        """Reboot device."""
        self.__multithreaded_cmd(self.__reboot)

    def unlock(self):
        """Unlock device."""
        self.__multithreaded_cmd(self.__unlock)

    def run_task(self, task):
        """Run a task."""
        def disable_verify_apps(handle):
            #Turn screen off and on to see which devices where affected.
            self.__turn_screen(handle, False)
            time.sleep(0.3)
            cmd = [self.adb, '-s', handle, 'shell', 'settings',
                   'put', 'global', 'package_verifier_enable', '0']
            self.__run(cmd)
            time.sleep(0.3)
            self.__turn_screen(handle, True)

        if task == 'disable_verify_apps':
            self.__multithreaded_cmd(disable_verify_apps)
        else:
            print("unknown task.")

    def shell(self, arguments, log_type):
        output_mutex = threading.Lock()
        output = {}

        def run_shell(handle):
            cmd = [self.adb, '-s', handle, 'shell'] + arguments
            out, err, ret = self.__run(cmd, timeout=None)

            output_mutex.acquire()
            output[handle] = out
            output_mutex.release()

        self.__multithreaded_cmd(run_shell)

        def file_logging(handle, content):
            fout = open("device_{id}.out".format(id=handle), 'w')
            fout.write(content);
            fout.close()

        def stdout_logging(handle, content):
            print("Device: {id}\nOutput:\n{entry}".format(id=handle,
                entry=content))

        for key, entry in output.items():
            if log_type == 'none':
                return
            elif log_type == 'stdout':
                stdout_logging(key, entry)
            elif log_type == 'file':
                file_logging(key, entry)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Handle multiple android devices simultaneously.')

    parser.add_argument('--adb', help='path to adb', default="adb")
    parser.add_argument(
        '--threads', type=int, help='the number of threads to use', default=10)

    parser.add_argument(
        '-s',
        '--specific_devices',
        help='Specific devices',
        default=[],
        action="append",
        nargs='?')

    subparsers = parser.add_subparsers(
        dest='command',
        help='Sub-command help')
    list_parser = subparsers.add_parser('list', help='List devices.')

    list_parser.add_argument(
        '-q', '--quick',
        help="A quick list of connected devices.",
        action='store_true')

    shell_parser = subparsers.add_parser('shell', help="Run a shell command.")
    shell_parser.add_argument(
        '--log_type',
        help="Specify the logging approach. NB: If file is specified, already "
             "existing files will be overwritten.",
        default='none',
        choices=['none', 'stdout', 'file'])
    shell_parser.add_argument(
        'shell_command',
        help='Command to be executed, including arguments',
        nargs='+')

    def coordinate(input):
        try:
            x, y = map(int, input.split(','))
            return x, y
        except:
            raise argparse.ArgumentTypeError("Coordinates must be x,y")

    tap_parser = subparsers.add_parser(
        'tap',
        help='Simulate a tap on the screen.')

    tap_parser.add_argument(
        'location',
        help="Coordinate (x,y)",
        type=coordinate)

    swipe_parser = subparsers.add_parser(
        'swipe',
        help='Simulate a swipe on the screen.')

    swipe_parser.add_argument(
        'start',
        help="The beginning of the swipe (x,y)",
        type=coordinate)

    swipe_parser.add_argument(
        'end',
        help="The end of the swipe (x,y)",
        type=coordinate)

    press_parser = subparsers.add_parser('press', help="Press a button.")
    press_parser.add_argument(
        'button',
        help="Button to press.",
        choices=BUTTONS.keys())

    subparsers.add_parser('shutdown', help="Shutdown device(s).")

    subparsers.add_parser('turn_on', help="Turn on device(s).")

    subparsers.add_parser('reboot', help="Reboot device(s).")

    screen_parser = subparsers.add_parser('screen', help="Control screen.")
    turn_values = {'on': True, 'off': False}
    screen_parser.add_argument(
        'turn',
        choices=turn_values.keys(),
        help='Turn the screen on or off.')

    install_parser = subparsers.add_parser('install', help='Install APK.')
    install_parser.add_argument('apk', help="APK to install.", nargs='?')

    uninstall_parser = subparsers.add_parser(
        'uninstall',
        help="Uninstall application.")
    uninstall_parser.add_argument(
        'package_name',
        help='Package name of the application to uninstall')

    has_parser = subparsers.add_parser(
        'has',
        help="Check if a certain application is installed.")
    has_parser.add_argument(
        'package_name',
        help='Package name of the application to check')

    running_parser = subparsers.add_parser(
        'running',
        help="Check if a certain application is running.")
    running_parser.add_argument(
        'package_name',
        help='Package name of the application to check')

    start_parser = subparsers.add_parser('start', help="Start application.")
    start_parser.add_argument(
        'package_name',
        help='Package name of the application to start')
    start_parser.add_argument(
        '--activity',
        default='MainActivity',
        help='Activity name of the application to start')
    start_parser.add_argument(
        '--action',
        default='',
        help='Action of the application to start')
    start_parser.add_argument(
        '-d', '--data_string',
        default='',
        help='data string to pass to the application')
    start_parser.add_argument(
        '-e', '--extras', metavar='key=value',
        nargs='*',
        default='',
        help='data string to pass to the application')

    stop_parser = subparsers.add_parser('stop', help="Stop application.")
    stop_parser.add_argument(
        'package_name',
        help='Package name of the application to stop')

    restart_parser = subparsers.add_parser(
        'restart', help="Restart application.")
    restart_parser.add_argument(
        'package_name',
        help='Package name of the application to restart')

    subparsers.add_parser('unlock', help="Unlocks the screen. Note, this "
                                         "command only works on Huawei "
                                         "T1_A21L units.")

    tasks = [
        "disable_verify_apps",
    ]

    task_parser = subparsers.add_parser('run', help="Run a predefined task.")
    task_parser.add_argument(
        'task',
        choices=tasks,
        help='The task to run.')

    args = parser.parse_args()
    adb = ADB(args.adb, args.threads, args.specific_devices)
    if 'extras' in dir(args):
        args.extras = \
            {extra.split('=')[0]: extra.split('=')[1] for extra in args.extras}

    {
        'list': lambda args: adb.list_quick() if args.quick else adb.list(),
        'tap': lambda args: adb.tap(args.location),
        'swipe': lambda args: adb.swipe(args.start, args.end),
        'press': lambda args: adb.press(args.button),
        'shutdown': lambda args: adb.shutdown(),
        'turn_on': lambda args: adb.turn_on(),
        'reboot': lambda args: adb.reboot(),
        'screen': lambda args: adb.turn_screen(turn_values[args.turn]),
        'install': lambda args: adb.install(args.apk),
        'uninstall': lambda args: adb.uninstall(args.package_name),
        'has': lambda args: adb.has(args.package_name),
        'running': lambda args: adb.running(args.package_name),
        'start': lambda args: adb.start(args.package_name, args.activity,
                                        args.action, args.data_string,
                                        args.extras),
        'stop': lambda args: adb.stop(args.package_name),
        'shell': lambda args: adb.shell(args.shell_command, args.log_type),
        'restart': lambda args: adb.restart(args.package_name),
        'unlock': lambda args: adb.unlock(),
        'run': lambda args: adb.run_task(args.task)
    }[args.command](args)


if __name__ == '__main__':
    main()
