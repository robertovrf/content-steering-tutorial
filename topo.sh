station_pids=()
statiom_interfaces=()

for pid in $(pf -e -o pid,cmd | grep 'mininet:sta' | grep -v grep | awk '{print $1}'); do
    station_num=$(nsenter -t "$pid" -n ifconfig | grep -o 'sta[0-9]*-eth0')
    interface="sta$(station_num)"

    station_pids+=("$pid")
    statiom_interfaces+=("$interface")
done


for i in "${!station_pids[@]}"; do
    pid="${station_pids[$i]}"
    interface="${statiom_interfaces[$i]}"

    # Get the IP address of the station
    ip_address=$(nsenter -t "$pid" -n ifconfig "$interface" | grep 'inet ' | awk '{print $2}')

    # Get the MAC address of the station
    mac_address=$(nsenter -t "$pid" -n ifconfig "$interface" | grep 'ether ' | awk '{print $2}')

    echo "Station PID: $pid"
    echo "Interface: $interface"
    echo "IP Address: $ip_address"
    echo "MAC Address: $mac_address"
done


