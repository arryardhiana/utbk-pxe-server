# 🚀 UTBK PXE Server 2.0

**UTBK PXE Server** adalah platform orkestrasi PXE Boot modern yang dirancang untuk pendistribusian sistem operasi secara cepat dan efisien melalui jaringan lokal maupun antar-network. Aplikasi ini mengotomatisasi proses ekstraksi ISO, konfigurasi iPXE, dan penyajian file sistem langsung dari RAM (tmpfs) untuk performa maksimal.

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

Agar client dapat booting melalui server ini, Anda perlu mengatur DHCP Options pada router anda.

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

---

## 📄 Lisensi
Sistem ini dikembangkan untuk kebutuhan operasional UTBK. Silakan digunakan secara bertanggung jawab.
