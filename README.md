perfcmp
=======

CSV benchmark data analysis script

This script was born out of frustration at the lack of reproducibility of
benchmark results, or more specifically, benchmark results which contained
a random noise or error term larger than the performance improvement that
I was trying to measure.

The field of statistical analysis has already developed analytical
methods for trying to pick out signals like these from noisy
environments. However, these are not always easy to write into
system-level benchmarking programs directly. Such enhancements to
benchmarking programs would also not be able to account for a significant
source of noise that I identified: the fact that repeated runs of a
benchmark function within one invocation of a benchmarking executable
would typically bear a much greater similarity to one another than to any
run within a subsequent invocation of the same executable. The mechanism
behind this remains unknown, although I believe I have ruled out cache
concerns and address space layout randomisation.

To work around this, I typically write a shell script to repeatedly run
the benchmark program and post-process the results into one CSV file,
then feed that file, along with another file representing another series
of runs where something has changed, into this Python script. This
filters out any (assumed spurious) outlying data points in each data set
independently using a median-absolute-difference method, calculates the
mean and sample standard deviation of each, and uses Student's
T-distribution to estimate the confidence with which we can say there has
been a significant change to the timing between the two series of runs
(assuming a Gaussian distribution of errors).

Many benchmarking programs actually produce a series of different
benchmarks on each run. Perfcmp was originally developed for use with the
Pixman library's lowlevel-blt-bench program, so by default it assumes
each run will have produced output for tests named "L1", "L2", "M", "HT",
"VT", "R" and "RT". To override this, simply include the desired test
names, comma-separated, on the first line of each CSV file. Subsequent
lines should contain a comma-separated list of one of more numerical
benchmark results, representing one run of the benchmark program.

For information on the command-line options accepted by perfcmp, use
  $ perfcmp.py -h

Perfcmp is distributed under the terms of the "Old Style with legal
disclaimer" MIT Licence. Python programming by Steve Revill.
