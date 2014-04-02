#!/usr/bin/env python
# coding: utf-8
#
# Copyright © 2013-2015 RISC OS Open Ltd
#
# Permission to use, copy, modify, distribute, and sell this software and its
# documentation for any purpose is hereby granted without fee, provided that
# the above copyright notice appear in all copies and that both that
# copyright notice and this permission notice appear in supporting
# documentation, and that the name of the copyright holders not be used in
# advertising or publicity pertaining to distribution of the software without
# specific, written prior permission.  The copyright holders make no
# representations about the suitability of this software for any purpose.  It
# is provided "as is" without express or implied warranty.
#
# THE COPYRIGHT HOLDERS DISCLAIM ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS, IN NO EVENT SHALL THE COPYRIGHT HOLDERS BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING
# OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
# SOFTWARE.

import csv
import numpy
import sys

# scipy - if you don't have this, you need to "sudo apt-get install python-numpy python-scipy"
from scipy import stats
from operator import itemgetter
from math import sqrt
from optparse import OptionParser

# scipy's t-test function now outputs an annoying warning about scipy's mean function being deprecated
import warnings
warnings.simplefilter('ignore',DeprecationWarning)

options    = None
min_conf   = 99.0

labels     = [ "L1", "L2", "M", "HT", "VT", "R", "RT" ]
hit_text   = False # Yuck! This is a lot easier in Python 3 using nonlocal
max_outliers = 0

def vprint(str):
    if options.verbose:
        print(str)

def load_csv(file):
    """
    Load a CSV file containing all of the test results for each of the tests.

    This routine very much assumes that the input CSV file contains either empty items
    or numbers (assumed to be floating point). If it hits a cell containing something which
    doesn't evaluate to a float, it will probably fail badly.

    The one exception to the above rule is when the first line of the CSV file contains
    something which doesn't evaluate to a number. In that case, it's assumed to be the
    test name strings (stored in 'labels').
    """
    def tidy_csv(data):
        """
        Strip out empty cells from the CSV and remove leading and trailing spaces on each item, then convert to float.

        'data' is a list of lists. Each sublist element is one of the fields read in from the CSV file.
        """
        global hit_text
        global labels

        hit_text = False

        def number_to_float(idx, s):
            """
            If the string passed into this function can evaluate to a float, do so.
            """
            global hit_text

            if idx == 0:
                try:
                    return float(s)
                except:
                    hit_text = True
                    return s.strip('"')
            else:
                return float(s)

        for idx, values in enumerate(data):
            # Strip leading/trailing spaces from each value
            values = map(lambda s: s.strip(), values)
            # Remove empty values from the list
            values = [x for x in values if x]
            # Convert values to floats
            values = map(lambda s: number_to_float(idx, s), values)
            # Update the list of 'data'
            data[idx] = values

        if hit_text:
            vprint("Found test names in CSV file...")
            vprint(str(data[0]) + "\n")
            labels = data[0]
            del data[0]

        return data

    try:
        fd = open(file, "rb")
        vprint("Load CSV file '" + file + "'")
    except:
        print("Failed to open file '" + file + "'")
        sys.exit(1)
    reader = csv.reader(fd, delimiter=',')
    data   = list(reader)
    data   = tidy_csv(data)
    fd.close()
    return data

def transpose(matrix):
    """
    Switch columns and rows in a 2D array (a list of lists).
    """
    nums = numpy.asarray(matrix)
    #print "shape", nums.shape
    nums = nums.transpose()
    return nums.tolist()

def MAD(row, label):
    """
    Use a calculation of the median of the absolute difference to remove any
    outlying data points from the row.
    """
    global max_outliers
    size   = len(row)
    #print "size", size
    median = numpy.median(row)
    #print "median", median
    diffs  = [abs(x - median) for x in row]
    median = numpy.median(diffs)
    if not median:
        return row
    diffs  = [(x / median) for x in diffs]
    row    = [x for i, x in enumerate(row) if diffs[i] < 5]
    if size != len(row):
        vprint("Removed " + str(size - len(row)) + " outliers from " + label)
    max_outliers = max(max_outliers, size - len(row))

    return row

def stats_for_all_tests(matrix):
    """
    Compute some statistics given a list of the results from each test run ('matrix' is a list of lists).
    """
    def stats_for_test(row):
        """
        Compute some statistics for a single test run ('row' is a list of results).
        """
        nums = numpy.asarray(row)
        #print "row_shape,mean", nums.shape, nums.mean()
        return { "mean" : nums.mean(), "median" : numpy.median(nums), "stddev" : nums.std(ddof=1) }

    return [stats_for_test(j) for i, j in enumerate(matrix)]

def compare(old_stats, old_data, new_stats, new_data):
    """
    Compare two sets of tests and their corresponding statistics and return list of specific results for each test.
    """

    results = []
    idx     = 0

    for old, new in zip(old_stats, new_stats):
        vprint("Computing test " + labels[idx] + "...")
        if options.invert:
            mean_diff = old['mean'] - new['mean']
            pcnt_diff = 100.0 * mean_diff / new['mean']
        else:
            mean_diff = new['mean'] - old['mean']
            pcnt_diff = 100.0 * mean_diff / old['mean']
        (t_value, conf) = stats.ttest_ind(old_data[idx], new_data[idx])
        conf            = 100.0 * (1.0 - conf)

        data = {
                'label' : labels[idx],
                'omean' : old['mean'],
                'ostd'  : old['stddev'],
                'nmean' : new['mean'],
                'nstd'  : new['stddev'],
                'dmean' : mean_diff,
                'dpcnt' : pcnt_diff,
                'tval'  : t_value,
                'conf'  : conf
            }
        results.append(data)
        idx += 1
    return results

if __name__ == "__main__":
    # Parse the options to this program when run from the command line
    usage = "usage: %prog [options] <before-file> <after-file>"
    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--csv',         dest='csv',      default='',       help='Name of output csv file to write numeric results to')
    parser.add_option('-i', '--invert',      dest='invert',   default=False,    help='Invert the sense of the comparison to "lower is better"', action='store_true')
    parser.add_option('-m', '--min-conf',    dest='min_conf', default=min_conf, help='Override the threshold for minimum confidence level (percentage, default ' + str(min_conf) + '%)')
    parser.add_option('-r', '--reverse',     dest='reverse',  default=False,    help='When sorting results, output in reverse (ascending) order', action='store_true')
    parser.add_option('-s', '--significant', dest='short',    default=False,    help='Omit results which are considered to be insignificant', action='store_true')
    parser.add_option('-t', '--test',        dest='test',     default='',       help='Name of the test sequence (optional)')
    parser.add_option('-u', '--unsorted',    dest='unsort',   default=False,    help="Don't sort the results by percentage difference", action='store_true')
    parser.add_option('-v', '--verbose',     dest='verbose',  default=False,    help='Output verbose progress information', action='store_true')
    (options, args) = parser.parse_args()

    print("\nTest of feature '" + options.test + "'\n")

    # We can try to derive the input filenames from the test name, if there is one
    old_file = ""
    new_file = ""
    try:
        old_file = args[0]
        new_file = args[1]
    except:
        pass

    if options.test:
        if not old_file:
            old_file = options.test + ".before.csv"
        if not new_file:
            new_file = options.test + ".after.csv"
    else:
        if not old_file:
            parser.error("CSV file for 'before' results not specified (-b)")
        if not new_file:
            parser.error("CSV file for 'after' results not specified (-a)")

    options.min_conf = float(options.min_conf)

    # Load the input CSV files
    old_data = load_csv(old_file)
    new_data = load_csv(new_file)
    vprint("")

    # Transpose rows and columns
    old_data = transpose(old_data)
    new_data = transpose(new_data)

    # Strip out any outlying data points
    vprint("Check for outliers in 'before' data...")
    old_data = [MAD(row, labels[idx]) for idx, row in enumerate(old_data)]
    vprint("Check for outliers in 'after' data...")
    new_data = [MAD(row, labels[idx]) for idx, row in enumerate(new_data)]
    vprint("")

    # Calculate some statistics for each of the tests
    old_stats = stats_for_all_tests(old_data)
    new_stats = stats_for_all_tests(new_data)

    # Build a list of results for each test
    results = compare(old_stats, old_data, new_stats, new_data)
    vprint("")

    #exit(0)

    # The real output, either to screen or to a CSV file
    fd = None
    if options.csv:
        try:
            fd = open(options.csv, "w")
            vprint("Outputting to file '" + options.csv + "'")
            fd.write(""""test","before mean","before std dev","after mean","after std dev","percent diff","diff mean","confidence","t-value"\n""")
        except:
            print("Failed to open output file '" + options.csv + "'")

    # Output a human-readable version to the console
    max_len = 2 + len(max(labels, key=len))
    max_str = str(max_len)

    fmt = "{0:<" + max_str + "}{1}"
    print(fmt.format(" ", "   Before          After"))
    print(fmt.format(" ", "  Mean StdDev     Mean StdDev   Confidence   Change"))

    #for idx, val in enumerate(labels):
    #    results[idx]['label'] = val

    if not options.unsort:
        results = sorted(results, key=itemgetter('dpcnt'), reverse=not options.reverse)

    for idx, values in enumerate(results):
        # Significance estimate
        sig = ""
        if values['conf'] < options.min_conf:
            sig = "  (insignificant)"

        if not options.short or (values['conf'] >= options.min_conf):
            fmt = "{0:<" + max_str + "}{1:6.1f} {2:6.1f}   {3:6.1f} {4:6.1f}  {5:8.2f}%  {6:+8.1f}%{7}"
            print(fmt.format(values['label'], values['omean'], values['ostd'], values['nmean'], values['nstd'], values['conf'], values['dpcnt'], sig))

        # Output to the CSV file
        if fd:
            outstr = '"%s",%0.6f,%0.6f,%0.6f,%0.6f,%0.6f,%0.6f,%0.6f,%0.6f\n' % \
                (values['label'], values['omean'], values['ostd'], values['nmean'], \
                values['nstd'], values['dpcnt'], values['dmean'], values['conf'], values['tval'])
            fd.write(outstr)

    print("\nAt most {0:d} outliers rejected per test per set.".format(max_outliers))

    if fd:
        fd.close()
