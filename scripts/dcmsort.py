#!/usr/bin/env -S python3 -u

import os
import re
import sys
import shutil
import pydicom
import logging
import filecmp
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('dicomsorter')
logging.basicConfig(level=logging.INFO)

def main():
    parser = ArgumentParser()
    parser.add_argument('--base-dir', type=Path, required=True)
    parser.add_argument('--do-sort', action='store_true')
    parser.add_argument('--confirm', action='store_true')
    parser.add_argument('--chmod', type=int, default=504)
    parser.add_argument('--chgrp', type=str)
    parser.add_argument('--rename', action='store_true')
    parser.add_argument('--log-file', type=Path)
    parser.add_argument('--log-max-bytes', type=int, default=0)
    parser.add_argument('--log-backup-count', type=int, default=0)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    # set logging level
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logger.setLevel(level)

    # add rotating log file handler
    if args.log_file:
        handler = RotatingFileHandler(
            args.log_file,
            maxBytes=args.log_max_bytes,
            backupCount=args.log_backup_count
        )
        logger.addHandler(handler)

    if not args.base_dir.exists():
        logger.error(f'directory does not exist {args.base_dir}')
        sys.exit(1)

    for sourcefile in args.base_dir.iterdir():
        if not sourcefile.is_file():
            continue

        # check if the current file is even in dicom format
        try:
            ds = pydicom.dcmread(sourcefile, stop_before_pixels=True)
            logger.debug(f'found dicom file {sourcefile}')
        except:
            logger.debug(f'skipping file {sourcefile}')
            continue

        # get project name from StudyDescription or use UNKNOWN
        project = get_project_name(ds, default='UNKNOWN')

        # get session name from PatientID, fallback on StudyInstanceUID, or a timestamp
        timestamp = datetime.now().isoformat()
        session = get_session_name(ds, default=timestamp)

        # define destination directory
        projectdir = Path(args.base_dir, project)
        destdir = Path(projectdir, session)

        # define destination file
        basename = sourcefile.name
        if args.rename:
            # do not sort this file if there's an error generating a basename
            try:
                basename = get_file_basename(ds, session)
            except Exception as e:
                logger.exception(e)
                continue
        destfile = Path(destdir, basename)

        # create destination directory with desired ownership and mode bits
        if args.do_sort:
            if not destdir.exists():
                projectdir.mkdir(parents=True, exist_ok=True)
                if args.chmod:
                    logger.debug(f'setting mode on {projectdir} to {oct(args.chmod)}')
                    projectdir.chmod(args.chmod)
                if args.chgrp:
                    logger.debug(f'setting group ownership on {projectdir} to {args.chgrp}')
                    shutil.chown(projectdir, group=args.chgrp)
                destdir.mkdir(parents=True, exist_ok=True)
                if args.chmod:
                    logger.debug(f'setting mode on {destdir} to {oct(args.chmod)}')
                    destdir.chmod(args.chmod)
                if args.chgrp:
                    logger.debug(f'setting group ownership on {destdir} to {args.chgrp}')
                    shutil.chown(destdir, group=args.chgrp)

        # compare source and destination files
        logger.info(f'source file {sourcefile}')
        logger.info(f'destination file {destfile}')
        try:
            # skip file if source and destination files are different
            if not filecmp.cmp(sourcefile, destfile):
                logger.warning(f'source and destination exist and are not identical')
                continue
            else:
                logger.info(f'source and destination exist and are identical')
        except FileNotFoundError:
            # destination (or source) file does not exist
            pass

        # atomically rename source file to destination
        if args.do_sort:
            try:
                logger.info(f'renaming source to destination')
                if args.confirm:
                    input('press enter to continue')
                sourcefile.rename(destfile)
            except Exception as e:
                logger.exception(e)
                continue

def get_file_basename(ds, session):
    session = get_session_name(ds, '')
    modality = get_modality_name(ds, '')
    series_number = get_series_number(ds, '')
    instance_number = get_instance_number(ds, '')
    sopinstanceuid = get_sop_instance_uid(ds)
    parts = list()
    if session:
        parts.append(session)
    if modality:
        parts.append(modality)
    if series_number:
        parts.append(series_number)
    if instance_number:
        parts.append(instance_number)
    parts.append(sopinstanceuid)
    basename = '.'.join(parts)
    return f'{basename}.dcm'

def get_sop_instance_uid(ds):
    value = str(ds.get('SOPInstanceUID', '')).strip()
    if not value:
        raise SOPInstanceUIDError(ds.filename)
    return value

def get_instance_number(ds, default='UNKNWON'):
    return str(ds.get('InstanceNumber', default)).strip()

def get_series_number(ds, default='UNKNWON'):
    return str(ds.get('SeriesNumber', default)).strip()
    
def get_modality_name(ds, default='UNKNOWN'):
    return str(ds.get('Modality', default)).strip()

def get_project_name(ds, default='UNKNOWN', upper=True):
    value = str(ds.get('StudyDescription', default)).strip()
    if not value:
        value = default
    value = re.sub(r'\s+', '_', value)
    if upper:
        return value.upper()
    return value

def get_session_name(ds, default='UNKNOWN'):
    value = str(ds.get('PatientID', '')).strip()
    if not value:
        value = str(ds.get('StudyInstanceUID', '')).strip()
    if not value:
        value = default
    value = re.sub(r'\s+', '_', value)
    return value

class SOPInstanceUIDError(Exception):
    pass

if __name__ == '__main__':
    main()

