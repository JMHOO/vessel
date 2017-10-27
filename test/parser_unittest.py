import unittest

from vessel.parser import DICOMParser

class TestParser(unittest.TestCase):  
    def test_dicom_parser(self):
        dicom_parser = DICOMParser()
        self.assertEqual(dicom_parser.Pixel('data/dicoms/SCD0000201/126.dcm')['width'], 256)
        #print(dicom_parser.Coords('data/contourfiles/SC-HF-I-1/i-contours/IM-0001-0048-icontour-manual.txt'))


if __name__ == '__main__':
    unittest.main()
