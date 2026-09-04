"""Unit tests for the shared counting logic."""

import unittest

from shared import count_occurrences


class CountOccurrencesTest(unittest.TestCase):
    def test_case_variations(self) -> None:
        self.assertEqual(count_occurrences("fuck FUCK Fuck fUcK", "fuck"), 4)

    def test_derived_forms(self) -> None:
        self.assertEqual(count_occurrences("fucking fucked fucker fucks", "fuck"), 4)

    def test_alternate_spellings(self) -> None:
        self.assertEqual(count_occurrences("fuk fck phuck f*ck f**k f***", "fuck"), 6)

    def test_fuck_you_phrase(self) -> None:
        self.assertEqual(count_occurrences("fuck u FUCK YOU fuckyou", "fuck"), 3)

    def test_custom_word_has_no_extra_variants(self) -> None:
        self.assertEqual(count_occurrences("hello HELLO helloing", "hello"), 3)

    def test_empty_word_counts_nothing(self) -> None:
        self.assertEqual(count_occurrences("whatever fuck", ""), 0)


if __name__ == "__main__":
    unittest.main()
