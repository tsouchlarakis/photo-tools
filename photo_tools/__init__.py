"""Top-level package for Photo Tools."""

__author__ = """Andoni Sooklaris"""
__email__ = 'andoni.sooklaris@gmail.com'

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions


import ast
import exiftool
import logging
import os
import pathlib
import re
import subprocess
import typing
from .utils import find_binary, logger_setup, ensurelist, syscmd, split_at, assert_value_dtype, rename_dict_keys
from collections import defaultdict
from xml.etree import ElementTree


logger = logger_setup(name='photo-tools', level=logging.WARNING)


class EXIF(object):
    """
    Extract and operate on EXIF metadata from a media file or multiple files. Wrapper for
    `exiftool` by Phil Harvey system command.
    """
    def __init__(self, fpath: typing.Union[str, pathlib.Path]):
        self.fpath = ensurelist(fpath)
        self.fpath = [os.path.abspath(f) for f in self.fpath]
        for f in self.fpath:
            assert os.path.isfile(f), f'File "{f}" does not exist'

        self.is_batch = len(self.fpath) > 1
        self.exiftool_bin = find_binary('exiftool', abort=True)
        logger.info(f'Found exiftool binary "{self.exiftool_bin}"')

    def extract(self, method: str='doni', clean_keys: bool=False, clean_values: bool=False):
        """
        Extract EXIF metadata from file or files. Parameter `method` may be one of
        'doni' or 'pyexiftool'. The `clean_*` toggles will apply `self.clean_keys()` and/or
        `self.clean_values()` respectively to the output metadata dictionary.
        """
        assert method in ['doni', 'pyexiftool']

        def split_cl_filenames(fpaths: typing.Union[str, pathlib.Path],
                               char_limit: int,
                               exiftool_bin: typing.Union[str, pathlib.Path]):
            """
            Determine at which point to split list of filenames to comply with command-line
            character limit, and split list of filenames into list of lists, where each sublist
            represents a batch of files to run `exiftool` on, where the entire call to `exiftool`
            for that batch will be under the maximum command-line character limit. Files must
            be broken into batches if there are too many to fit on in command-line command,
            because the `exiftool` syntax is as follows:

            exiftool filename_1 filename_2 filename_3 ... filename_n

            With too many files, the raw length of the call to `exiftool` might be over the
            character limit.
            """
            split_idx = []
            count = 0

            # Get character length of each filename
            str_lengths = [len(x) for x in fpaths]

            # Get indices to split at depending on character limit
            for i in range(len(str_lengths)):
                # Account for two double quotes and a space
                val = str_lengths[i] + 3
                count = count + val
                if count > char_limit - len(exiftool_bin + ' '):
                    split_idx.append(i)
                    count = 0

            # Split list of filenames into list of lists at the indices gotten in
            # the previous step
            return split_at(fpaths, split_idx)

        def etree_to_dict(t):
            """
            Convert XML ElementTree to dictionary.

            Source: https://stackoverflow.com/questions/7684333/converting-xml-to-dictionary-using-elementtree
            """
            d = {t.tag: {} if t.attrib else None}
            children = list(t)

            if children:
                dd = defaultdict(list)
                for dc in map(etree_to_dict, children):
                    for k, v in dc.items():
                        dd[k].append(v)
                d = {t.tag: {k: v[0] if len(v) == 1 else v
                             for k, v in dd.items()}}

            if t.attrib:
                d[t.tag].update(('@' + k, v)
                                for k, v in t.attrib.items())

            if t.text:
                text = t.text.strip()
                if children or t.attrib:
                    if text:
                      d[t.tag]['#text'] = text
                else:
                    d[t.tag] = text

            return d

        def unnest_http_keynames(d):
            """
            Iterate over dictionary and test for key:value pairs where `value` is a
            dictionary with a key name in format "{http://...}". Iterate down until the
            terminal value is retrieved, then return that value to the original key name `key`
            """
            tmpd = {}

            for k, v in d.items():
                while isinstance(v, dict) and len(v) == 1:
                    key = list(v.keys())[0]
                    if re.search(r'\{http:\/\/.*\}', key):
                        v = v[key]
                    else:
                        break

                tmpd[k] = v

            return tmpd

        if method == 'doni':
            if not len(self.fpath):
                return {}

            num_files = len(self.fpath)
            logger.info(f'Extracting EXIF metadata for {num_files} files')

            char_limit = 50000

            file_batches = split_cl_filenames(self.fpath, char_limit, self.exiftool_bin)
            logger.info(f'Split {num_files} file(s) into {len(file_batches)} batch(es)')

            commands = []
            for batch in file_batches:
                cmd = self.exiftool_bin + ' -xmlFormat ' + ' '.join(['"' + f + '"' for f in batch]) + ' ' + '2>/dev/null'
                commands.append(cmd)

            exifd = {}
            for i, cmd in enumerate(commands):
                logger.info(f'Running batch {i+1} of {len(file_batches)} containing {len(file_batches[i])} total files')

                try:
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
                    xmlstring, err = proc.communicate()
                    xmlstring = xmlstring.decode('utf-8')
                except Exception as e:
                    logger.exception(f'Unable to execute system command: {cmd}')
                    raise e

                try:
                    root = ElementTree.fromstring(xmlstring)
                    elist = etree_to_dict(root)
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF']
                    elist = elist['{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description']
                    if isinstance(elist, dict):
                        elist = [elist]

                except Exception as e:
                    logger.info('Unable to coerce ElementTree to dictionary')
                    raise e

                for d in elist:
                    tmpd = {}

                    # Clean dictionary keys in format @{http://...}KeyName
                    for k, v in d.items():
                        new_key = re.sub(r'@?\{.*\}', '', k)
                        tmpd[new_key] = v

                    # Unnest nested dictionary elements with "http://..." as the keys
                    tmpd = unnest_http_keynames(tmpd)

                    fnamekey = os.path.join(tmpd['Directory'], tmpd['FileName'])
                    exifd[fnamekey] = tmpd

                del elist


            if clean_keys:
                exifd = self.clean_keys(exifd)
                logger.info('Cleaned EXIF dictionary keys')

            if clean_values:
                exifd = self.clean_values(exifd)
                logger.info('Cleaned EXIF dictionary values')

            logger.info('EXIF metadata extraction complete')
            return exifd

        elif method == 'pyexiftool':
            with exiftool.ExifTool() as et:
                if self.is_batch:
                    exifd = et.get_metadata_batch(self.fpath)
                else:
                    exifd = et.get_metadata(self.fpath)

            return exifd

    def write(self, attrs: dict):
        """
        Write EXIF attribute(s) on a file or list of files, specified in key:value pairs of
        attr_name: desired_attr_value.
        """
        for k, v in attrs.items():
            self.__is_valid_tag_name__(k)

        tracker = {}
        for fpath in self.fpath:
            for tag_name, tag_value in attrs.items():
                default_cmd = f'{self.exiftool_bin} -overwrite_original -{tag_name}="{str(value)}" "{fpath}"'

                # Handle any special tag_name cases
                if tag_name == 'Keywords':
                    # Must be written in format:
                    #     exiftool -keywords=one -keywords=two -keywords=three FILE
                    # Otherwise, comma-separated keywords will be written as a single string
                    if isinstance(value, str):
                        if ',' in value:
                            value = value.split(', ')

                    if isinstance(value, list):
                        if len(value) > 1:
                            kwd_cmd = ' '.join(['-keywords="' + str(x) + '"' for x in value])

                    if 'kwd_cmd' in locals():
                        cmd = f'{self.exiftool_bin} -overwrite_original {kwd_cmd} "{fpath}"'
                    else:
                        cmd = default_cmd

                else:
                    cmd = default_cmd

                res = syscmd(cmd, encoding='utf-8')

                # Make sure that tag was appropriately set on `fpath`
                if self.__is_valid_tag_message__(res):
                    logger.info(f'File "{fpath}" set tag "{tag_name}" to value "{tag_value}"')
                    tracker[fpath] = True
                else:
                    logger.error(f'File "{fpath}" failed to set tag "{tag_name}" to value "{tag_value}" but exiftool system command did not throw an error')
                    tracker[fpath] = False

        return tracker

    def remove(self, tags: typing.Union[str, list]):
        """
        Remove EXIF attribute from a file or list of files.
        """
        tags = ensurelist(tags)
        for tag in tags:
            self.__is_valid_tag_name__(tag)

        for file in self.fpath:
            logger.info("File: " + file)

            for tag in tags:
                cmd = '{} -overwrite_original -{}= "{}"'.format(self.exiftool_bin, tag, file)

                try:
                    logger.var('cmd', cmd)
                    res = syscmd(cmd, encoding='utf-8')
                    logger.var('res', res)

                    if self.__is_valid_tag_message__(res):
                        logger.info("Success. Tag: %s" % tag)
                    else:
                        logger.error("ExifTool Error. Tag: %s" % tag)
                        logger.debug('ExifTool output: %s' % str(res))

                except Exception as e:
                    logger.exception("Failed. Tag: %s" % tag)
                    raise e

    def clean_values(self, exifd: dict):
        """
        Attempt to coerce EXIF values to Python data structures where possible. Try to coerce
        numerical values to Python int or float datatypes, dates to Python datetime values,
        and so on.

        Example:
            >>> EXIF().clean_values({
            >>>     'sample_int_pos': '+7',
            >>>     'sample_int_neg': '-7',
            >>>     'sample_dt_colon': '2018:02:29 01:28:10',
            >>>     'sample_dt_correct': '2018-02-29 01:28:10',
            >>>     'sample_float': '11.11',
            >>> })
            {
                'sample_int_pos': 7,
                'sample_int_neg': -7,
                'sample_dt_colon': '2018-02-29 01:28:10',
                'sample_dt_correct': '2018-02-29 01:28:10',
                'sample_float': 11.11,
            }
        """
        def detect_dtype(val: typing.Any):
            """
            Wrap `assert_value_dtype()` in the context of EXIF metadata cleaning. Acceptable
            return values are ['bool', 'float', 'int', 'date', 'datetime', 'str'].
            """
            valid_dtypes = ['bool', 'float', 'int', 'datetime', 'date', 'str']
            for dtype in valid_dtypes:
                if dtype == 'str':
                    return dtype
                else:
                    if assert_value_dtype(val, dtype):
                        return dtype

            # 'Otherwise' condition
            return 'str'

        newexifd = {}
        for fpath, d in exifd.items():
            newexifd[fpath] = {}

            for k, v in d.items():
                dtype = detect_dtype(v)
                if dtype in ['bool', 'date', 'datetime', 'int', 'float']:
                    coerced_value = assert_value_dtype(v, dtype, return_coerced_value=True)
                    if v != coerced_value:
                        newexifd[fpath][k] = coerced_value
                        continue

                # Accounts for str values
                newexifd[fpath][k] = v

        return newexifd

    def clean_keys(self, exifd: dict):
        """
        Clean EXIF element names.
        """
        column_map_json_fpath = os.path.join(os.path.dirname(__file__), 'data', 'exif_column_map.json')
        with open(column_map_json_fpath, 'r') as f:
            column_map = ast.literal_eval(f.read())

        newd = {}
        not_found_keys = []

        for fpath, dct in exifd.items():
            newd[fpath] = rename_dict_keys(dct, column_map)
            for exif_key in newd[fpath].keys():
                if exif_key not in column_map.keys() and exif_key not in column_map.values():
                    logger.warning(f'No mapped name found for key {exif_key} in {column_map_json_fpath}, key not renamed and left as-is')
                    not_found_keys.append(exif_key)

        if not_found_keys:
            # Key(s) not in above column map, this means we must rename them manually from
            # ExifKeyName to exif_key_name.
            new_keynames = []
            for key in not_found_keys:
                new_key = ''
                for i, char in enumerate(key):
                    if char == char.upper() and not char.isdigit() and i > 0:
                        new_key += '_' + char
                    else:
                        new_key += char

                # Corrections
                new_key = new_key.lower()
                new_key = new_key.replace('i_d', 'id')

                new_keynames.append(new_key)

            newd[fpath] = rename_dict_keys(newd[fpath], dict(zip(not_found_keys, new_keynames)))

        return newd

    def __is_valid_tag_name__(self, tags: typing.Union[str, list]):
        """
        Check EXIF tag names for illegal characters.
        """
        tags = ensurelist(tags)
        illegal_chars = ['-', '_']
        for tag in tags:
            for char in illegal_chars:
                if char in tag:
                    raise Exception(f'Illegal character "{char}" in tag name "{tag}"')

        return True

    def __is_valid_tag_message__(self, tagmsg: str):
        """
        Determine if EXIF write was successful based on tag message.
        """
        if 'nothing to do' in tagmsg.lower():
            return False
        else:
            return True
