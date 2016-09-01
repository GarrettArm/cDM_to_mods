#! /usr/bin/python3

import os
import sys
from shutil import copyfile
import subprocess
import datetime
import re
import csv
import json
from copy import deepcopy

from lxml import etree as ET
# add mods validation step


def convert_to_mods(alias):
    cdm_data_dir = os.path.realpath(os.path.join('/media/garrett_armstrong/U/Cached_Cdm_files', alias))
    nicks_to_names_dict = make_nicks_to_names(cdm_data_dir)
    mappings_dict = parse_mappings_file(alias)

    cdm_data_filestructure = [(root, dirs, files) for root, dirs, files in os.walk(cdm_data_dir)]
    simple_pointers, cpd_parent_pointers = parse_root_cdm_pointers(cdm_data_filestructure)

    for pointer in simple_pointers:
        target_file = '{}.json'.format(pointer)
        path_to_pointer = [os.path.join(root, target_file)
                           for root, dirs, files in cdm_data_filestructure
                           if target_file in files][0]
        pointer_json = get_cdm_pointer_json(path_to_pointer)
        nicks_texts = parse_cdm_pointer_json(pointer_json)
        propers_texts = convert_nicks_to_propers(nicks_to_names_dict, nicks_texts)
        mods = make_pointer_mods(path_to_pointer, pointer, pointer_json, propers_texts, alias, mappings_dict)
        output_path = os.path.join('output', '{}_simples'.format(alias), 'original_format')
        os.makedirs(output_path, exist_ok=True)
        with open('{}/{}.xml'.format(output_path, pointer), 'w') as f:
            f.write(ET.tostring(mods, pretty_print=True).decode('utf-8'))
    print('finished simples')

    parents_children = dict()
    for cpd_parent in cpd_parent_pointers:
        cpd_parent_etree = ET.parse(os.path.join(cdm_data_dir, 'Cpd', '{}_cpd.xml'.format(cpd_parent)))
        children_pointers = [i.text for i in cpd_parent_etree.findall('./page/pageptr')]
        parents_children[cpd_parent] = children_pointers

    for pointer, _ in parents_children.items():
        path_to_pointer = os.path.join(cdm_data_dir, 'Cpd', '{}.json'.format(pointer))
        pointer_json = get_cdm_pointer_json(path_to_pointer)
        nicks_texts = parse_cdm_pointer_json(pointer_json)
        propers_texts = convert_nicks_to_propers(nicks_to_names_dict, nicks_texts)
        mods = make_pointer_mods(path_to_pointer, pointer, pointer_json, propers_texts, alias, mappings_dict)
        output_path = os.path.join('output', '{}_compounds'.format(alias), 'original_format', pointer)
        os.makedirs(output_path, exist_ok=True)
        with open('{}/MODS.xml'.format(output_path, pointer), 'w') as f:
            f.write(ET.tostring(mods, pretty_print=True).decode('utf-8'))
        copyfile(os.path.join(cdm_data_dir, 'Cpd', '{}_cpd.xml'.format(pointer)), os.path.join(output_path, 'structure.cpd'))

    for parent, children_pointers in parents_children.items():
        for pointer in children_pointers:
            path_to_pointer = os.path.join(cdm_data_dir, 'Cpd', parent, '{}.json'.format(pointer))
            pointer_json = get_cdm_pointer_json(path_to_pointer)
            nicks_texts = parse_cdm_pointer_json(pointer_json)
            propers_texts = convert_nicks_to_propers(nicks_to_names_dict, nicks_texts)
            mods = make_pointer_mods(path_to_pointer, pointer, pointer_json, propers_texts, alias, mappings_dict)
            output_path = os.path.join('output', '{}_compounds'.format(alias), 'original_format', parent, pointer)
            os.makedirs(output_path, exist_ok=True)
            with open('{}/MODS.xml'.format(output_path, pointer), 'w') as f:
                f.write(ET.tostring(mods, pretty_print=True).decode('utf-8'))
    print('finished compounds')


    alias_xslts = read_alias_xslt_file(alias)

    simples_output_dir = os.path.join('output','{}_simples'.format(alias))
    flatten_simple_dir(simples_output_dir)
    run_saxon_simple(simples_output_dir, alias_xslts)

    cpd_output_dir = os.path.join('output', '{}_compounds'.format(alias))
    flatten_cpd_dir(cpd_output_dir)
    run_saxon_cpd(cpd_output_dir, alias_xslts)
    reinflate_cpd_dir(cpd_output_dir)

    print('\n\nYour output files are in:\noutput/{}_simple/final_format/\nand\noutput/{}_compounds/final_format/'.format(alias, alias))


def read_alias_xslt_file(alias):
    with open(os.path.join('alias_xslts', '{}.txt'.format(alias)), 'r') as f:
        return [i for i in f.read().split('\n')]


def flatten_simple_dir(simple_dir):
    source_dir = os.path.join(simple_dir, 'original_format')
    flattened_dir = os.path.join(simple_dir, 'presaxon_flattened')
    os.makedirs(flattened_dir, exist_ok=True)
    for file in os.listdir(source_dir):
        if '.xml' in file:
            copyfile(os.path.join(source_dir, file), os.path.join(flattened_dir, file))


def run_saxon_simple(simple_dir, alias_xslts):
    input_dir = os.path.join(simple_dir, 'presaxon_flattened')
    for xslt in alias_xslts:
        if xslt == 'subjectSplit':
            continue
        print('doing Simple saxon {}'.format(xslt))
        output_dir = os.path.join(simple_dir, xslt)
        os.makedirs(output_dir, exist_ok=True)
        path_to_xslt = os.path.join('xsl', '{}.xsl'.format(xslt))
        subprocess.call(['java',
                         '-jar',
                         'saxon9he.jar',
                         '-s:{}'.format(input_dir),
                         '-xsl:{}'.format(path_to_xslt),
                         '-o:{}'.format(output_dir)])
        input_dir = output_dir
    else:
        os.makedirs(os.path.join(simple_dir, 'post-saxon'), exist_ok=True)
        for file in os.listdir(os.path.join(simple_dir, xslt)):
            copyfile(os.path.join(simple_dir, xslt, file), os.path.join(simple_dir, 'post-saxon', file))
        os.makedirs(os.path.join(simple_dir, 'final_format'), exist_ok=True)
        for file in os.listdir(os.path.join(simple_dir, xslt)):
            copyfile(os.path.join(simple_dir, 'post-saxon', file), os.path.join(simple_dir, 'final_format', file))


def flatten_cpd_dir(cpd_dir):
    source_dir = os.path.join(cpd_dir, 'original_format')
    flattened_dir = os.path.join(cpd_dir, 'presaxon_flattened')
    os.makedirs(flattened_dir, exist_ok=True)
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if ".xml" in file:
                copyfile(os.path.join(root, file), os.path.join(flattened_dir, '{}.xml'.format(root.split('/')[-1])))


def run_saxon_cpd(cpd_dir, alias_xslts):
    input_dir = os.path.join(cpd_dir, 'presaxon_flattened')
    for xslt in alias_xslts:
        # this needs to be discussed, as this subjectSplit xsl breaks Mike's xsl subjectSplit
        if xslt == 'subjectSplit':
            continue
        print('doing Compound saxon {}'.format(xslt))
        output_dir = os.path.join(cpd_dir, xslt)
        os.makedirs(output_dir, exist_ok=True)
        path_to_xslt = os.path.join('xsl', '{}.xsl'.format(xslt))
        subprocess.call(['java',
                         '-jar',
                         'saxon9he.jar',
                         '-s:{}'.format(input_dir),
                         '-xsl:{}'.format(path_to_xslt),
                         '-o:{}'.format(output_dir)])
        input_dir = output_dir
    else:
        os.makedirs(os.path.join(cpd_dir, 'post-saxon'), exist_ok=True)
        for file in os.listdir(os.path.join(cpd_dir, xslt)):
            copyfile(os.path.join(cpd_dir, xslt, file), os.path.join(cpd_dir, 'post-saxon', file))


def reinflate_cpd_dir(cpd_dir):
    original_format = [(root, dirs, files) for root, dirs, files in os.walk(os.path.join(cpd_dir, 'original_format'))]
    for file in os.listdir(os.path.join(cpd_dir, 'post-saxon')):
        for root, dirs, files in original_format:
            if file.split('.')[0] == os.path.split(root)[-1]:
                source_file = os.path.join(cpd_dir, 'post-saxon', file)
                dest_path = root.replace('original_format', 'final_format')
                os.makedirs(dest_path, exist_ok=True)
                dest_file = os.path.join(dest_path, 'MODS.xml')
                copyfile(source_file, dest_file)
    for root, dirs, files in original_format:
        if 'structure.cpd' in files:
            source_file = os.path.join(root, 'structure.cpd')
            dest_file = os.path.join(root.replace('original_format', 'final_format'), 'structure.cpd')
            copyfile(source_file, dest_file)


def make_nicks_to_names(cdm_data_dir):
    rosetta_filepath = os.path.join(cdm_data_dir, 'Collection_Fields.json')
    with open(rosetta_filepath, 'r') as f:
        parsed_rosetta_file = json.loads(f.read())
    return {field['nick']: field['name'] for field in parsed_rosetta_file}


def parse_mappings_file(alias):
    with open('mappings_files/{}.csv'.format(alias), 'r') as f:
        csv_reader = csv.reader(f, delimiter=',')
        return {i: j for i, j in csv_reader}


def parse_root_cdm_pointers(cdm_data_filestructure):
    Elems_ins = [os.path.join(root, file)
                 for root, dirs, files in cdm_data_filestructure
                 for file in files
                 if ("Elems_in_Collection" in file and ".json" in file)]
    simple_pointers, cpd_parent_pointers = [], []
    for file in Elems_ins:
        with open(file, 'r') as f:
            parsed_json_elems_file = json.loads(f.read())
        for i in parsed_json_elems_file['records']:
            pointer = str(i['pointer'] or i['dmrecord'])
            if i['filetype'] == 'cpd':
                cpd_parent_pointers.append(pointer)
            else:
                simple_pointers.append(pointer)
    return (simple_pointers, cpd_parent_pointers)


def get_cdm_pointer_json(filepath):
    with open(filepath, 'r') as f:
        return f.read()


def parse_cdm_pointer_json(pointer_json):
    parsed_alias_json = json.loads(pointer_json)
    return {nick: text for nick, text in parsed_alias_json.items()}


def convert_nicks_to_propers(nicks_to_names_dict, nicks_texts):
    propers_texts = dict()
    for k, v in nicks_texts.items():
        if k in nicks_to_names_dict:
            propers_texts[nicks_to_names_dict[k]] = v
    return propers_texts


def make_pointer_mods(path_to_pointer, pointer, pointer_json, propers_texts, alias, mappings_dict):
    NSMAP = {None: "http://www.loc.gov/mods/v3",
             'mods': "http://www.loc.gov/mods/v3",
             'xsi': "http://www.w3.org/2001/XMLSchema-instance",
             'xlink': "http://www.w3.org/1999/xlink", }
    root_element = ET.Element("mods", nsmap=NSMAP)

    for k, v in mappings_dict.items():
        if k in propers_texts and propers_texts[k]:
            replacement = propers_texts[k]
            for a, b in [('&', '&amp;'),
                         ('"', '&quot;'),
                         ('<', '&lt;'),
                         ('>', '&gt;')]:
                replacement = replacement.replace(a, b)
            v = v.replace("%value%", replacement)
            new_element = ET.fromstring(v)
            root_element.append(new_element)
        elif 'null' in k:
            new_element = ET.fromstring(v)
            if 'CONTENTdmData' in v:
                make_contentDM_elem(new_element[0], pointer, pointer_json, alias)
            root_element.append(new_element)

    id_elem = ET.Element("identifier", attrib={'type': 'uri', 'invalid': 'yes', 'displayLabel': "Migrated From"})
    id_elem.text = 'http://cdm16313.contentdm.oclc.org/cdm/singleitem/collection/{}/id/{}'.format(alias, pointer)
    root_element.append(id_elem)

    merge_same_fields(root_element)
    subject_split(root_element)
    normalize_date(root_element)
    delete_empty_fields(root_element)
    return root_element


def make_contentDM_elem(cdm_elem, pointer, pointer_json, alias):
    alias_elem = ET.Element('alias')
    alias_elem.text = alias
    cdm_elem.append(alias_elem)
    pointer_elem = ET.Element('pointer')
    pointer_elem.text = pointer
    cdm_elem.append(pointer_elem)
    dmGetItemInfo_elem = ET.Element('dmGetItemInfo', attrib={
        'mimetype': "application/json",
        'source': "https://server16313.contentdm.oclc.org/dmwebservices/index.php?q=dmGetItemInfo/{}/{}/json".format(alias, pointer),
        'timestamp': '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), })
    dmGetItemInfo_elem.text = pointer_json
    cdm_elem.append(dmGetItemInfo_elem)


def subject_split(etree):
    for subj_elem in etree.findall('.//subject'):
        for child in subj_elem.getchildren():
            for split in list(child.text.split(';')):
                new_elem = deepcopy(subj_elem)
                for i in new_elem:
                    new_elem.remove(i)
                new_child_elem = deepcopy(child)
                new_child_elem.text = split.strip()
                new_elem.append(new_child_elem)
                subj_elem.getparent().append(new_elem)
        etree.remove(subj_elem)
    for subj_elem in etree.findall('.//subject'):
        new_elem = deepcopy(subj_elem)
        for i in new_elem:
            new_elem.remove(i)
        for child in subj_elem.getchildren():
            for split in list(child.text.split('--')):
                new_child_elem = deepcopy(child)
                new_child_elem.text = split.strip()
                new_elem.append(new_child_elem)
                subj_elem.getparent().append(new_elem)
        etree.remove(subj_elem)


year_month_day = re.compile(r'(\d{4})[/.-](\d{2})[/.-](\d{2})')     # 2013-12-25
year_last = re.compile(r'(\d{2})[/.-](\d{2})[/.-](\d{4})')          # 12-25-2013


def normalize_date(root_elem):
    date_elems = [i for tag in ('dateCaptured', 'recordChangeDate', 'recordCreationDate')
                  for i in root_elem.findall('.//{}'.format(tag))]
    for i in date_elems:
        yearmonthday = year_month_day.search(i.text)
        yearlast = year_last.search(i.text)
        if yearmonthday:
            i.text = yearmonthday.group()
        elif yearlast:
            i.text = '{}-{}-{}'.format(yearlast.group(3),
                                       yearlast.group(1),
                                       yearlast.group(2))


def merge_same_fields(orig_etree):
    for elem in orig_etree:
        for following_elem in elem.itersiblings():
            if elem.tag == following_elem.tag and elem.attrib == following_elem.attrib:
                for child in following_elem.iterchildren():
                    elem.insert(-1, child)
    return orig_etree


def delete_empty_fields(orig_etree):
    elems_list = [i for i in orig_etree]
    for elem in elems_list:
        if not elem.text and len(elem) == 0:
            orig_etree.remove(elem)
    return orig_etree


if __name__ == '__main__':
    alias = sys.argv[1]
    convert_to_mods(alias)
