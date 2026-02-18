FROM python:3.11-alpine

# Install system dependencies
RUN apk add --no-cache \
    nginx \
    tftp-hpa \
    bash \
    procps \
    iproute2 \
    curl \
    p7zip \
    tzdata \
    munin \
    munin-node \
    perl-cgi \
    perl-libwww

# iPXE UEFI setup
RUN mkdir -p /tmp/ipxe && \
    curl -o /tmp/ipxe/snponly.efi https://boot.ipxe.org/x86_64-efi/snponly.efi

# Create directories
RUN mkdir -p /app/uploads /ram-disk /var/lib/tftpboot /run/nginx /var/www/munin /var/run/munin /var/log/munin && \
    addgroup nginx munin && \
    chmod -R 755 /var/www/munin && \
    chown -R munin:munin /var/lib/munin /var/www/munin /var/run/munin /var/log/munin

# Copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY backend /app/backend
COPY frontend /app/frontend

# Copy configurations
COPY scripts/entrypoint.sh /app/entrypoint.sh
COPY scripts/nginx.conf /etc/nginx/nginx.conf

# Set workdir
WORKDIR /app

# Ports
EXPOSE 80 69/udp 8000

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
