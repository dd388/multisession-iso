#!/usr/bin/env python3

# Dianne's quick hack to make a multisession ISO mountable and readable
# by command-line tools
# inspired by OPF's left-pad technique and her own fruitless efforts
# in trying to modify an already-mastered ISO
# Note: This only preserves the ISO-part of the disk
# There's a comment further down that explains why

# Technique is as follows:
# Write the first 16 sectors as zeros
# Get the path table information, write that out to the new file
# Skip ahead, based on the offset
# Write the rest of the file

import struct
import argparse
import sys
import os

# Take the input and output arguments
parser = argparse.ArgumentParser()
parser.add_argument('inputfile', metavar='[input_file]',
                     help='input multisession ISO file')
parser.add_argument('outputfile', metavar='[output_file]',
                     help='output new ISO file (must not already exist)')
args = parser.parse_args()

# Exit if people do not follow the rules.
if not os.path.exists(os.path.abspath(args.inputfile)):
    sys.exit("Input file does not exist. Quitting.")

if os.path.exists(os.path.abspath(args.outputfile)):
    sys.exit("Output file exists. Quitting.")


# We are going to assume the sector size is 2048
sector_size = 2048 # Technically this might not be true

# Set up the output file
outfile = open(args.outputfile, 'wb')


# Let's begin reading the input file and making the new ISO
osSector = 0
with open(args.inputfile, 'rb') as g:
    while osSector < 16: # Fast fwd through initial sectors
        outfile.write(b'\x00' * sector_size)
        g.read(sector_size)
#        outfile.write(g.read(sector_size)) # Keep all of the original stuff
# It turns out to break the HFS part of a multi-session; which oddly enough
# works just fine as-is. More testing needed for ISO9660/HFS+ multisession
# and ISO9660/UDF multisession variations.
        osSector = osSector + 1

    volSector = g.read(sector_size)
    osSector = osSector + 1

    pathTablesLocs = set()

    while volSector[0] != 255:
        # Get the locations of the path tables
        # Not technically needed for this technique but may be helpful
        #     when debugging.
        pathTablesLocs.add(struct.unpack("<I", volSector[140:144])[0])
        pathTablesLocs.add(struct.unpack("<I", volSector[144:148])[0])
        pathTablesLocs.add(struct.unpack(">I", volSector[148:152])[0])
        pathTablesLocs.add(struct.unpack(">I", volSector[152:156])[0])

        # Go to the next sector
        outfile.write(volSector)
        volSector = g.read(sector_size)
        osSector = osSector + 1

    pathTablesLocs.remove(0)
    pathTablesLocs = list(sorted(pathTablesLocs))

    # Offset should be equal to the first path table extent minus
    #    the current sector
    offset = pathTablesLocs[0] - osSector

    # Get the Set Terminator and write it to the file
    outfile.write(volSector)

    # Fill the space between start of ISO and path tables, sparsely
    outfile.seek(outfile.tell() + (sector_size * offset))

    # Write the rest of the file
    outfile.write(g.read())

# Close the output file
outfile.close()
