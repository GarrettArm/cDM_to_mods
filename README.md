# How to:

Part of the ingest to Islandora pathway (cdm_xporter -> cDM_to_mods -> [convert_to_islandorabooknews] -> Islandora ingest)

A spreadsheet of source data skips the cdm_xporter step & starts at the cDM_to_mods step.

### Setup

 - Install git and docker-compose as described in the [gnatty repo](https://github.com/lsulibraries/gnatty#if-you-need-dependecies).  

- `git clone https://github.com/lsulibraries/cDM_to_mods`

- Run `docker-compose up --build -d` from this folder. 

### Converting cdm_xporter output to mods
  
  1) Make a mapping_file for each collection.  A mapping file assigns each Dublin Core element to it's MODS equivalent.  Some examples are in ./mappings_files/ .  This file is a 2 column csv file.  Its second column is a template for an xml element, with the word %value% as a placeholder.  Its first column is a keyword matching the "name" of the field (as found in the file "Collection_Fields.json").  The corresponding "nick" value matches the key in the contentDM source json file.

  2) Make an alias_xslt file for each collection.  An alias_xslt file is a list of xslts to run against the rough mods files.  See the examples in ./alias_xslts/  After the xlts run, the mods should be finished valid mods.
  Cara and Mike wrote a number of useful xslt's in the ./xsl/ folder.  But you may also write your own & save it at ./xls/

  3) Copy the source folder from U:/ContentDmData/Cached_Cdm_files/{$alias} to somewhere in this folder.

  5) From this folder, `docker-compose exec cdm_to_mods python3 convert_cdm_to_mods.py {alias} {path/to/Cached_Cdm_files}`
        -this /Cached_Cdm_files needs only metadata.
  
  6) From this folder, `docker-compose exec cdm_to_mods python3 post_cdm_cleanup.py {alias} {path/to/Cached_Cdm_files}`
        -this /Cached_Cdm_files needs metadata+binaries

### Converting a spreadsheet to mods

  1) Make a Mappings sheet in your xslx file; no need for a separate file.  See Xlsx_Template_Prototype/CollectionX.xlsx for an example.
  There are two columns -- Column name from the Metadata sheet + xml element
  A 'null1', 'null2' in place of a column name will result in every mods file holding a hardcoded xml element.

  2) Make an alias_xslt file for each collection.  An alias_xslt file is a list of xslts to run against the rough mods files.  See the examples in ./alias_xslts/  After the xlts run, the mods should be finished valid mods.
  Cara and Mike wrote a number of useful xslt's in the ./xsl/ folder.  But you may also write your own & save it at ./xls/

  3) The Metadata sheet contains all your useful metadata plus the folders & filenames of the source binaries.  Your binaries can be grouped in whatever folder(s), as long as they match what you describe in the spreadsheet.  With one restriction: a compound object's binaries should all be in one folder named after the "Identifier" of the parent object as named in the Spreadsheet.

  4) `docker-compose exec cdm_to_mods python3 convert_xlsx_to_mods.py {path/to/your_spreadsheet.xlsx}`

  5) `docker-compose exec cdm_to_mods python3 post_xlsx_cleanup.py {alias} {root folder with the spreadsheet.xslx & binaries}


## Why the long command

docker-compose  -- the program that runs the virtual machine
exec  -- execute for us please
cdm_to_mods  -- which virtual machine we want to use
python3  -- the program we run inside the virtual machine
\*.py  -- the python script to run
{alias}, {path/to/etc}, etc  -- some info telling the script where our source data is


## What each script does

convert_cdm_to_mods.py and convert_xlsx_to_mods.py:
  - applies the mapping to the sourcedata to create rough mods files.
  - performs xsl transformations to refine the mods.  (using the cDM_to_mods/alias_xlsts/{alias}.txt file)
  - validates each mods record against the mods schema (using schema/mods-3.6.xsd).
  - make sure the count of source items equals output items.
  - complains loudly if anything fails.

  - This step's output can be found in cDM_to_mods/output/{alias}\_simple/final_format and cDM_to_mods/output/{alias}\_compound/final_format.  Seperating simples from compounds facilitates easier uploading into Islandora.

post_cdm_cleanup.py and post_xlsx_cleanup.py:
  - verifies that each object in the collection was converted into a mod file.  
  - copies the binaries from the source_directory with the matching metadata.
  - complains if there is not exactly one {.jp2, .mp3, .mp4, .pdf} for each mods.
  - creates a structure file, which is necessary for Islandora Compound Batch Upload.
  - checks all the mods for access restrictions, and reports those to cDM_to_mods/{alias}\_restrictions.txt  Some collections have user restrictions on items. 
  - packages the items into zips as required by Islandora Batch importer

  - This step's output can be found in cDM_to_mods/Upload_to_Islandora/{alias}

  - These output zips are ready for use in Islandora batch ingests: (simple)[https://github.com/lsulibraries/internal-docs/blob/master/source/simple_object.rst] and (compound)[https://github.com/lsulibraries/internal-docs/blob/master/source/compound_object.rst].

## Last steps, if necessary

  - if you wish to use the Book or Newspaper module in Islandora, one last step is necessary.  The output of cDM_to_mods is a zip file at Upload_to_Islandora.  Feed that zip file to (convert_to_islandorabooknews)[https://github.com/lsulibraries/convert_to_islandorabooknews].  The source must be a simple-pdf collection or a jp2-compound collection.
