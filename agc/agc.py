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
    with gzip.open(amplicon_file, "rt") as file:
        
        sequence = ""
        for line in file:
            if line[0] == ">":
                if len(sequence) >= minseqlen:
                    yield(sequence)
                line = next(file, None)
                sequence = str(line.strip())
            else:
                sequence += str(line.strip())
        if len(sequence) >= minseqlen:
            yield(sequence)
                


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
            if id_seq not in kmer_dict[kmer]:
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
    """Prend en une liste de s??quences align??es au format ["SE-QUENCE1", "SE-QUENCE2"]
    Retourne le pourcentage d'identite entre les deux."""
    id_nu = 0
    for i in range(len(alignment_list[0])):
        if alignment_list[0][i] == alignment_list[1][i]:
            id_nu += 1
    return round(100.0 * id_nu / len(alignment_list[0]), 2)


def std(data):
    st_dev = statistics.pstdev(data)
    return(st_dev)


def detect_chimera(perc_identity_matrix):
    seq_similar = []
    list_std =[std(elem) for elem in perc_identity_matrix]
    mean_std = statistics.mean(list_std)
    for i in range(0, len(perc_identity_matrix), 1):
        if perc_identity_matrix[i][0] > perc_identity_matrix[i][1]:
            seq_similar.append(0)
        else:
            seq_similar.append(1)
    if mean_std > 5:
        if seq_similar.count(0) >= 1 and seq_similar.count(1) >= 1:
            return(True)
        else:
            return(False)
    else:
	    return(False)


def chimera_removal(amplicon_file, minseqlen, mincount, chunk_size, kmer_size):
    kmer_dict ={}
    sequences = dereplication_fulllength(amplicon_file, minseqlen, mincount)
    # Par d??faut les 2 premi??re seq sont d??finies comme non chim??rique
    no_chim_list = []

    no_chim_list.append(next(sequences, None))
    no_chim_list.append(next(sequences, None))

    for chunk in get_chunks(no_chim_list[0][0], chunk_size):  # M??J du dictionnaire de Kmer sans chim??re
                kmer_dict = get_unique_kmer(kmer_dict, chunk, 0, kmer_size)
    for chunk in get_chunks(no_chim_list[1][0], chunk_size):
                kmer_dict = get_unique_kmer(kmer_dict, chunk, 1, kmer_size)
    
    sequences = list(sequences)
    for i in range(0, len(sequences), 1):
    	parents = search_mates(kmer_dict, sequences[i][0], kmer_size)  # Recherche de parents
    	# Si moins de 2 parents => s??quence consid??r??e comme non-chim??rique
    	if len(parents) < 2:
    	    no_chim_list.append(sequences[i])
    	    for chunk in get_chunks(sequences[i][0], chunk_size):
                kmer_dict = get_unique_kmer(kmer_dict, chunk, i+2, kmer_size)
    	else:
    	    chunks = get_chunks(sequences[i][0], chunk_size)		    # D??coupe s??quence en segments
    	    par_1 = get_chunks(sequences[parents[0]][0], chunk_size)	#
    	    par_2 = get_chunks(sequences[parents[1]][0], chunk_size)	# D??coupe des parents

    	    perc_identity_matrix = []		# Cr??ation d'une matrice d'identit?? de forme
    					                    # 1ere ligne : [segment 1 s??quence 1, segment 1 s??quence 2]
    						                # et ainsi de suite
    	    for j in range(0, len(chunks), 1):
        		ident_1 = nw.global_align(chunks[j], par_1[j], gap_open=-1,
                                                  gap_extend=-1, matrix= match)
        		ident_2 = nw.global_align(chunks[j], par_2[j], gap_open=-1,
                                                  gap_extend=-1, matrix= match)
        		perc_identity_matrix.append([get_identity(ident_1), get_identity(ident_2)])
    	# D??tecte si la s??quence est une chim??re ou non 
    	    if detect_chimera(perc_identity_matrix) == True: # Si oui
                pass
    	    else:					                         # Si non
    	        no_chim_list.append(sequences[i])
    	        for chunk in get_chunks(sequences[i][0], chunk_size):
                        kmer_dict = get_unique_kmer(kmer_dict, chunk, i+2, kmer_size)
    
    for elem in no_chim_list:
        yield(elem)		# G??n??rateur sans s??quences chim??riques 
            
	    

def abundance_greedy_clustering(amplicon_file, minseqlen, mincount, chunk_size, kmer_size):
    
    match = os.path.abspath(os.path.join(os.path.dirname(__file__),"MATCH"))
    seq_len = list(chimera_removal(amplicon_file, minseqlen, mincount, chunk_size, kmer_size))
    OTU_list = [seq_len[0]]
    
    for elem in seq_len:
        for otu in OTU_list:
            alignment_list = nw.global_align(otu[0], elem[0], gap_open=-1,
                                             gap_extend=-1, matrix= match)
            
            if get_identity(alignment_list) < 97:
                OTU_list.append(elem)
    return(OTU_list)

def fill(text, width=80):
    """Split text with a line return to respect fasta format"""
    return os.linesep.join(text[i:i+width] for i in range(0, len(text), width))

def write_OTU(OTU_list, output_file):
    
    with open(output_file, "wt") as save:
        for i in range(0, len(OTU_list), 1):
            n = i+1
            save.write(">OTU_{} occurrence:{}\n{}\n".format(n, OTU_list[i][1], fill(OTU_list[i][0])))

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
    # Liste d'OTU non-chim??riques
    OTU_list = abundance_greedy_clustering(args.amplicon_file, args.minseqlen, args.mincount,
					   args.chunk_size, args.kmer_size)    
    # Ecriture des OTU
    write_OTU(OTU_list, args.output_file)

if __name__ == '__main__':
    main()
