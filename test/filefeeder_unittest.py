import unittest
from vessel.preprocess import FileFeeder
from vessel.preprocess import DICOMFileIterator

class TestFileFeeder(unittest.TestCase):
    def test_link_building(self):
        feeder = FileFeeder('data')
        self.assertEqual(feeder._patient_contours['SCD0000401'], 'SC-HF-I-5')
        print(len(feeder))
    
    def test_patient_files(self):
        feeder = FileFeeder('data')
        self.assertEqual(len(feeder._patient_files['SCD0000401']['dicoms']), 220)
        self.assertEqual(len(feeder._patient_files['SCD0000401']['i_contours']), 18)
        self.assertEqual(len(feeder._patient_files['SCD0000401']['o_contours']), 9)

    def test_smiple_iterator(self):
        feeder = FileFeeder('data')
        for image, mask in feeder:
            if mask is None:
                y = 'None'
            else:
                y = mask.shape
            print(image.shape, y)

    def test_DICOMFileIterator(self):
        feeder = FileFeeder('data')
        itert = DICOMFileIterator(x=feeder.files(), batch_size=8)

        print("Total sample: {}, batches: {}".format(len(feeder), len(itert)))
        # test for generate 20 batch
        n = 20
        while(n>0):
            batch_x, batch_y = next(itert)
            print(batch_x.shape, batch_y.shape)
            n -= 1

if __name__ == '__main__':
    unittest.main()
