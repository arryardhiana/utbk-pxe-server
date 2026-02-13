# 🚀 UTBK PXE Server 2.0

**UTBK PXE Server** adalah platform orkestrasi PXE Boot yang dirancang untuk pendistribusian sistem operasi secara cepat dan efisien melalui jaringan lokal maupun antar-network. Aplikasi ini mengotomatisasi proses ekstraksi ISO, konfigurasi iPXE, dan penyajian file sistem langsung dari RAM (tmpfs) untuk performa maksimal.

![Dashboard Preview](assets/dashboard.png)

---

## 🛠️ Cara Instalasi

### 0. Instalasi Docker (Jika belum ada):
Jika server Anda baru, jalankan perintah satu baris ini untuk instalasi Docker otomatis:
```bash
curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER
```

### 1. Persyaratan:
- Perangkat dengan interface jaringan fisik (ens/eth)
- Akses Root/Sudo
- **Penting**: Pastikan port `80` pada host tidak sedang digunakan oleh aplikasi lain (seperti Apache/Nginx bawaan) agar server PXE dapat berjalan normal.

### 2. Jalankan Server:
   ```bash
   git clone https://github.com/arryardhiana/utbk-pxe-server.git
   cd utbk-pxe-server
   
   # Jalankan Orchestrator (Bawaan Tanpa Netdata)
   docker compose up -d --build
   ```

### 3. Monitoring Opsional (Netdata):
Jika Anda membutuhkan monitoring sistem yang mendalam, jalankan perintah ini:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
   ```

4. **Akses Dashboard**:
   - **Main Dashboard**: `http://ip-server:8000`
   - **Netdata Monitoring**: `http://ip-server:19999` (Hanya jika monitoring aktif)

---

## ✨ Fitur Utama

- **Built-in Monitoring**: Pantau statistik client (Min/Max) dan kecepatan network (Real-time & 6h history) langsung di dashboard utama tanpa database.
- **Optional Netdata**: Monitoring mendalam tingkat OS yang dapat diaktifkan melalui port `19999`.
- **High Performance**: Penyajian file sistem langsung dari RAM (tmpfs) untuk mempercepat proses loading client.
- **Auto Ingestion**: Ekstraksi ISO otomatis ke dalam struktur direktori PXE.

---

## 🛰️ Contoh Konfigurasi MikroTik (DHCP Server)

Agar client dapat booting melalui server ini, Anda perlu mengatur DHCP Options pada router anda.

### Melalui Winbox/Terminal:
Masuk ke menu `/ip dhcp-server network` dan atur parameter berikut pada jaringan yang digunakan:

```bash
# Ganti <SERVER_IP> dengan IP Server UTBK PXE Anda
/ip dhcp-server network
set [find address=192.168.88.0/24] \
    next-server=<SERVER_IP> \
    boot-file-name=bootx64.efi
```

### Penjelasan Parameter:
- **Next Server (Option 66)**: Alamat IP Host tempat UTBK PXE Server berjalan.
- **Boot File Name (Option 67)**:
  - Gunakan `bootx64.efi` (Standard UEFI).

---

## 📄 Lisensi & Hak Cipta
Sistem ini dikembangkan oleh **Arry A - Universitas Padjadjaran**.  
Copyright © 2026. All rights reserved.

---
*Terima kasih telah menggunakan UTBK PXE Server.*
