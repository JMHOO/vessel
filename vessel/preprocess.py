import re
import os
import numpy as np

import vessel.configuration as config
from vessel.parser import DICOMParser
from vessel.utils import Iterator


class PatientFile(object):
    """Holds the file sets by each patient
       If we need to retrieve dicoms by patient's id, this class can help.
    """
    FILE_SETS_LABELS = ['dicoms', 'i_contours', 'o_contours']

    def __init__(self, dicoms_folder, contour_folder):
        self._paired_files = []
        self._files = {}
        self._paths = {}
        path_to_be_scanned = [
            dicoms_folder,
            os.path.join(contour_folder, config.IOConfig['inner_contour_folder']),
            os.path.join(contour_folder, config.IOConfig['outter_contour_folder'])
        ]
        
        # scan file in specific directory
        for i, path in enumerate(path_to_be_scanned):
            files = []
            for dirname, _, filenames in os.walk(path):
                self._paths[self.FILE_SETS_LABELS[i]] = path
                for filename in filenames:
                    files.append(filename)
            self._files[self.FILE_SETS_LABELS[i]] = files

        self._build_file_array()

    def _build_file_array(self):
        """
        build file array
           if i/o-contour-file doesn't exist, it will be marked as None
        result:
            [
                [DICOM file, i-contour-file, o-contour-file],
                [DICOM file, i-contour-file, o-contour-file],
                ...
                [DICOM file, i-contour-file, o-contour-file]
            ]
        """

        # use regexp to search index id from i/o-contour-files' name
        # e.g. 
        #   IM-0001-0027-icontour-manual.txt
        #   0027 is the index id we are looking for
        contour_index = {}
        pattern = r'(\d+)-[io]contour'
        for con_file in self._files['i_contours']:
            match = re.search(pattern, con_file)
            if match:
                index = int(match.group(1))
                contour_index[index] = (con_file, None)
        
        for con_file in self._files['o_contours']:
            match = re.search(pattern, con_file)
            if match:
                index = int(match.group(1))
                i_con = None
                if index in contour_index:
                    i_con, _ = contour_index[index]
                contour_index[index] = (i_con, con_file)
        
        # connect dicom, i-contour and o-contour together
        # if the dicom file name isn't a number, this file will be ignored
        for dicom_file in self._files['dicoms']:
            i_con, o_con = None, None
            filename, file_ext = os.path.splitext(dicom_file)
            if filename.isdigit():
                index = int(filename)
                if index in contour_index:
                    i_con, o_con = contour_index[index]
                    if i_con:
                        i_con = os.path.join(self._paths['i_contours'], i_con)
                    if o_con:
                        o_con = os.path.join(self._paths['o_contours'], o_con)

            self._paired_files.append(
                [os.path.join(self._paths['dicoms'], dicom_file), i_con, o_con]
            )

    def paired_files(self):
        return np.array(self._paired_files)

    def __getitem__(self, key):
        if self._files is None:
            return None

        return self._files[key] if key in self._files.keys() else None

    def __bool__(self): 
        return len(self._files['dicoms']) > 0


class FileFeeder(object):
    """Scan DICOM and contour files
    directory: a folder that contains dcm and contour files
    The folder structure is expect as:
       directory
          |---- dicoms          # folder name can defind in configuration.py
          |____ contourfiles    # folder name can defind in configuration.py
            |---- i-contours    # folder name can defind in configuration.py
            |____ o-contours    # folder name can defind in configuration.py
    """
    def __init__(self, directory):
        self._directory = os.path.abspath(directory)
        self._patient_contours = {}         # a map describe dicoms(patient id) and contourfiles
        self._patient_files = {}            # a map decribe patient id ant PatientFile object
        self._file_array = None
        self.n = 0
        self._iter_index = 0
        if os.path.exists(self._directory):
            self.scan_files()
        else:
            raise IOError("Directory [{}] not exist!".format(self._directory))
        
    def _build_patient_contours(self):
        link_file = os.path.join(self._directory, config.IOConfig['link_file'])
        if os.path.exists(link_file):
            with open(link_file, 'r') as fp_link:
                next(fp_link)               # skip first line (column name)
                for line in fp_link:
                    links = line.strip().split(',')
                    if len(links) != 2:     # ignore invalid line
                        continue
                    # links[0]: patient_id, links[1]: contour_id
                    self._patient_contours[links[0]] = links[1]
    
    def scan_files(self):
        """Scan directory
           1. use link.csv build link between  [patient] <---> [contourfiles]
           2. for each [patient]
              build link between  [*.dcm] <---> ([i-contour], [o-contour])
           3. concat all patient's file together
           e.g. scaned file array
            [
                [140.dcm, ...-0140-icontour-manual.txt, ...-0140-ocontour-manual.txt ],
                ...
                [220.dcm, None, None ]
            ]
        """
        self._build_patient_contours()
        dicoms_path = os.path.join(self._directory, config.IOConfig['dicoms_folder'])
        base_contour_path = os.path.join(self._directory, config.IOConfig['contour_folder'])
        patient_files = []
        if os.path.exists(dicoms_path):
            for dirname, dirnames, _ in os.walk(dicoms_path):
                for sub_dir in dirnames:
                    self._patient_files[sub_dir] = PatientFile(
                        os.path.join(dicoms_path, sub_dir), 
                        os.path.join(base_contour_path, self._patient_contours[sub_dir]))
                    patient_files.append(self._patient_files[sub_dir].paired_files())
        if patient_files:
            self._file_array = np.concatenate(patient_files)
            self.n = self._file_array.shape[0]
            self._iter_index = 0

    def __len__(self):
        return self.n

    # iterator FileFeeder
    def __iter__(self):
        return self

    # this is a SIMPLE iterator, no parallel !
    # return: ([pixel_data], [mask]) if that dcm don't have corresponding contourfile, [maks] will be None
    def __next__(self):
        if self._iter_index >= self.n:
            raise StopIteration
        
        item = self._file_array[self._iter_index]
        self._iter_index += 1
        return DICOMParser.ReadDICOM(item[0], item[1], item[2])
        
    def files(self):
        return self._file_array


class DICOMFileIterator(Iterator):
    """An implementation of utils.Iterator
       Iterate data through batches
       This iterator is designed for parallel, a locker will be apply when retrieving the INDICES of next batch.
          But the locker will not affect the _process_batch_data
    """
    def __init__(self, x, batch_size, shuffle=True, seed=None):
        """
        x is a numpy array of file group. e.g.
           x = [
               [140.dcm, ..-0140-icontour-manual.txt, ...-0140-ocontour-manual.txt ],
               ...
               [220.dcm, None, None ]
           ]
        """
        self.x = x
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.seed = seed
        sample_size = 0
        if x is not None:
            sample_size = x.shape[0]
        super().__init__(sample_size, batch_size, shuffle, seed)

    def _process_batch_data(self, index_array):
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
        batch_x = []
        batch_y = []
        for i, row in enumerate(index_array):
            x = self.x[row]
            img, mask = DICOMParser.ReadDICOM(x[0], x[1], x[2])
            batch_x.append(img)
            batch_y.append(mask)
        return (np.asarray(batch_x), np.asarray(batch_y))

    def next(self):
        # lock during generate index array
        with self.index_locker:
            index_array = next(self.index_generator)

        # print("batch index array: {}".format(index_array))
        # process_batch_data can be parallel
        return self._process_batch_data(index_array)

    