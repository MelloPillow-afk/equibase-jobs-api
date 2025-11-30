import csv
import os
import unittest


class TestCsvComparison(unittest.TestCase):
    def test_compare_csv_outputs(self):
        generated_path = "outputs/01-01-23.csv"
        correct_path = "outputs/correct-01-01-23.csv"

        # Ensure both files exist
        self.assertTrue(os.path.exists(generated_path), "Generated CSV not found")
        self.assertTrue(os.path.exists(correct_path), "Correct CSV not found")

        with open(generated_path) as f1, open(correct_path) as f2:
            reader1 = list(csv.reader(f1))
            reader2 = list(csv.reader(f2))

            # Sort rows by Date, Race #, PGM (if available) or just full row
            # Header is first row, keep it separate
            header1 = reader1[0]
            header2 = reader2[0]
            data1 = sorted(reader1[1:], key=lambda x: (x[0], x[1], x[4])) # Sort by Date, Race, Jockey
            data2 = sorted(reader2[1:], key=lambda x: (x[0], x[1], x[4]))

            reader1 = [header1] + data1
            reader2 = [header2] + data2

            # Compare content
            set1 = set(tuple(row) for row in reader1)
            set2 = set(tuple(row) for row in reader2)

            missing_in_generated = set2 - set1
            extra_in_generated = set1 - set2

            if missing_in_generated:
                print("\nMissing in Generated:")
                for row in missing_in_generated:
                    print(row)

            if extra_in_generated:
                print("\nExtra in Generated:")
                for row in extra_in_generated:
                    print(row)

            self.assertEqual(len(reader1), len(reader2), f"Row count mismatch: Generated={len(reader1)}, Correct={len(reader2)}")

            for i, (row1, row2) in enumerate(zip(reader1, reader2)):
                self.assertEqual(row1, row2, f"Mismatch at row {i+1}:\nGenerated: {row1}\nCorrect:   {row2}")

if __name__ == "__main__":
    unittest.main()
