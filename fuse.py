#!/usr/bin/env python

# coding: utf-8

import SimpleITK as sitk
import numpy as np
import os
import sys

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

def write_stats_image(arr, spacing, direction):
    stats_img = sitk.GetImageFromArray(arr)
    stats_img.SetSpacing(spacing)
    stats_img.SetDirection(direction)
    sitk.WriteImage(stats_img,"resampled_mean.mha")

# parse input arguments
# 1. t2wi_path: path to directory containing three subdirectories 
#    whose names match "cor", "sag", and "axial" (case-insensitive)
t2wi_path = sys.argv[1]

# get paths to directories containing the three orthogonal DICOM MR image stacks
img_stack_folders = os.listdir(t2wi_path)
sag_dir = [x for x in img_stack_folders if "sag" in x.lower()][0]
cor_dir = [ x for x in img_stack_folders if "cor" in x.lower()][0]
axial_dir = [ x for x in img_stack_folders if "axial" in x.lower()][0]

# Sagittal image (reference)
print("resample sagittal image stack")
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames( os.path.join(t2wi_path,sag_dir))
reader.SetFileNames(dicom_names)
sag_img = reader.Execute()
sag_img_resampled = get_superresolution_recon(sag_img, sag_img)
sitk.WriteImage(sag_img_resampled, "resampled_sag.mha")

# Coronal image
print("resample coronal image stack")
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames(os.path.join(t2wi_path,cor_dir))
reader.SetFileNames(dicom_names)
cor_img = reader.Execute()
cor_img_resampled = get_superresolution_recon(cor_img, sag_img_resampled)
sitk.WriteImage(cor_img_resampled, "resampled_cor.mha")

# Resample axial image
print("resample axial image stack")
reader = sitk.ImageSeriesReader()
dicom_names = reader.GetGDCMSeriesFileNames(os.path.join(t2wi_path,axial_dir))
reader.SetFileNames(dicom_names)
axial_img = reader.Execute()
axial_img_resampled = get_superresolution_recon(axial_img, sag_img_resampled)
sitk.WriteImage(axial_img_resampled, "resampled_axial.mha")

# Fuse the three MR image stacks using the mean, median, max, and min of the three images 
print("fusing images")
arr = np.stack([sitk.GetArrayFromImage(sag_img_resampled),
                sitk.GetArrayFromImage(cor_img_resampled),
                sitk.GetArrayFromImage(axial_img_resampled)])
write_stats_image(np.mean(arr, axis=0), sag_img_resampled.GetSpacing(), sag_img_resampled.GetDirection())
write_stats_image(np.median(arr, axis=0), sag_img_resampled.GetSpacing(), sag_img_resampled.GetDirection())
write_stats_image(np.max(arr, axis=0), sag_img_resampled.GetSpacing(), sag_img_resampled.GetDirection())
write_stats_image(np.min(arr, axis=0), sag_img_resampled.GetSpacing(), sag_img_resampled.GetDirection())

