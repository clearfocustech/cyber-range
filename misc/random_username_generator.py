import random
import secrets

###################
# Generate an ansible inventory file .in ini format of random usernames and passwords
#
# First names https://raw.githubusercontent.com/dominictarr/random-name/master/first-names.txt
# Last names https://gist.github.com/craigh411/19a4479b289ae6c3f6edb95152214efc
######################


with open('fnames') as f:
    fnames = f.read().splitlines()

with open('lnames') as f:
    lnames = f.read().splitlines()
i=1
while i<100:
    fname=random.choice(fnames)
    lname=random.choice(lnames)
    passwd=secrets.token_urlsafe(6)
    # Defines the username format as the first 2 letters of the firstname and then the whole last name
    print(fname[0]+fname[1]+lname+" firstname="+fname+" surname="+lname+" password="+passwd+" " )
    i=i+1
