import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.category_normalization import canonicalize_category
from app.services.rule_based_classifier import classify_transaction


class CategoryNormalizationTestCase(unittest.TestCase):
    def test_bill_aliases_share_one_category(self):
        aliases = ["Bills", "Tagihan rutin", "Tagihan Bulanan"]

        self.assertEqual(
            {"Tagihan Bulanan"},
            {canonicalize_category(alias) for alias in aliases},
        )

    def test_food_aliases_share_one_category(self):
        aliases = ["Makanan", "Food"]

        self.assertEqual(
            {"Food"},
            {canonicalize_category(alias) for alias in aliases},
        )

    def test_grocery_aliases_share_one_category(self):
        aliases = ["Groceries", "Grocery"]

        self.assertEqual(
            {"Grocery"},
            {canonicalize_category(alias) for alias in aliases},
        )

    def test_generic_transport_maps_to_routine_transport(self):
        self.assertEqual("Transportasi Rutin", canonicalize_category("Transport"))
        self.assertEqual("Transportasi Rutin", canonicalize_category("Transportasi"))
        self.assertEqual(
            "Transportasi Non Rutin",
            canonicalize_category("Transportasi Non Rutin"),
        )

    def test_rule_based_classifier_outputs_canonical_category(self):
        classification = classify_transaction({
            "title": "bayar kartu kredit",
            "raw_category": "Bills",
            "direction": "expense",
        })

        self.assertEqual("Tagihan Bulanan", classification["category"])


if __name__ == "__main__":
    unittest.main()
