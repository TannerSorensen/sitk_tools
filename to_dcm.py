#!/usr/bin/env python

import os
import sys
import time
import SimpleITK as sitk

def writeSlices(series_tag_values, img, i):
    castFilter = sitk.CastImageFilter()
    castFilter.SetOutputPixelType(sitk.sitkInt16)
    
    # Convert floating type image (imgSmooth) to int type (imgFiltered)
    image_slice = castFilter.Execute(img[:,:,i])

    # Tags shared by the series.
    list(map(lambda tag_value: image_slice.SetMetaData(tag_value[0], tag_value[1]), series_tag_values))

    # Slice specific tags.
    image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d")) # Instance Creation Date
    image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S")) # Instance Creation Time

    # Setting the type to CT preserves the slice location.
    image_slice.SetMetaData("0008|0060", "CT")  # set the type to CT so the thickness is carried over

    # (0020, 0032) image position patient determines the 3D spacing between slices.
    image_slice.SetMetaData("0020|0032", '\\'.join(map(str,img.TransformIndexToPhysicalPoint((0,0,i))))) # Image Position (Patient)
    image_slice.SetMetaData("0020,0013", str(i)) # Instance Number

    # Write to the output directory and add the extension dcm, to force writing in DICOM format.
    writer.SetFileName(os.path.join(output_path,str(i).zfill(4)+'.dcm'))

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    writer.Execute(image_slice)

# parse input arguments
# 1. img_filename: name of image file (incl. extension)
img_filename = sys.argv[1]
# 2. output_path: path of directory containing the output DICOM series
output_path = sys.argv[2]

img = sitk.ReadImage(img_filename)

modification_time = time.strftime("%H%M%S")
modification_date = time.strftime("%Y%m%d")

# Copy some of the tags and add the relevant tags indicating the change.
# For the series instance UID (0020|000e), each of the components is a number, cannot start
# with zero, and separated by a '.' We create a unique series ID using the date and time.
# tags of interest:
direction = img.GetDirection()
series_tag_values = [("0008|0031",modification_time), # Series Time
                  ("0008|0021",modification_date), # Series Date
                  ("0008|0008","DERIVED\\SECONDARY"), # Image Type
                  ("0020|000e", "1.2.826.0.1.3680043.2.1125."+modification_date+".1"+modification_time), # Series Instance UID
                  ("0020|0037", '\\'.join(map(str, (direction[0], direction[3], direction[6],# Image Orientation (Patient)
                                                    direction[1],direction[4],direction[7])))),
                  ("0008|103e", "Created-SimpleITK")] # Series Description


writer = sitk.ImageFileWriter()
# Use the study/series/frame of reference information given in the meta-data
# dictionary and not the automatically generated information from the file IO
writer.KeepOriginalImageUIDOn()

list(map(lambda i: writeSlices(series_tag_values, img, i), range(img.GetDepth())))
