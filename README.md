# Sort DICOM files into folders that make sense
When DICOM files are received by a SCP, we want to store them without any 
processing overhead.

The purpose of `dcmsort.py` is to periodically crawl over a directory 
containing lots of DICOM files and sort those files into subdirectories 
that makes finding files easier.

# Requirements
`dicomsorter` has been developed and tested with Python 3.11, but it may 
work with versions as low as 3.4.

# Installation
The easiest way is to install `dicomsorter` is within a virtual environment

```bash
python3 -m venv dicomsorter
dicomsorter/bin/pip install git+https://github.com/harvard-nrg/dicomsorter@v0.1.0
```

# General overview
This program aims to be robust to unexpected terminations (e.g., `SIGKILL`, 
`SIGTERM`) and concurrent invocations.

1. The only file system manipulation performed by `dcmsort.py` is a single 
   atomic `rename`.
2. Files will be sorted into `<Project>` and `<Session>` subdirectories
   1. The `<Project>` will determined from the value contained in the 
      `StudyDescription` DICOM header, falling back to `UNKNOWN`.
   2. The `<Session>` will be determined from the value contained within the
      `PatientID` DICOM header, falling back to `StudyInstanceUID`, or a
      simple ISO-8601 timestamp.

## practice run
By default, `dcmsort.py` will not rename any files. You can safely run 
`dcmsort.py` to see what it would have done

```bash
dcmsort.py -v
```

## production run
Pass `--do-sort` to have `dcmsort.py` follow through with file renaming

```bash
dcmsort.py -v --do-sort
```

## additional help
Pass `--help` for additional help

```bash
dcmsort.py --help
```

