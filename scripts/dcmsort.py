#!/usr/bin/env python3

import os
import sys
import shutil
import pydicom
import logging
import filecmp
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser

logger = logging.getLogger('dicomsorter')
logging.basicConfig(
    level=logging.INFO
)

def main():
    parser = ArgumentParser()
    parser.add_argument('--base-dir', type=Path, required=True)
    parser.add_argument('--do-sort', action='store_true')
    parser.add_argument('--confirm', action='store_true')
    parser.add_argument('--chmod', type=int, default=504)
    parser.add_argument('--chgrp', type=str)
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logger.setLevel(level)

    if not args.base_dir.exists():
        logger.error(f'directory does not exist {args.base_dir}')
        sys.exit(1)

    for sourcefile in args.base_dir.iterdir():
        if not sourcefile.is_file():
            continue

        # check if the current file is dicom format
        try:
            ds = pydicom.dcmread(sourcefile, stop_before_pixels=True)
            logger.debug(f'found dicom file {sourcefile}')
        except:
            logger.debug(f'skipping file {sourcefile}')
            continue

        # get project name from StudyDescription, or use UNKNOWN
        project = ds.get('StudyDescription', 'UNKNOWN').strip().upper()

        # get session name from PatientID, fallback on StudyInstanceUID, or a timestamp
        session = ds.get('PatientID', None)
        if not session:
            session = ds.get('StudyInstanceUID', None)
        if not session:
            now = datetime.now()
            session = now.isoformat()
        session = session.strip()

        # define destination file
        projectdir = Path(args.base_dir, project)
        destdir = Path(projectdir, session)
        destfile = Path(destdir, sourcefile.name)

        # create destination directory with desired ownership and mode bits
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

        # rename source file to destination
        if args.do_sort:
            try:
                logger.info(f'renaming source to destination')
                if args.confirm:
                    input('press enter to continue')
                sourcefile.rename(destfile)
            except Exception as e:
                logger.exception(e)
                continue

if __name__ == '__main__':
    main()

