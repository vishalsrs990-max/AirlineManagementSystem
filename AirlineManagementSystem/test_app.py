import unittest

class TestBasic(unittest.TestCase):
    def test_dummy(self):
        self.assertEqual(1 + 1, 2)

if __name__ == '__main__':
    unittest.main()


