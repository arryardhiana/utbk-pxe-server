# 🚀 UTBK PXE Server 2.0

**UTBK PXE Server** adalah platform orkestrasi PXE Boot modern yang dirancang untuk pendistribusian sistem operasi secara cepat dan efisien melalui jaringan lokal maupun antar-network. Aplikasi ini mengotomatisasi proses ekstraksi ISO, konfigurasi iPXE, dan penyajian file sistem langsung dari RAM (tmpfs) untuk performa maksimal.

---

## ✨ Fitur Utama
- **Auto ISO Ingestion**: Cukup upload file ISO, sistem akan otomatis mengekstrak Kernel, Initrd, dan RootFS.
- **RAM-Speed Delivery**: Semua komponen boot dilayani langsung dari RAM menggunakan Nginx dengan optimasi `sendfile`.
- **Smart IP Autodetect**: Mendeteksi interface jaringan host secara otomatis (ens/eth) pada booting pertama.
- **Premium Dashboard**: UI modern dengan fitur **Dark/Light Mode** dan **Live Traffic Monitor**.
- **Real-time Metrics**: Memantau penggunaan RAM, Cache, dan jumlah client PXE unik dalam jendela waktu 15 detik.
- **Cross-Network Optimized**: Penyesuaian konfigurasi untuk kestabilan transfer data pada infrastruktur jaringan yang kompleks (VLAN/VPN).

---

## 🛠️ Cara Instalasi

1. **Persyaratan**:
   - Docker & Docker Compose
   - Perangkat dengan interface jaringan fisik (ens/eth)

2. **Clone & Jalankan**:
   ```bash
   git clone https://github.com/arryardhiana/utbk-pxe-server.git
   cd utbk-pxe-server
   docker compose up -d --build
   ```

3. **Akses Dashboard**:
   Buka browser dan akses `http://ip-server:8000`

---

## 🛰️ Konfigurasi MikroTik (DHCP Server)

Agar client dapat booting melalui server ini, Anda perlu mengatur DHCP Options pada MikroTik Anda.

### Melalui Winbox/Terminal:
Masuk ke menu `/ip dhcp-server network` dan atur parameter berikut pada jaringan yang digunakan:

```bash
# Ganti 10.8.0.70 dengan IP Server UTBK PXE Anda
/ip dhcp-server network
set [find address=192.168.88.0/24] \
    next-server=10.8.0.70 \
    boot-file-name=bootx64.efi
```

### Penjelasan Parameter:
- **Next Server (Option 66)**: Alamat IP Host tempat UTBK PXE Server berjalan.
- **Boot File Name (Option 67)**:
  - Gunakan `bootx64.efi` (Standard UEFI).
  - Sistem ini menggunakan `snponly.efi` yang di-rename menjadi `bootx64.efi` untuk performa terbaik menggunakan driver motherboard.

---

## 📂 Struktur Direktori
- `/frontend`: Dashboard UI (HTML, Tailwind, Alpine.js).
- `/backend`: API server menggunakan FastAPI (Python).
- `/data-source`: Penyimpanan permanen ISO dan konfigurasi.
- `/tftpboot`: Direktori layanan TFTP untuk iPXE binaries.
- `/scripts`: Konfigurasi Nginx dan Entrypoint sistem.

---

## 📄 Lisensi
Sistem ini dikembangkan untuk kebutuhan operasional UTBK. Silakan digunakan secara bertanggung jawab.
