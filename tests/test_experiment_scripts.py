import unittest
from pathlib import Path


def make_valid_experiment_rows():
    from scripts.run_experiments import BUFFER_SAMPLES, FIELDNAMES

    rows = []
    for buffer_packets in BUFFER_SAMPLES:
        row = dict.fromkeys(FIELDNAMES, "0")
        row["buffer_packets"] = str(buffer_packets)
        row["tx_packets"] = "100"
        row["rx_packets"] = "90"
        row["lost_packets"] = "10"
        row["queue_disc_drops"] = "5"
        row["packet_loss_ratio_percent"] = "10.000000"
        row["throughput_mbps"] = "1.500000"
        row["average_delay_ms"] = "2.500000"
        row["run_seed"] = "1"
        row["flow_id"] = "1"
        rows.append(row)
    return rows


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

    def test_validate_rows_accepts_valid_default_buffer_rows(self):
        from scripts.run_experiments import validate_rows

        validate_rows(make_valid_experiment_rows(), repetitions=1)

    def test_validate_rows_rejects_rx_packets_above_tx_packets(self):
        from scripts.run_experiments import validate_rows

        rows = make_valid_experiment_rows()
        rows[0]["rx_packets"] = "101"

        with self.assertRaisesRegex(ValueError, "rx_packets"):
            validate_rows(rows, repetitions=1)

    def test_validate_rows_rejects_wrong_lost_packet_count(self):
        from scripts.run_experiments import validate_rows

        rows = make_valid_experiment_rows()
        rows[0]["lost_packets"] = "9"

        with self.assertRaisesRegex(ValueError, "lost_packets"):
            validate_rows(rows, repetitions=1)

    def test_validate_rows_rejects_wrong_packet_loss_ratio(self):
        from scripts.run_experiments import validate_rows

        rows = make_valid_experiment_rows()
        rows[0]["packet_loss_ratio_percent"] = "11.000000"

        with self.assertRaisesRegex(ValueError, "packet_loss_ratio_percent"):
            validate_rows(rows, repetitions=1)

    def test_validate_rows_rejects_negative_throughput_or_delay(self):
        from scripts.run_experiments import validate_rows

        for field in ("throughput_mbps", "average_delay_ms"):
            with self.subTest(field=field):
                rows = make_valid_experiment_rows()
                rows[0][field] = "-0.1"

                with self.assertRaisesRegex(ValueError, field):
                    validate_rows(rows, repetitions=1)

    def test_validate_rows_rejects_non_finite_float_metrics(self):
        from scripts.run_experiments import validate_rows

        for value in ("nan", "inf", "-inf"):
            with self.subTest(value=value):
                rows = make_valid_experiment_rows()
                rows[0]["throughput_mbps"] = value

                with self.assertRaisesRegex(ValueError, "throughput_mbps"):
                    validate_rows(rows, repetitions=1)

    def test_validate_rows_rejects_duplicate_buffer_seed_pair(self):
        from scripts.run_experiments import validate_rows

        rows = make_valid_experiment_rows()
        rows[1]["buffer_packets"] = rows[0]["buffer_packets"]

        with self.assertRaisesRegex(ValueError, "Duplicate buffer/seed pair"):
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

    def test_aggregate_rows_by_buffer_returns_sorted_unique_buffers(self):
        from scripts.plot_results import aggregate_rows_by_buffer

        rows = [
            {"buffer_packets": "5", "throughput_mbps": "10.0"},
            {"buffer_packets": "1", "throughput_mbps": "3.0"},
        ]

        buffers, values = aggregate_rows_by_buffer(rows, "throughput_mbps")

        self.assertEqual(buffers, [1, 5])
        self.assertEqual(values, [3.0, 10.0])

    def test_aggregate_rows_by_buffer_averages_duplicate_buffers(self):
        from scripts.plot_results import aggregate_rows_by_buffer

        rows = [
            {"buffer_packets": "5", "average_delay_ms": "10.0"},
            {"buffer_packets": "1", "average_delay_ms": "2.0"},
            {"buffer_packets": "5", "average_delay_ms": "14.0"},
            {"buffer_packets": "1", "average_delay_ms": "4.0"},
        ]

        buffers, values = aggregate_rows_by_buffer(rows, "average_delay_ms")

        self.assertEqual(buffers, [1, 5])
        self.assertEqual(values, [3.0, 12.0])

    def test_aggregate_rows_by_buffer_rejects_invalid_metric_values(self):
        from scripts.plot_results import aggregate_rows_by_buffer

        rows = [{"buffer_packets": "1", "average_delay_ms": "not-a-number"}]

        with self.assertRaisesRegex(ValueError, "average_delay_ms"):
            aggregate_rows_by_buffer(rows, "average_delay_ms")

    def test_aggregate_rows_by_buffer_rejects_invalid_buffer_values(self):
        from scripts.plot_results import aggregate_rows_by_buffer

        rows = [{"buffer_packets": "not-a-buffer", "average_delay_ms": "1.0"}]

        with self.assertRaisesRegex(ValueError, "buffer_packets"):
            aggregate_rows_by_buffer(rows, "average_delay_ms")


if __name__ == "__main__":
    unittest.main()
