#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""OTU clustering"""

import argparse
import sys
import os
import gzip
import statistics
from collections import Counter
# https://github.com/briney/nwalign3
# ftp://ftp.ncbi.nih.gov/blast/matrices/
import nwalign3 as nw

__author__ = "Your Name"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Your Name"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Your Name"
__email__ = "your@email.fr"
__status__ = "Developpement"


def isfile(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments():
    """Retrieves the arguments of the program.
      Returns: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', '-amplicon_file', dest='amplicon_file', type=isfile, required=True, 
                        help="Amplicon is a compressed fasta file (.fasta.gz)")
    parser.add_argument('-s', '-minseqlen', dest='minseqlen', type=int, default = 400,
                        help="Minimum sequence length for dereplication (default 400)")
    parser.add_argument('-m', '-mincount', dest='mincount', type=int, default = 10,
                        help="Minimum count for dereplication  (default 10)")
    parser.add_argument('-c', '-chunk_size', dest='chunk_size', type=int, default = 100,
                        help="Chunk size for dereplication  (default 100)")
    parser.add_argument('-k', '-kmer_size', dest='kmer_size', type=int, default = 8,
                        help="kmer size for dereplication  (default 10)")
    parser.add_argument('-o', '-output_file', dest='output_file', type=str,
                        default="OTU.fasta", help="Output file")
    return parser.parse_args()

def read_fasta(amplicon_file, minseqlen):
    with gzip.open(amplicon_file, "rt") as  file:
        lines = ""
        for line in file:
            if line[0] == ">":
                if len(lines) >= minseqlen:
                    yield(lines)
                lines = ""
            else:
                lines = lines + str(line.strip())
	yield(lines)


def dereplication_fulllength(amplicon_file, minseqlen, mincount):
    list_read = [read for read in read_fasta(amplicon_file, minseqlen)]
    set_read = list(set(list_read))
    count_read = []
    for i in range(0, len(set_read), 1):
        if list_read.count(set_read[i]) >= mincount:
            count_read.append([set_read[i], list_read.count(set_read[i])])
    count_read.sort(key= lambda x: x[1], reverse=True)
    for i in range(0, len(count_read), 1):
        yield(count_read[i])


def get_unique_kmer(kmer_dict, sequence, id_seq, kmer_size):
    for kmer in cut_kmer(sequence, kmer_size):
	if kmer in kmer_dict:
	    kmer_dict[kmer].append(id_seq)
	else:
	   kmer_dict[kmer] = [id_seq] 
    return(kmer_dict)


def search_mates(kmer_dict, sequence, kmer_size):
    parent_list = []
    for kmer in cut_kmer(sequence, kmer_size):
	if kmer in kmer_dict:
	    if len(parent_list) == 0: 
		parent_list = kmer_dict[kmer]
	    else:
		parent_list = parent_list + kmer_dict[kmer]
    commun = Counter(parent_list).most_common(2)
    parents_id = [commun[0][0],commun[1][0]]
    return(parents_id)
	    

def get_unique(ids):
    return {}.fromkeys(ids).keys()


def common(lst1, lst2): 
    return list(set(lst1) & set(lst2))


def get_chunks(sequence, chunk_size):
    """"""
    len_seq = len(sequence)
    if len_seq < chunk_size * 4:
        raise ValueError("Sequence length ({}) is too short to be splitted in 4"
                         " chunk of size {}".format(len_seq, chunk_size))
    return [sequence[i:i+chunk_size] 
              for i in range(0, len_seq, chunk_size) 
                if i+chunk_size <= len_seq - 1]


def cut_kmer(sequence, kmer_size):
    """Cut sequence into kmers"""
    for i in range(0, len(sequence) - kmer_size + 1):
        yield sequence[i:i+kmer_size]

def get_identity(alignment_list):
    """Prend en une liste de séquences alignées au format ["SE-QUENCE1", "SE-QUENCE2"]
    Retourne le pourcentage d'identite entre les deux."""
    id_nu = 0
    for i in range(len(alignment_list[0])):
        if alignment_list[0][i] == alignment_list[1][i]:
            id_nu += 1
    return round(100.0 * id_nu / len(alignment_list[0]), 2)

def chimera_removal(amplicon_file, minseqlen, mincount, chunk_size, kmer_size):
    pass

def abundance_greedy_clustering(amplicon_file, minseqlen, mincount, chunk_size, kmer_size):
    seq_len = list(dereplication_fulllength(amplicon_file, minseqlen, mincount))
    OTU_list = [seq_len[0]]
    for i in range(1, len(seq_len), 1):
        sequence1 = seq_len[i][0]
        j = i + 1
        while j != len(OTU_list)-1:
            sequence2 = OTU_list[j][0]
            alignment_list = nw.global_align(sequence1, sequence2, gap_open=-1,
gap_extend=-1, matrix=os.path.abspath(os.path.join(os.path.dirname(__file__),"MATCH")))
            if get_identity(alignment_list) < 97.0:
                OTU_list.append(seq_len[i])
                j = len(OTU_list)-1
            else:
                j += 1
    return(OTU_list)


def fill(text, width=80):
    """Split text with a line return to respect fasta format"""
    return os.linesep.join(text[i:i+width] for i in range(0, len(text), width))

def write_OTU(OTU_list, output_file):
    with open(output_file, "a") as save:
	for i in range(0, len(OTU_list), 1):
	    n = i+1
	    save.write(">OTU_{} occurrence:{}\n{}".format(n, OTU_list[i][1], fill(OTU_list[i][0])))

#==============================================================
# Main program
#==============================================================
def main():
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    # Votre programme ici


if __name__ == '__main__':
    main()
