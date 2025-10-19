from unittest import TestCase


class TestUtilsInit(TestCase):
    """Test cases for utils __init__.py module."""
    
    def test_profiler_import(self):
        """Test that JuraganMaterialProfiler can be imported from utils."""
        from api.juragan_material.utils import JuraganMaterialProfiler
        self.assertIsNotNone(JuraganMaterialProfiler)
    
    def test_all_exports(self):
        """Test __all__ exports."""
        from api.juragan_material import utils
        self.assertIn('JuraganMaterialProfiler', utils.__all__)
        self.assertEqual(len(utils.__all__), 1)
