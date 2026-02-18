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

# Fix previously corrupted munin-node.conf if any
sed -i '/\[nginx\*\]/d' /etc/munin/munin-node.conf 2>/dev/null || true
sed -i '/env.url http:\/\/127.0.0.1\/nginx_status/d' /etc/munin/munin-node.conf 2>/dev/null || true

# Configure Nginx plugin environment (correct place)
echo "Configuring Nginx plugin environment..."
mkdir -p /etc/munin/plugin-conf.d
echo -e "[nginx*]\nenv.url http://127.0.0.1/nginx_status" > /etc/munin/plugin-conf.d/nginx

# Auto-configure Munin plugins
echo "Configuring Munin plugins..."
munin-node-configure --shell | sh 2>/dev/null || true

# Force-enable Nginx plugins if not already enabled
for p in nginx_status nginx_request; do
    if [ ! -L /etc/munin/plugins/$p ]; then
        ln -s /usr/share/munin/plugins/$p /etc/munin/plugins/$p 2>/dev/null || true
    fi
done

# Fix Munin master config (illegal characters like underscores in hostname)
echo "Fixing Munin master config..."
sed -i "s/\[$(hostname)\]/\[pxe-node\]/g" /etc/munin/munin.conf 2>/dev/null || true
# Catch-all for any section name with underscores
sed -i 's/\[\([^]]*\)_\([^]]*\)\]/\[\1-\2\]/g' /etc/munin/munin.conf 2>/dev/null || true

# Explicitly set htmldir to match our Nginx config
sed -i "s|#htmldir.*|htmldir /var/www/munin|g" /etc/munin/munin.conf
sed -i "s|^htmldir.*|htmldir /var/www/munin|g" /etc/munin/munin.conf

# Final fallback: ensure at least one valid node exists if parsing still fails
if ! grep -q "\[pxe-node\]" /etc/munin/munin.conf; then
    echo -e "\n[pxe-node]\n    address 127.0.0.1\n    use_node_name yes" >> /etc/munin/munin.conf
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
