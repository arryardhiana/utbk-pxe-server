#!/bin/sh
set -e

# Install needed packages
apk add --no-cache dnsmasq iproute2 > /dev/null

# Find the network interface (ignoring lo and docker/bridge interfaces)
# Since network_mode is host, this sees the host's interfaces
DEFAULT_IFACE=$(ip -4 route show default | awk '/dev/ {for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -n 1)

if [ -z "$DEFAULT_IFACE" ]; then
    # Fallback: take the first non-virtual link
    DEFAULT_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep -vE '^(lo|docker|br-|veth)' | head -n 1 | tr -d ' ')
fi

if [ -z "$DEFAULT_IFACE" ]; then
    echo "ERROR: Could not detect a physical network interface."
    exit 1
fi

echo "Auto-detected interface: $DEFAULT_IFACE"

# We use the config template mounted and copy it so we can modify it
cp /etc/dnsmasq.conf.template /etc/dnsmasq.conf

# Handle DNS toggle based on ENABLE_DNS environment variable
sed -i '/^port=0/d' /etc/dnsmasq.conf
if [ "$ENABLE_DNS" = "true" ]; then
    echo "DNS is ENABLED (ENABLE_DNS=true). Dnsmasq will listen on port 53."
else
    echo "DNS is DISABLED (ENABLE_DNS!=true). Setting port=0 to disable DNS feature."
    echo "port=0" >> /etc/dnsmasq.conf
fi

# Remove any existing interface line so we don't duplicate
sed -i '/^interface=/d' /etc/dnsmasq.conf

# Add the correctly detected interface
echo "interface=$DEFAULT_IFACE" >> /etc/dnsmasq.conf

echo "Starting dnsmasq..."
exec dnsmasq -k
