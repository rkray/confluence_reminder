#!/usr/bin/env python3
# author: René Kray <rene@kray.info>
# date: 2017-03-5
# purpose: send reminder emails if confluece pages are out dated

import os
from   pprint   import pprint
from   optparse import OptionParser 
from   datetime import datetime,date
import json
import sys        # for eprint needed
import yaml       # sudo apt install python3-yaml
import requests   # sudo apt-get install python3-requests


# little helper function to write error messages to stderr
# usage is similar to the normal print function
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Little helper class to handle meta information of confluence pages
class ConfluencePage():
    def __init__(self,base_url,page_id):
        # geting related meta data to page_id
        r = requests.get(base_url+'/'+str(page_id))
        # transform date from json to python dict
        data=dict(json.loads(r.text))

        # setup the propperties
        self.title       = data['title']
        self.version     = data['version']['number']
        self.reviser     = data['version']['by']['displayName']
        self.webui       = data['_links']['base']+data['_links']['webui']

        last_change = data['version']['when']
        # Confluence Date Format: '2016-09-30T15:06:29.902+02:00'
        # timezone format has to be fixed in the string, because strptime
        # understand the timezone without the colon
        if last_change[-3]==":":
            last_change=last_change[0:-3]+last_change[-2:]

        # parse the date
        self.last_change=datetime.strptime(
            last_change, "%Y-%m-%dT%H:%M:%S.%f%z"
        )

# END of ConfluencePage class

# primary script class
class ConfluenceReminder():
    def __init__(self):
        # defiune defaults here
        self.conf=dict(
            verbose=False,
            configfile = (
                os.environ['HOME']+
                "/."+
                os.path.basename(__file__).replace(".py",".conf")
            )
        )

    def run(self):
        try:
            config = yaml.load(open(self.conf['configfile'], 'r'))
        except yaml.scanner.ScannerError as e:
            eprint("There is a problem in your config file!")
            eprint("{}: {}".format(type(e).__name__, e))
            exit(1)
        except FileNotFoundError as e:
            eprint("{}: {}".format(type(e).__name__, e))
            exit(1)

        self.conf.update(config)

        if (self.conf['verbose'] == False):
            pprint(self.conf)

        pages=self.conf['pages']

        for page in pages:
            cp=ConfluencePage(self.conf['base_url'], int(page['page_id']))
            page_age=(date.today()-cp.last_change.date()).days
            print(cp.title)
            print("  Page age: {age} days. Max age is {max_age} days.".format(
                age=page_age,
                max_age=page['max_age']
                )
            )
            if page_age > page['max_age']:
                print("  This page has to be updated.")
            else:
                print("  This page is up to date.")

        # Format String
        # ('Hi, my name is {name} and my age is {age}\n'.format(name="René", age=45))

    # evaluate commandline arguments and switches
    def get_arguments(self):
        parser = OptionParser()

        parser.add_option(
            "-c", "--configfile",
            dest    = "configfile",
            default = self.conf['configfile'],
            help    = "read configuration from filer")
        parser.add_option(
            "-q", "--quiet",
            action  = "store_false", dest="verbose", default=True,
            help    = "don't print status messages to stdout")

        (options, args) = parser.parse_args()
        # join defaults with optons from command line
        self.conf.update(vars(options))

# END of ConfluenceReminder class

# Run this party only if this file is started as script
if __name__=="__main__":
   cr=ConfluenceReminder()
   cr.get_arguments()
   cr.run()

