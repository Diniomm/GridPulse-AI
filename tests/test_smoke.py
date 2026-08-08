import unittest

from gridpulse import __version__


class PackageSmokeTest(unittest.TestCase):
    def test_package_exposes_version(self) -> None:
        self.assertEqual(__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
