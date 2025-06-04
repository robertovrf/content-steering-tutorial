#!/bin/bash

station_pids=()
station_interfaces=()


# Iterate over each station process
for pid in $(ps -e -o pid,cmd | grep 'mininet:sta' | grep -v grep | awk '{print $1}'); do
    station_num=$(nsenter -t "$pid" -n ifconfig | grep -o 'sta[0-9]*-eth0' | grep -o 'sta[0-9]*' | grep -o '[0-9]*')
    interface="sta${station_num}-eth0"

    station_pids+=("$pid")
    station_interfaces+=("$interface")
done

# Execute tc qdisc commands for each collected station PID
for i in "${!station_pids[@]}"; do
    pid="${station_pids[$i]}"
    interface="${station_interfaces[$i]}"
    
    mnexec -a "$pid" tc qdisc add dev "$interface" root handle 1: htb default 1
    mnexec -a "$pid" tc class add dev "$interface" parent 1: classid 1:1 htb rate 20mbit quantum 1500
done

# Open the trace file and read bandwidth values
trace_file="trace.txt"
if [[ ! -f "$trace_file" ]]; then
    echo "Trace file not found!"
    exit 1
fi

# Read the trace file line by line
while IFS= read -r bw; do
    for i in "${!station_pids[@]}"; do
        pid="${station_pids[$i]}"
        interface="${station_interfaces[$i]}"
        
        mnexec -a "$pid" tc qdisc del dev "$interface" root
        mnexec -a "$pid" tc qdisc add dev "$interface" root netem rate "$bw"kbit loss 0.09%
    done

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Set bandwidth $bw on all interfaces" >> "log_trace.txt"
    sleep 1
done < "$trace_file"
