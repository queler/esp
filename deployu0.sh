ls *.py|xargs -i{} mpremote connect /dev/ttyUSB0 cp {} :{}
