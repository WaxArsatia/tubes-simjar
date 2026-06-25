# Analisis QoS NS-3: Variasi Queue Buffer

Judul: Analisis Pengaruh Variasi Ukuran Queue Buffer terhadap Packet Loss, Throughput, dan Delay pada Topologi Jaringan Redundan Menggunakan NS-3.

## Isi

- `src/queue_buffer_qos.cc`: simulasi NS-3.
- `scripts/run_experiments.py`: compile dan menjalankan 10 sampel buffer.
- `scripts/plot_results.py`: membuat grafik PNG.
- `results/qos_results.csv`: data hasil eksperimen, termasuk drop pada queue disc.

## Topologi

Simulasi memakai 5 router dan 5 host. Router membentuk loop `R0-R1-R2-R3-R4-R0` dengan link redundan `R0-R2` dan `R1-R3`. Bottleneck ditempatkan pada link `R4 -> H4`.

Queue buffer yang diuji adalah `ns3::FifoQueueDisc` pada arah `R4 -> H4`. Device queue bottleneck dibuat kecil (`1p`) supaya antrean utama terjadi di queue disc yang menjadi variabel bebas.

## Variabel

- Variabel bebas: ukuran queue buffer `1,5,10,20,50,100,200,500,750,1000` packet.
- Variabel terikat: throughput, delay rata-rata, packet loss count, packet loss ratio, dan queue disc drops.
- Variabel kontrol: topologi, bandwidth, delay, packet size, traffic rate, durasi, routing, seed.

Traffic default dibuat mild congestion agar efek ukuran buffer terlihat:

- Flow utama `H0 -> H4`: `1Mbps`.
- Tiga background flow menuju `H4`: masing-masing `0.5Mbps`.
- Total offered load menuju bottleneck: `2.5Mbps`.
- Kapasitas bottleneck `R4 -> H4`: `2Mbps`.
- Traffic berhenti pada `19s`, sedangkan simulasi berhenti pada `25s` agar buffer besar punya waktu drain sebelum statistik final.

## Cara Menjalankan

Compile saja:

```bash
ns3-compile src/queue_buffer_qos.cc -o build/queue_buffer_qos
```

Jalankan satu skenario:

```bash
./build/queue_buffer_qos --bufferPackets=10 --runSeed=1 --csvHeader=true
```

Jika memakai `--simulationStop`, nilainya harus lebih besar dari waktu traffic stop tetap `19s`.

Jalankan semua eksperimen dan grafik:

```bash
python scripts/run_experiments.py
```

## Output

- `results/qos_results.csv`
- `results/throughput_vs_buffer.png`
- `results/delay_vs_buffer.png`
- `results/packet_loss_ratio_vs_buffer.png`
- `results/lost_packets_vs_buffer.png`
- `results/queue_disc_drops_vs_buffer.png`

## Verifikasi

```bash
python -m unittest tests/test_experiment_scripts.py -v
python scripts/run_experiments.py
```

CSV default harus berisi 10 baris data untuk buffer `1` sampai `1000` packet. Kolom `queue_disc_drops` dan `average_delay_ms` harus bervariasi antar ukuran buffer agar grafik menunjukkan pengaruh variabel bebas.
