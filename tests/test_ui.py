import unittest

from ui import InsightsHandler


class InsightsHandlerTest(unittest.TestCase):
    def test_downsamples_chart_data_to_fixed_size(self):
        values = list(range(500))
        result = InsightsHandler._downsample(values, 25)
        self.assertEqual(len(result), 25)
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[-1], 499.0)

    def test_range_meter_prefers_absolute_label(self):
        self.assertEqual(InsightsHandler._meter("Low", "High"), 88)
