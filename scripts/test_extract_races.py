import unittest

from extract_races import (
    extract_jockey_and_horse,
    parse_trainers_footer,
)


class TestRaceExtraction(unittest.TestCase):

    def test_extract_jockey_and_horse(self):
        # Standard
        h, j = extract_jockey_and_horse("Rozzyroo(Elliott,Christopher)")
        self.assertEqual(h, "Rozzyroo")
        self.assertEqual(j, "Elliott,Christopher")

        # Nested parens
        h, j = extract_jockey_and_horse("Ghostlyprince(Huayas,Gherson(Jason))")
        self.assertEqual(h, "Ghostlyprince")
        self.assertEqual(j, "Huayas,Gherson(Jason)")

        # Multiple groups (Country code)
        h, j = extract_jockey_and_horse("Caribbean(AUS)(Olver,Madison)")
        self.assertEqual(h, "Caribbean(AUS)")
        self.assertEqual(j, "Olver,Madison")

        # No parens
        h, j = extract_jockey_and_horse("HorseName")
        self.assertIsNone(h)
        self.assertIsNone(j)

    def test_parse_trainers_footer(self):
        # Multiline
        text = "Trainers: 1 - Jones, Eduardo; 2 - \n Brown, William"
        mapping = parse_trainers_footer(text)
        self.assertEqual(mapping.get("1"), "Jones, Eduardo")
        self.assertEqual(mapping.get("2"), "Brown, William")

if __name__ == '__main__':
    unittest.main()
