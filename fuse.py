#!/usr/bin/env python

# coding: utf-8

import SimpleITK as sitk
import numpy as np
import os
import sys
import time

def get_superresolution_recon(img, ref_img):
    resampler = sitk.ResampleImageFilter()
    resampler.SetDefaultPixelValue(0.0)

    # sagittal image is the reference
    resampler.SetReferenceImage(ref_img)

    # 5th order b-spline interpolator
    resampler.SetInterpolator(sitk.sitkBSpline)

    # rotate image to reference orientation
    resampler.SetOutputDirection(ref_img.GetDirection())

    # origin
    resampler.SetOutputOrigin(ref_img.GetOrigin())

    # output pixel type
    resampler.SetOutputPixelType(sitk.sitkUInt16)

    # output image spacing (isotropic at in-plane resolution)
    in_plane_resolution = min(ref_img.GetSpacing())
    resampler.SetOutputSpacing((in_plane_resolution,in_plane_resolution,in_plane_resolution))

    # set output size
    siz = ref_img.GetSize()
    spc = ref_img.GetSpacing()
    resampler.SetSize((int(siz[0]*spc[0]/in_plane_resolution), 
                       int(siz[1]*spc[1]/in_plane_resolution), 
                       int(round(siz[2]*spc[2]/in_plane_resolution))))

    # identity transform (no transform necessary for interpolation step)
    resampler.SetTransform(sitk.Transform(ref_img.GetDimension(), sitk.sitkIdentity))

    img_resampled = resampler.Execute(img)

    return img_resampled

def write_stats_mha(stats_img, spacing, direction):
    stats_img.SetSpacing(spacing)
    stats_img.SetDirection(direction)
    sitk.WriteImage(stats_img, output_filename+".mha")

def read_dicom_dir(input_dicom_path):
    series_reader = sitk.ImageSeriesReader()
    dicom_names = series_reader.GetGDCMSeriesFileNames(input_dicom_path)
    series_reader.SetFileNames(dicom_names)
    series_reader.MetaDataDictionaryArrayUpdateOn()
    series_reader.LoadPrivateTagsOn()
    img = series_reader.Execute()

    return (img, series_reader)

# parse input arguments
# 1. t2wi_path: path to directory containing three subdirectories 
#    whose names match "cor", "sag", and "axial" (case-insensitive)
t2wi_path = sys.argv[1]
# 2. output_dicom_path: path to directory containing output dicom files
output_dicom_path = sys.argv[2]

# get paths to directories containing the three orthogonal DICOM MR image stacks
img_stack_folders = os.listdir(t2wi_path)
sag_dir = [x for x in img_stack_folders if "sag" in x.lower()][0]
cor_dir = [ x for x in img_stack_folders if "cor" in x.lower()][0]
axial_dir = [ x for x in img_stack_folders if "axial" in x.lower()][0]

# Sagittal image (reference)
print("resample sagittal image stack")
sag_img, series_reader = read_dicom_dir(os.path.join(t2wi_path,sag_dir))
sag_img_resampled = get_superresolution_recon(sag_img, sag_img)
sitk.WriteImage(sag_img_resampled, "resampled_sag.mha")

# Coronal image
print("resample coronal image stack")
cor_img = read_dicom_dir(os.path.join(t2wi_path,cor_dir))[0]
cor_img_resampled = get_superresolution_recon(cor_img, sag_img_resampled)
sitk.WriteImage(cor_img_resampled, "resampled_cor.mha")

# Resample axial image
print("resample axial image stack")
axial_img = read_dicom_dir(os.path.join(t2wi_path,axial_dir))[0]
axial_img_resampled = get_superresolution_recon(axial_img, sag_img_resampled)
sitk.WriteImage(axial_img_resampled, "resampled_axial.mha")

# Fuse the three MR image stacks using the median of the three images 
print("fusing images")
arr = np.stack([sitk.GetArrayFromImage(sag_img_resampled),
                sitk.GetArrayFromImage(cor_img_resampled),
                sitk.GetArrayFromImage(axial_img_resampled)])
median_img = sitk.GetImageFromArray(np.median(arr, axis=0))

# cast floating point to unsigned integer
cast_filter = sitk.CastImageFilter()
cast_filter.SetOutputPixelType(sitk.sitkInt16)
median_img = cast_filter.Execute(median_img)

# set image properties
median_img.SetDirection(sag_img_resampled.GetDirection())
median_img.SetSpacing(sag_img_resampled.GetSpacing())
median_img.SetOrigin(sag_img_resampled.GetOrigin())

sitk.WriteImage(median_img, "med.mha")
print(median_img)
sys.exit()

# create output directory if it does not exist yet
if not os.path.exists(output_dicom_path):
    os.makedirs(output_dicom_path)

# initialize file writer
writer = sitk.ImageFileWriter()

# Use the study/series/frame of reference information given in the meta-data
# dictionary and not the automatically generated information from the file IO
writer.KeepOriginalImageUIDOn()

# Copy relevant tags from the original meta-data dictionary (private tags are also
# accessible).
tags_to_copy = ["0010|0010", # Patient Name
                "0010|0020", # Patient ID
                "0010|0030", # Patient Birth Date
                #"0020|000d",
                "0020|0010", # Study ID, for human consumption
                "0008|0020", # Study Date
                "0008|0030", # Study Time
                "0008|0050", # Accession Number
                "0008|0060"] # Modality

# set the modification date and time to be same for all DICOM images
modification_time = time.strftime("%H%M%S")
modification_date = time.strftime("%Y%m%d")

# copy some of the tags and add the relevant tags indicating the change
# (series instance UID (0020|000e) has numeric components, cannot start
# with zero, and separated by '.')
direction = median_img.GetDirection()
series_tag_values = [(k, series_reader.GetMetaData(0,k)) for k in tags_to_copy if series_reader.HasMetaDataKey(0,k)] + \
                 [("0008|0031",modification_time),    # Series Time
                  ("0008|0021",modification_date),    # Series Date
                  ("0008|0008","DERIVED\\SECONDARY"), # Image Type
                  ("0020|000d", "1.5.948.8.3.2892493.9.7260."+modification_date+".8"+modification_time),  # Study Instance UID
                  ("0020|000e", "1.5.948.8.3.2892493.9.7260."+modification_date+".8"+modification_time),  # Series Instance UID
                  ("0020|0037", '\\'.join(map(str, (direction[0], direction[3], direction[6],             # Image Orientation (Patient)
                                                    direction[1],direction[4],direction[7])))),
                  ("0008|103e", series_reader.GetMetaData(0,"0008|103e") + "super-resolution SimpleITK")] # Series Description

for i in range(median_img.GetDepth()):
    image_slice = median_img[:,:,i]
    # tags shared by the series
    for tag, value in series_tag_values:
        image_slice.SetMetaData(tag, value)
    # slice specific tags
    image_slice.SetMetaData("0008|0012", time.strftime("%Y%m%d")) # Instance Creation Date
    image_slice.SetMetaData("0008|0013", time.strftime("%H%M%S")) # Instance Creation Time
    image_slice.SetMetaData("0020|0032", '\\'.join(map(str,median_img.TransformIndexToPhysicalPoint((0,0,i))))) # Image Position (Patient)
    image_slice.SetMetaData("0020|0013", str(i)) # Instance Number

    # write to the output directory and add the extension dcm, to force writing in DICOM format
    writer.SetFileName(os.path.join(sys.argv[2],"0000-"+str(i).zfill(4)+".dcm"))
    writer.Execute(image_slice)
