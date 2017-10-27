import unittest
import time
from vessel.preprocess import FileFeeder, DICOMFileIterator
from vessel.utils import GeneratorQueue

def main():
    start_time = time.time()

    # set basic rule to mimic training
    batch_size = 12
    epochs = 2

    # create file feeder
    feeder = FileFeeder('data')
    n_of_samples = len(feeder)
    steps_of_epoch = n_of_samples / batch_size

    # generator to generate (pixel_data, mask)
    # it will return:
    """
    batch_x = [
        pixel_data, 
        pixel_data, 
        ...
        pixel_data
    ]
    batch_y = [
        mask,
        mask,
        ...
        mask
    ]
    return: (batch_x, batch_y)
    """
    generator = DICOMFileIterator(x=feeder.files(), batch_size=batch_size)

    try:
        # use GeneratorQueue to parallel generator
        queue = GeneratorQueue(generator=generator)
        queue.start()
        # output is our new generator
        output = queue.fetch()

        epoch = 0
        while epoch < epochs:
            steps = 0
            print("Epoch-{}".format(epoch))
            while steps < steps_of_epoch:
                x, y = next(output)
                current_batch_size = x.shape[0]
                print("Batch-{}, X.shape: {}, Y.shape: {}".format(steps, x.shape, y.shape))

                steps += 1
            epoch += 1
            # notify generator to re-shuffle index array
            generator.event_epoch_end()
    finally:
        queue.stop()
    
    elapsed_time = time.time() - start_time
    print("Used time: {}".format(elapsed_time))

if __name__ == '__main__':
    main()
