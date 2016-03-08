## Social Engineering Vulnerability Scanner

This tool makes use of public web and social information to identify potential social engineering weaknesses visible from an organisation's web presence. 

###Prerequisites

+ Python dependencies are in `requirements.txt`
+ API Keys are required to run various modules of the tool. See the `CREDENTIALS` file for information on gathering these.
+ The web-mining portion of the tool relies on the Stanford NER tool, which is available from [here](http://nlp.stanford.edu/software/CRF-NER.shtml). This needs to be launched as a server, separately to the tool itself. The NER tool requires a modern Java runtime. Once downloaded and unpacked, the command in `NER.sh` should launch the tool with the expected configuration.


###Operation

Launch the tool as
> python vuln_scorer.py --gk [googlekeyfile] --fk [facebookkeyfile] --tk [twitterkeyfile] --lk [linkedinkeyfile] run_name target_url

Where 'run_name' is a label which will be used for this launch and its results, and 'target_url' is the website homepage of the targeted organisation. 

Data collection could take significant amounts of time, so a stable connection is advised.

