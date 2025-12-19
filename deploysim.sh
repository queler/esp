sudo pkill socat
bash bridge &
ls *.py wifi.json|xargs -i{} mpremote connect /dev/ttyRFC2217 cp {} :{}
