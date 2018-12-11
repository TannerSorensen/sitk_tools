# sitk_tools

Command-line tools written in Python using the SimpleITK library.

## Contributors

Tanner Sorensen  
Signal Analysis and Interpretation Laboratory   
University of Southern California

## Contents

* `fuse.py`: fuse three orthogonal stacks of DICOM MR images in the sagittal, coronal, and axial orientation. If `path_to_dicom_dirs` is the path to a directory containing three subdirectories with `sag`, `cor`, and `axial` in their names (case-insensitive, requires only partial match), then the following illustrates how to call `fuse.py` from a Bash session:
```bash
./fuse.py path_to_dicom_dirs
```
The script outputs the following `.mha` files:
    * `resampled_sag.mha`, `resampled_cor.mha`, `resampled_axial.mha`: imaged obtained by resampling the sagittal, coronal, and axial DICOM image stacks to have isotropic spatial resolution (taken to be the in-plane spatial resoluton of the DICOM MR image stack). These files only contain information from a single image stack (i.e., no fusion).
    * `superres_mean.mha`, `superres_median.mha`, `superres_min.mha`, `superres_max.mha`: super-resolution images obtained by fusing `resampled_sag.mha`, `resampled_sag.mha`, and `resampled_sag.mha` by taking the mean, median, minimum, and maximum.

* `to_dcm.py`: convert image (e.g., `.mha` image) to a DICOM series. Example usage:
```bash
./to_dcm.py image.mha path_to_dicom_series
```
