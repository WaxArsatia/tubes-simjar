# Desain Analisis QoS NS-3: Variasi Queue Buffer

## Judul

Analisis Pengaruh Variasi Ukuran Queue Buffer terhadap Packet Loss, Throughput, dan Delay pada Topologi Jaringan Redundan Menggunakan NS-3.

## Tujuan

Membangun paket eksperimen NS-3 yang mengukur pengaruh variasi ukuran queue buffer terhadap QoS jaringan komputer. Paket harus menghasilkan source simulasi, data CSV dari minimal 10 sampel, dan grafik QoS yang konsisten dengan data.

## Ruang Lingkup

Deliverable:

- Source simulasi NS-3 C++.
- Script otomatis untuk menjalankan 10 variasi buffer.
- CSV hasil eksperimen.
- Grafik PNG untuk throughput, delay, packet loss ratio, packet loss count, dan queue disc drops.

Di luar scope:

- Implementasi protokol routing custom.
- GUI simulasi.
- Analisis statistik lanjutan seperti confidence interval.
- Perbandingan TCP vs UDP.

## Hipotesis

Hipotesis utama:

Semakin besar ukuran queue buffer, semakin rendah packet loss ratio pada link bottleneck sampai titik tertentu. Namun delay rata-rata dapat meningkat karena paket menunggu lebih lama di antrean.

Hipotesis nol:

Variasi ukuran queue buffer tidak memengaruhi packet loss ratio, throughput, atau delay rata-rata secara bermakna pada skenario simulasi yang sama.

## Variabel Penelitian

Variabel bebas:

- Ukuran queue buffer pada queue disc bottleneck, dalam satuan packet.
- Nilai sampel: `1, 5, 10, 20, 50, 100, 200, 500, 750, 1000`.
- Setiap nilai buffer adalah satu sampel variasi parameter utama. Script harus menjaga seed dan parameter lain tetap sama agar perubahan QoS dapat dikaitkan ke ukuran buffer.
- Script boleh menyediakan opsi `--repetitions` untuk menjalankan beberapa seed per buffer, tetapi output default harus tetap memenuhi 10 sampel utama sesuai daftar buffer.

Variabel terikat:

- Throughput flow utama dalam Mbps.
- Delay rata-rata flow utama dalam ms.
- Packet loss count flow utama.
- Packet loss ratio flow utama dalam persen.
- Queue disc drops pada `FifoQueueDisc` bottleneck.

Variabel kontrol:

- Topologi jaringan.
- Jumlah router dan host.
- Bandwidth tiap link.
- Delay tiap link.
- Durasi simulasi.
- Ukuran packet.
- Rate traffic utama.
- Rate background traffic.
- Waktu mulai dan selesai aplikasi.
- Routing global NS-3.
- Seed simulasi.

## Topologi

Topologi wajib memiliki minimal 5 router dan 5 host dengan jalur redundan berbentuk loop.

Node:

- Router: `R0`, `R1`, `R2`, `R3`, `R4`.
- Host: `H0`, `H1`, `H2`, `H3`, `H4`.

Koneksi host ke router:

- `H0 -- R0`
- `H1 -- R1`
- `H2 -- R2`
- `H3 -- R3`
- `H4 -- R4`

Koneksi antar-router:

- `R0 -- R1`
- `R1 -- R2`
- `R2 -- R3`
- `R3 -- R4`
- `R4 -- R0`
- `R0 -- R2`
- `R1 -- R3`

Loop utama terbentuk oleh `R0-R1-R2-R3-R4-R0`. Link `R0-R2` dan `R1-R3` menjadi jalur redundan tambahan.

## Parameter Simulasi

Parameter default:

- Simulator: NS-3, dikompilasi dengan `ns3-compile`.
- Link host-router umum: point-to-point `100Mbps`, `2ms`.
- Link bottleneck akses tujuan: `R4 -- H4`, point-to-point `2Mbps`, `10ms`.
- Link router-router umum: point-to-point `10Mbps`, `5ms`.
- Queue disc bottleneck: `ns3::FifoQueueDisc` dari traffic-control module pada netdevice `R4 -> H4`.
- Nilai `MaxSize` queue disc bottleneck harus diset dari argumen `--bufferPackets=<N>` menjadi format packet, misalnya `1p`, `10p`, `100p`, sampai `1000p`.
- Device queue selain queue disc bottleneck tidak boleh menjadi variabel bebas. Device queue bottleneck `R4 -> H4` diset kecil (`1p`) agar antrean aktif berada di `FifoQueueDisc` yang diuji.
- Packet size: `1024 bytes`.
- Durasi simulasi: `25s`.
- Traffic start: `1s`.
- Traffic stop: `19s`.
- Measurement duration: `trafficStop - trafficStart = 18s`.
- Flow utama: UDP CBR `H0 -> H4`.
- Rate flow utama: `1Mbps`.
- Background flow: UDP CBR `H1 -> H4`, `H2 -> H4`, `H3 -> H4`.
- Rate background per flow: `0.5Mbps`.
- Total offered load menuju `H4`: `2.5Mbps`, sedikit melebihi bottleneck `2Mbps` agar efek ukuran buffer terlihat tanpa membuat grafik flat.

## Pengukuran QoS

Monitoring memakai `FlowMonitorHelper` dan `FlowMonitor`.

Flow utama diidentifikasi dari alamat IP source `H0` dan destination `H4`.

Metrik:

- Throughput Mbps = `rxBytes * 8 / measurementDuration / 1_000_000`, dengan `measurementDuration = trafficStop - trafficStart = 18s`.
- Delay rata-rata ms = `delaySum / rxPackets * 1000`.
- Packet loss count = `txPackets - rxPackets`.
- Packet loss ratio persen = `(txPackets - rxPackets) / txPackets * 100`.
- Queue disc drops = `FifoQueueDisc` drop count dengan reason `FifoQueueDisc::LIMIT_EXCEEDED_DROP`.

Jika `rxPackets == 0`, delay rata-rata ditulis `0` dan kondisi dicatat sebagai kehilangan total.

## Data dan Grafik

File data utama:

- `results/qos_results.csv`

Kolom CSV:

- `buffer_packets`
- `tx_packets`
- `rx_packets`
- `lost_packets`
- `queue_disc_drops`
- `packet_loss_ratio_percent`
- `throughput_mbps`
- `average_delay_ms`
- `run_seed`
- `flow_id`

Grafik:

- `results/throughput_vs_buffer.png`
- `results/delay_vs_buffer.png`
- `results/packet_loss_ratio_vs_buffer.png`
- `results/lost_packets_vs_buffer.png`
- `results/queue_disc_drops_vs_buffer.png`

Semua grafik memakai sumbu X `buffer_packets`.

## Arsitektur File

File yang akan dibuat:

- `src/queue_buffer_qos.cc`
  - Mendefinisikan topologi, traffic, queue buffer, FlowMonitor, dan output satu baris CSV per run.
- `scripts/run_experiments.py`
  - Mengompilasi simulasi dengan `ns3-compile`.
  - Menjalankan 10 skenario buffer.
  - Menggabungkan output menjadi `results/qos_results.csv`.
- `scripts/plot_results.py`
  - Membaca CSV.
  - Membuat 5 grafik PNG.
- `README.md`
  - Instruksi compile, run, dan struktur output.

## Validasi

Validasi minimum:

- `ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos` berhasil.
- `python scripts/run_experiments.py` menghasilkan 10 baris data untuk buffer `1,5,10,20,50,100,200,500,750,1000`.
- CSV tidak kosong dan memiliki kolom yang ditentukan.
- Setiap nilai `buffer_packets` muncul tepat satu kali pada output default.
- Semua nilai `tx_packets` lebih besar dari 0.
- Semua nilai `flow_id` lebih besar dari 0.
- Kolom `queue_disc_drops` tersedia.
- Nilai `queue_disc_drops` dan `average_delay_ms` harus bervariasi antar ukuran buffer pada output default agar hasil representatif.
- Flow utama berhasil diidentifikasi sebagai traffic `H0 -> H4`; jika tidak, program harus keluar dengan error non-zero.
- Topologi memenuhi syarat 5 router, 5 host, loop `R0-R1-R2-R3-R4-R0`, dan link redundan `R0-R2`, `R1-R3`.
- Semua traffic menuju `H4` melewati link akses `R4 -> H4`, sehingga queue disc bottleneck pasti berada pada jalur flow utama dan background.
- Semua grafik PNG berhasil dibuat.

## Risiko dan Mitigasi

Risiko:

- Packet loss tidak muncul pada buffer besar.

Mitigasi:

- Bottleneck ditempatkan pada link `R4 -> H4`, sehingga semua flow menuju `H4` wajib melewati bottleneck tersebut. Total offered load dibuat sedikit lebih besar dari kapasitas bottleneck, dan device queue bottleneck dibuat `1p`, sehingga antrean terjadi pada `FifoQueueDisc`.

Risiko:

- Delay melonjak sangat besar pada buffer tinggi.

Mitigasi:

- Durasi simulasi dibuat lebih panjang dari traffic stop agar antrean pada buffer besar punya waktu drain sebelum statistik final.

## Keputusan Desain

- Memakai UDP CBR karena packet loss, delay, dan throughput lebih mudah dibandingkan antar-sampel.
- Memakai 10 variasi queue buffer deterministik agar langsung memenuhi syarat jumlah sampel.
- Memakai background traffic ringan agar bottleneck mengalami mild congestion dan kurva tidak flat.
- Memakai `queue_disc_drops` sebagai metrik tambahan agar efek langsung ukuran queue buffer terlihat.
- Memakai CSV dan grafik otomatis agar hasil dapat direproduksi.
