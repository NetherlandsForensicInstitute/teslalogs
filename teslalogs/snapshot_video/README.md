# Credits
Initial code shared by DamianXVI from www.teslamotorsclub.com.

First shared version [here](https://teslamotorsclub.com/tmc/threads/ap2-0-cameras-capabilities-and-limitations.86430/page-25#post-2131613).

Second version [here](https://teslamotorsclub.com/tmc/threads/ap2-0-cameras-capabilities-and-limitations.86430/page-44#post-2288116).

We rewrote the tool in Python to adapt to the various versions and changing formats encountered in the wild.

# Deleted snapshots
On recent versions, snapshots are likely deleted after a succesful upload to Tesla.
It should be possible to recover at least parts of snapshots using [PhotoRec](https://www.cgsecurity.org/wiki/PhotoRec) and looking for tar archives or gzipped files as the snapshots are stored as **.tgz** files.