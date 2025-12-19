sudo pkill socat
bash bridge &
ls *.py|xargs -i{} mpremote connect /dev/ttyRFC2217 cp {} :{}
