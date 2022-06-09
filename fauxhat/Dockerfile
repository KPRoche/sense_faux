# if this works I can build a new image without having to recompile everything.
FROM quay.io/kproche0/rpi-sci-hat:stream8
MAINTAINER Kevin P Roche, kproche@us.ibm.com

#
#RUN rm -rf examples efficientdet_lite0.tflite 

COPY /sense_faux /usr/local/lib/python3.6/site-packages/sense_faux
COPY /.sensehat /root/.sensehat/

COPY . /app

WORKDIR /app

#RUN python3 -m pip install -U  netifaces --user
ARG tz="America/Los_Angeles"
ENV TZ=$tz

ENV LOGGER_DELAY=$logger_delay
ENV CAM_ROTATION=$cam_rotation

EXPOSE:5000

#CMD ["/bin/bash","launch-hat.sh"]
CMD ["/bin/bash"]

#--------------------------Notes -----------------------------
# Container must be run in privileged mode or have explicit access to devices
#		/dev/sda1 /dev/fb1 /dev/video0 /input/event
#sudo podman run --privileged -it <image> bash

#need to make directory /media/usbdrive
#need to mount /dev/sda-1



