rname=$1
url=$2
echo "Run name: $rname"
echo "Target: $url"
nohup python vuln_scorer.py --gk gplus_cred.config --fk fb_cred.config --lk li_cred.config --tk tw_cred.config $rname $url
