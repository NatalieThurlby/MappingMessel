# ---
# jupyter:
#   jupytext:
#     formats: ipynb,md
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: messel
#     language: python
#     name: messel
# ---

# # Creating a combined catalogue

# +
# TODO: Check that I have the higher levels of the Thomas catalogue included (that I did not tidy them before reading them in here.) Anything I want to skip should be in `missing.txt`.
# TODO: Create tidy data.
# TODO: Do Named entity recognition on the Titles.
# -

import pandas as pd
import re
from scripts.date_cleaner import tidy_time_df
import os
import numpy as np

# ## Input Data
# The input data to this notebook are two catalogues.
# 1. One larger catalogue, relating to all Oliver Messel items at the time of the Bristol-Turing August 2019 Data Study Group (DSG), including letters between Oliver and Vang Riis-Hansen.
# 1. An smaller catalogue, relating to recently acquired letters between Oliver and Thomas.


dsg_catalogue_fn = '../data/original/dsg/full_catalogue.csv'
output_catalogue_fn = '../data/processed/combined_catalogue.csv'

thomas_catalogue_fn = '../data/original/additional/BTC285MesselLettersCatalogueExport.xlsx'
thomas_catalogue_skip_fn = '../data/original/additional/missing.txt'

dsg_catalogue = pd.read_csv(dsg_catalogue_fn, index_col='Ref_No')
print(dsg_catalogue.head(6))

dsg_catalogue[dsg_catalogue['Title'].str.contains("letter")]

# +
# i=0
# for index in dsg_catalogue.index:
#     if len(index.split('/')) > i:
#         j= index
#         i = len(j.split('/'))
# print(i, j)
# print(dsg_catalogue.loc[j])
# -

# The DSG catalogue contains the following columns:
# * `Level`: Archive catalogues have a hierarchical structure, and are arranged in levels. The levels have names (e.g. `Class`, `Sub-class`) which is what this column contains. The highest level in this data is `Collection`. The hierarchical arrangement of levels can be inferred from the `Ref_No`. `Item`s are the most fundamental/individual unit.
# * `Ref_No`: There is a reference number for each hierarchical level of the collection.
# * `Title`: There is a title for each hierarchical level of the collection, written by the archivist.
# * `Date`: There is a date, or date range (estimated by the archivist) for each level of the collection. These need some processing/tidying as they're not easily computer-readable.
# * `Description`: Description, written by the archivist. Descriptions of higher levels reveal the organisation of the collection, whereas descriptions of `Item`s explain the contents of an individual unit.
# * `Format`: The format refers to what type of item the catalogue entry refers to, e.g. `Written Document`, `DVD`, or `Photograph`. 
# * `Dating_Method`: This explains how the archivist decided the `Date`.
# * `Extent`: The Physical Extent of the level. How many boxes, plans, USB drives, envolopes, etc, the level is made up of.

#| print(dsg_catalogue.Format.unique()) 
# print(dsg_catalogue.Dating_Method.unique())
print(dsg_catalogue.Extent.unique())

thomas_catalogue = pd.read_excel(thomas_catalogue_fn, index_col='Ref_No', usecols=range(10))
print(thomas_catalogue.head(3))

# The Thomas catalogue has the following columns, some column names may be the same as above, but that does not guarantee that they have the same meaning:
# * `Level` - same as DSG catalogue. See above.
# * `Ref_No` - same as DSG catalogue. See above.
# * `Extent` - refers to the digital extent (the number of digital files).
# * `Extent/2` - refers to the physical extent, the same meaning as the `Extent` column from the DSG catalogue. See above.
# * `Title` - same as DSG catalogue. See above.
# * `Date` - Possibly the year the items were added to the collection, all say `2017`.
# * `Date/2` - refers to the dating of the catalogue level, same as `Date` column from the DSG catalogue. See above.
# * `Description` - same as DSG catalogue. See above.
# * `Format` - refers to the digital Format (all `TIFF` files).
# * `Access_Conditions` - some levels of this colletion have access conditions/some parts of some letters are redacted.

# ## Outputs
#
# This notebook uses the input materials to create two processed datasets:
# 1. A large combined catalogue of all Oliver Messel items (letters and otherwise) made by combining the two input data sources. This large catalogue is later used to create the social network. 
# 2. A subsection of this catalogue which relates to only items for which we have letter images. Again, this catalogue contains items between Oliver and Vang Riis-Hansen, and between Oliver and Thomas. 
#
# We would like these output datasets to have the following columns:
# * `Ref_No`: Reference number, from which level can be inferred. Kept the same from both input catalogues.
# * `Description`: Description written by archivist. Kept the same from both input catalogues.
# * `Title`: Title written by archivist. Kept the same from both input catalogues.
# * `Format`: Physical format. Kept the same from the DSG catalogue. The physical format is added by hand for the Thomas catalogue.
# * `Extent`: Physical extent (number of boxes, pages, DVDs, etc). Kept the same from both input catalogues.
# * `Date`: Date as written by archivist.
# * `Date_tidy`: Date in [`datetime64`](https://numpy.org/doc/stable/reference/arrays.datetime.html) format.
# * `Date_status`: Whether the date is known exactly (`exact`), roughly (`circa`), or has been chosen as the central point in a range of possible dates (`centred`). Uncertainty is indicated by `c.`, `c`, or square brackets in the original date written by archivists. Any of these will earn a `circa`.
# * `Letter_recipient`: Letter recipient if level is a letter, NaN otherwise. 
# * `Letter_written_by`: Letter written by if level is a letter, NaN otherwise.
# * `Extent_pages`: Physical extent of pages of letters, excluding envelopes, if level is a letter, NaN otherwise.
# * `Pages_digitised`: Names of letter files used in the OCR/NLP (i.e. not envelopes/postcards) that we have digital copies of, separated by semicolons. 

columns_large = ['Ref_No', 'Description', 'Title', 'Format', 'Date', 'Date_tidy', 'Date_status']  # Larger data set
columns_small = columns_large + ['To', 'From', 'Extent_pages'] # For the smaller dataset relating to images would also like information relating to who the letters were written by and sent to.

# ### Time 
#
# The `Date_tidy` column will contain the date in datetime64 format, while the cleaning required to get this will be described in the `Date_status` column. It will describe whether the date is known exactly (`exact`), roughly (`circa`), or has been chosen as the central point in a range of possible dates (`centred`).
#
# Uncertainty is indicated by `c.`, `c`, or square brackets. Any of these will earn a `circa`.

# ## Data Cleaning

# ### DSG Catalogue items

# #### Levels
# The DSG Catalogue contains descriptions at higher levels than the `Item` level (for example, at the `Collection`, 
# `Class`, `Sub-class`, and `File` levels. Ideally, I'd be able to use the information about the levels that the item belongs to, but I don't want to double-count (or worse) the importance of them (e.g. for the social network graph), counting individual letters and collections thereof.
#
# Therefore, I only use catalogue `Item`s for graphs, but can look for information about what they are in their own description/title (primarily), but also in their parent categpries.

# ### Time

print(dsg_catalogue[dsg_catalogue.Dating_Method.notnull()])

# TODO: Add nd, n.d., n.d, no date to date_cleaner and remove from here.
dsg_catalogue.Date = dsg_catalogue.Date.replace('n.d', 'nd')


dsg_catalogue = tidy_time_df(dsg_catalogue, 'Date')
thomas_catalogue = tidy_time_df(thomas_catalogue, 'Date/2')

# ### Additional Catalogue items

# In the additional catalogue, `Format` describes the file format rather than the type of document. We choose to keep `Format` as the type of document.

# +
skip = []
with open(thomas_catalogue_skip_fn) as skip_f:
    for line in skip_f:
        line = [x.strip() for x in line.strip().split(',')] 
        skip.append(line)
skip = pd.DataFrame(skip, columns=['Ref_No', 'Reason'])
skip.set_index('Ref_No', inplace=True)

assert(len(skip.loc['BTC285/1/2'].Reason) == len('redacted'))
# -

# TODO: Ask Julian about whether this is how these things should be catagorised by Format
skip_dict = {
    'newsclipping':'Printed Document',
    'photo': 'Photograph',
    'postcard': 'Printed Document'
}

format_series = pd.Series(index=thomas_catalogue.index, dtype='object')
for ref_no, row in thomas_catalogue.iterrows():    
    try:
        reason = skip.loc[ref_no].Reason
        if reason == 'redacted':
            format_ = 'Written Document'
        else:
            format_ = skip_dict[reason]
    except KeyError:
        format_ = 'Written Document'  # TODO: Check this is right
    
    format_series.loc[ref_no] = format_
thomas_catalogue.Format = format_series


# ## Data Filtering

# ### Creating the written documents version

dsg_written_documents = dsg_catalogue[dsg_catalogue.Format == 'Written Document']

# The following loads in a hand-chosen list of catalogue items to exclude, either because they are (partly) redacted, or are not letters.

thomas_catalogue_images = thomas_catalogue.copy()
for ref_no in skip.index:
    try:
        thomas_catalogue_images.drop(ref_no, inplace=True)
        print(ref_no)
    except KeyError:
        # If missing, means that I didn't download
        continue
