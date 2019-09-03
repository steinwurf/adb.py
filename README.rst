======
adb.py
======

`adb.py` allow tasks to be performed on multiple connected Android devices
simultaneously.
This is very useful when you need to perform the same task on many devices
e.g. installing an `apk`.

.. contents:: Table of Contents:
   :local:

Usage
=====

The `adb.py` project wraps the `Android Debug Bridge
<https://developer.android.com/studio/command-line/adb.html>`_ (`adb`) tool
shipped with the Android SDK. After installing Android SDK you can find the
adb tool in `<android-sdk>/platform-tools`.

Basic commands
==============

Unless `adb` is available in your path, you need to specify where it can be
found using `--adb path-to-platform-tools`.

Help
----

To see the available commands you can write::

    ./adb.py --help

All commands have addition sub-help menus, e.g. you can access additional help
for the `list` command by writing::

    ./adb.py list --help


Listing available devices
-------------------------

There are two ways of listing the available devices: `quick` displays only
minimal information whereas standard displays more information such as battery
level etc.

Example using `--quick` or `-q`::

    ./adb.py --adb ../../android-sdk/platform-tools/adb list --quick

Or to get more verbose information without `--quick`::

    ./adb.py --adb ../../android-sdk/platform-tools/adb list

Troubleshooting: `unauthorized device`
......................................

If you see a message `unauthorized device` when listing connected devices,
make sure you've accepted the prompt asking you to "Allow USB debugging".

Installing an APK
-----------------

One common task is to install an application on the connected devices::

    ./adb.py --adb ~/android-sdk/platform-tools/adb install <APK>

Troubleshooting: `Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]`
...............................................................

If you see this message during installation it means that the application was
already installed, most likely signed with a different key. The `solution
<http://stackoverflow.com/a/13160869>`_ is simply to first `uninstall` the
application, see Section `Uninstalling an apk`_.

Uninstalling an APK
-------------------

To uninstall an already installed application with the package name
`com.company.app`::

    ./adb.py --adb ~/android-sdk/platform-tools/adb uninstall com.company.app

Troubleshooting: Get package name from APK
..........................................

You can get the package name from an `apk` by running (`stackoverflow answer
<http://stackoverflow.com/a/6289168>`_)::

    aapt dump badging <path-to-apk> | grep package:\ name

The `aapt` utility is available in `<android-sdk>/build-tools/<version>`.
