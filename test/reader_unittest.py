import unittest
from vessel.preprocess import FileFeeder, DICOMFileIterator
from vessel.utils import GeneratorQueue

class TestGenerator(unittest.TestCase):  
    def test_generator_queue(self):
        batch_size = 12
        epochs = 2

        feeder = FileFeeder('data')
        n_of_samples = len(feeder)
        steps_of_epoch = n_of_samples / batch_size

        generator = DICOMFileIterator(x=feeder.files(), batch_size=8)
        queue = GeneratorQueue(generator=generator)

        queue.start()
        output = queue.fetch()

        epoch = 0
        while epoch < epochs:
            steps = 0
            print("Epoch-{}".format(epoch))
            while steps < steps_of_epoch:
                item = next(output)
                x, y = item
                current_batch_size = x.shape[0]
                print("Batch-{}, X.shape: {}, Y.shape: {}".format(steps, x.shape, y.shape))

                steps += 1
            epoch += 1
        queue.stop()

        

if __name__ == '__main__':
    unittest.main()

