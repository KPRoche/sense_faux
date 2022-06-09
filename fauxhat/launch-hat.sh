#!/bin/bash

# Shell script to do final environment set up and launch logger program

# device i2c-1 only appears after the container starts, so change ownership
echo 'authorizing connection to i2c devices'
echo $PIHAT | sudo -S chown :input /dev/i2c-1
echo 'authorizing connection to joystick device'
sudo -S chown :input /dev/input/event*
#echo 'mounting usb drive'
#sudo mount /dev/sda1 ~/usb-drive
unset PIHAT


# start the logger script
python3 sendtonodered.meye.py


