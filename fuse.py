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
# 2. output_filename: filename for super-resolution image as .mha file
output_filename = sys.argv[2]

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

# set image properties
median_img.SetDirection(sag_img_resampled.GetDirection())
median_img.SetSpacing(sag_img_resampled.GetSpacing())
median_img.SetOrigin(sag_img_resampled.GetOrigin())

# append file extension if not already included
if ".mha" not in output_filename:
    output_filename = output_filename+".mha"

# write .mha image
sitk.WriteImage(median_img, output_filename)


