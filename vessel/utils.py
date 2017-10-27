import os
import sys
import logging
import threading
import time
import multiprocessing as mp
from abc import abstractmethod
import numpy as np
import vessel.configuration as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Iterator(object):
    """Generic data iterator, design for batch fetching.
    Every `Iterator` must implement the `_process_batch_data`
    method.
    # Arguments
        :n, total size.
        :batch_size.
        :shuffle
        :seed, Random seed for shuffle
    """
    def __init__(self, n, batch_size, shuffle, seed):
        self.n = n
        self.batch_size = batch_size
        self.seed = seed
        self.shuffle = shuffle
        self.batch_index = 0
        self.batches_visited_counter = 0
        self.index_locker = threading.Lock()        # ensure we get the correct index array
        self.index_array = None
        self.index_generator = self._generate_index()

    def _reset_index_array(self):
        self.index_array = np.arange(self.n)
        if self.shuffle:
            self.index_array = np.random.permutation(self.n)

    def __getitem__(self, idx):
        if idx >= len(self):
            print('exceed maximun batches')
            return None

        if self.seed is not None:
            np.random.seed(self.seed + self.batches_visited_counter)
        self.batches_visited_counter += 1
        if self.index_array is None:
            self._reset_index_array()
        batch_index_array = self.index_array[self.batch_size * idx:
                                             self.batch_size * (idx + 1)]
        return self._process_batch_data(batch_index_array)

    def __len__(self):
        return int(np.ceil(self.n / float(self.batch_size)))

    def event_epoch_end(self):
        self._reset_index_array()

    def reset(self):
        self.batch_index = 0

    # generate an index array for current batch
    def _generate_index(self):
        self.reset()
        while True:
            if self.seed is not None:
                np.random.seed(self.seed + self.batches_visited_counter)
            if self.batch_index == 0:
                self._reset_index_array()

            current_index = (self.batch_index * self.batch_size) % self.n
            if current_index + self.batch_size < self.n:
                self.batch_index += 1
            else:
                self.batch_index = 0

            self.batches_visited_counter += 1
            yield self.index_array[current_index:
                                   current_index + self.batch_size]

    #def __iter__(self):
    #    return self

    def __next__(self, *args, **kwargs):
        return self.next(*args, **kwargs)

    def next(self, args, kwargs):
        pass

    @abstractmethod
    def _process_batch_data(self, index_array):
        """Gets a batch of preprocessed data
        :index_array, array of indices of a batch.
        
        :return
            A batch of preprocessed data.
        """
        raise NotImplementedError


class GeneratorQueue(object):
    def __init__(self, generator, seed=None):
        self._wait_time = 0.05
        self._generator = generator
        self._processes = []
        self._max_workers = config.Performance['max_workers']
        self._cache_size = config.Performance['cache_size']
        self._stop_event = None
        self._seed = seed
        self.queue = None

    def start(self):
        self._stop_event = mp.Event()
        self.queue = mp.Queue(self._cache_size)

        def data_generator_runner(p_id):
            while not self._stop_event.is_set():
                try:
                    item = next(self._generator)
                    self.queue.put(item)
                    logger.info("GeneratorQueue::Process-{} loaded data, size:({}, {})".format(p_id, item[0].shape, item[1].shape))
                except StopIteration:
                    break
                except Exception:
                    self._stop_event.set()

        try:
            for i in range(self._max_workers):
                np.random.seed(self._seed)
                p = mp.Process(target=data_generator_runner, args=(i,))
                p.daemon = True
                if self._seed is not None:
                    self._seed += 1
                self._processes.append(p)
                p.start()
        except:
            self.stop()
            raise

    def stop(self, timeout=None):
        if self.is_running():
            self._stop_event.set()

        for p in self._processes:
            if p.is_alive():
                p.terminate()

        if self.queue is not None:
            self.queue.close()

        self._processes = []
        self._stop_event = None
        self.queue = None

    def is_running(self):
        return self._stop_event is not None and not self._stop_event.is_set()

    def fetch(self):
        """Creates another generator to fetch data from the queue.
        :return, A generator
        """
        while self.is_running():
            if not self.queue.empty():
                item = self.queue.get()
                if item is not None:
                    yield item
            else:
                # The consumer may faster than producer
                # wait workers to load data
                all_finished = all([not p.is_alive() for p in self._processes])
                if all_finished and self.queue.empty():
                    raise StopIteration()
                else:
                    print('queue empty, loading data...')
                    time.sleep(self._wait_time)