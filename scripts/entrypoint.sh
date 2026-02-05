#!/bin/bash

# Prepare TFTP binaries
echo "Preparing TFTP binaries..."
cp /tmp/ipxe/snponly.efi /var/lib/tftpboot/bootx64.efi || true

# Start TFTP server with verbose logging
echo "Starting TFTP server (verbose mode)..."
/usr/sbin/in.tftpd --foreground --user root --address 0.0.0.0:69 --secure -L -vvv /var/lib/tftpboot &

# Start Nginx
echo "Starting Nginx..."
nginx &

# Start FastAPI
echo "Starting FastAPI backend..."
cd /app
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
