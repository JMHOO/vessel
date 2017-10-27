"""Parsing code for DICOMS and contour files"""

import dicom
from dicom.errors import InvalidDicomError

import numpy as np
from PIL import Image, ImageDraw


class DICOMParser():
    @staticmethod
    def Pixel(filename):
        """Parse the given DICOM filename
        :param filename: filepath to the DICOM file to parse
        :return: dictionary with DICOM image data
        """
        try:
            dcm = dicom.read_file(filename)
        except InvalidDicomError as e:
            print(e)
            return None

        dcm_image = dcm.pixel_array

        if hasattr(dcm, 'RescaleIntercept') and hasattr(dcm, 'RescaleSlope'):
            dcm_image = dcm_image * dcm.RescaleSlope + dcm.RescaleIntercept

        return { 'pixel_data' : dcm_image, 'width': dcm.Columns, 'height': dcm.Rows }

    @staticmethod
    def Coords(filename):
        """Parse the given contour filename

        :param filename: filepath to the contourfile to parse
        :return: list of tuples holding x, y coordinates of the contour
        """

        coords_lst = []
        with open(filename, 'r') as infile:
            for line in infile:
                line = line.strip()
                if not line:
                    continue

                coords = line.split(' ')
                if len(coords) != 2:
                    # try to split with ,
                    coords = line.split(',')
                    if len(coords) != 2:
                        continue
                
                try:
                    coor_x, coor_y = float(coords[0]), float(coords[1])
                except ValueError:
                    continue

                coords_lst.append(( coor_x, coor_y ))
        return coords_lst

    @staticmethod
    def CreateMask(contour_file, width, height):
        ploy = DICOMParser.Coords(contour_file)
        img = Image.new(mode='L', size=(width, height), color=0)
        ImageDraw.Draw(img).polygon(xy=ploy, outline=0, fill=1)
        mask = np.array(img).astype(bool)
        return mask

    @staticmethod
    def ReadDICOM(dicom_file, i_contour_file=None, o_contour_file=None):
        dcm = DICOMParser.Pixel(dicom_file)
        if not dcm:
            return None

        mask = None
        if i_contour_file:
            mask = DICOMParser.CreateMask(i_contour_file, dcm['width'], dcm['height'])
            
        return (dcm['pixel_data'], mask)