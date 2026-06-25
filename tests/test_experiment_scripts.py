import unittest
from pathlib import Path


class ExperimentScriptTests(unittest.TestCase):
    def test_buffer_samples_are_required_default_values(self):
        from scripts.run_experiments import BUFFER_SAMPLES

        self.assertEqual(BUFFER_SAMPLES, [1, 5, 10, 20, 50, 100, 200, 500, 750, 1000])

    def test_build_simulation_command_uses_expected_cli_args(self):
        from scripts.run_experiments import build_simulation_command

        command = build_simulation_command(Path("build/queue_buffer_qos"), 20, 3)
        self.assertEqual(command[0], "build/queue_buffer_qos")
        self.assertIn("--bufferPackets=20", command)
        self.assertIn("--runSeed=3", command)
        self.assertIn("--csvHeader=true", command)

    def test_parse_simulation_csv_requires_one_data_row(self):
        from scripts.run_experiments import parse_simulation_csv

        stdout = (
            "buffer_packets,tx_packets,rx_packets,lost_packets,"
            "queue_disc_drops,packet_loss_ratio_percent,throughput_mbps,"
            "average_delay_ms,run_seed,flow_id\n"
            "10,100,90,10,8,10.000000,0.040960,12.500000,1,7\n"
        )
        row = parse_simulation_csv(stdout)
        self.assertEqual(row["buffer_packets"], "10")
        self.assertEqual(row["lost_packets"], "10")

    def test_validate_rows_rejects_missing_buffer_sample(self):
        from scripts.run_experiments import BUFFER_SAMPLES, validate_rows

        rows = []
        fieldnames = [
            "buffer_packets",
            "tx_packets",
            "rx_packets",
            "lost_packets",
            "packet_loss_ratio_percent",
            "throughput_mbps",
            "average_delay_ms",
            "run_seed",
            "flow_id",
        ]
        for buffer_packets in BUFFER_SAMPLES[:-1]:
            row = dict.fromkeys(fieldnames, "1")
            row["buffer_packets"] = str(buffer_packets)
            rows.append(row)

        with self.assertRaisesRegex(ValueError, "Expected 10 rows"):
            validate_rows(rows, repetitions=1)

    def test_fieldnames_include_queue_disc_drops(self):
        from scripts.run_experiments import FIELDNAMES

        self.assertIn("queue_disc_drops", FIELDNAMES)

    def test_validate_rows_requires_queue_disc_drop_column(self):
        from scripts.run_experiments import BUFFER_SAMPLES, validate_rows

        rows = []
        fieldnames = [
            "buffer_packets",
            "tx_packets",
            "rx_packets",
            "lost_packets",
            "packet_loss_ratio_percent",
            "throughput_mbps",
            "average_delay_ms",
            "run_seed",
            "flow_id",
        ]
        for buffer_packets in BUFFER_SAMPLES:
            row = dict.fromkeys(fieldnames, "1")
            row["buffer_packets"] = str(buffer_packets)
            rows.append(row)

        with self.assertRaisesRegex(ValueError, "queue_disc_drops"):
            validate_rows(rows, repetitions=1)

    def test_validate_metric_variation_rejects_flat_metrics(self):
        from scripts.run_experiments import BUFFER_SAMPLES, FIELDNAMES, validate_metric_variation

        rows = []
        for buffer_packets in BUFFER_SAMPLES:
            row = dict.fromkeys(FIELDNAMES, "1")
            row["buffer_packets"] = str(buffer_packets)
            row["run_seed"] = "1"
            row["flow_id"] = "1"
            row["queue_disc_drops"] = "5"
            rows.append(row)

        with self.assertRaisesRegex(ValueError, "flat"):
            validate_metric_variation(rows, ["queue_disc_drops"])


if __name__ == "__main__":
    unittest.main()
