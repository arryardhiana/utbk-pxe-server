#!/bin/bash

# Prepare TFTP binaries
echo "Preparing TFTP binaries..."
cp /tmp/ipxe/snponly.efi /var/lib/tftpboot/bootx64.efi || true

# Start TFTP server
echo "Starting TFTP server..."
/usr/sbin/in.tftpd --foreground --user root --address 0.0.0.0:69 --secure -L -vvv /var/lib/tftpboot &

# Start Nginx
echo "Starting Nginx..."
if [ ! -f /var/www/munin/index.html ]; then
    echo "<html><head><meta http-equiv='refresh' content='10'></head><body><h1>Munin is initializing...</h1><p>Please wait 5 minutes for the first graph generation.</p></body></html>" > /var/www/munin/index.html
    chown munin:munin /var/www/munin/index.html
fi
nginx &

# Initialize Munin node
echo "Initializing Munin node..."
if [ ! -f /etc/munin/munin-node.conf.bak ]; then
    cp /etc/munin/munin-node.conf /etc/munin/munin-node.conf.bak
    echo "allow ^127\.0\.0\.1$" >> /etc/munin/munin-node.conf
    echo "allow ^::1$" >> /etc/munin/munin-node.conf
fi

# Start Munin Node
echo "Starting Munin node..."
munin-node &

# Start Munin Master (cron simulator)
echo "Starting Munin master loop..."
(
    while true; do
        echo "Updating Munin graphs..."
        su -s /bin/sh munin -c /usr/bin/munin-cron
        sleep 300
    done
) &

# Start FastAPI
echo "Starting FastAPI backend..."
cd /app
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
