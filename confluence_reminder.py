#!/usr/bin/env python3
# author: René Kray <rene@kray.info>
# date: 2017-03-5
# purpose: send reminder emails if confluece pages are out dated

import os
from   pprint   import pprint
from   optparse import OptionParser 
from   datetime import datetime,date
import smtplib
from   email.mime.multipart import MIMEMultipart
from   email.mime.text      import MIMEText
import json
import sys        # for eprint needed
import yaml       # sudo apt install python3-yaml
import requests   # sudo apt-get install python3-requests

# to get the body of a confluence page you have to add
# ?expand=body.storage to the URL
# The body of the page can you find in data["body"]["storage"]["value"]

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

        if (self.conf['verbose'] == True):
            pprint(self.conf)

        pages=self.conf['pages']

        for page in pages:
            cpage=ConfluencePage(self.conf['base_url'], int(page['page_id']))
            page_age=(date.today()-cpage.last_change.date()).days
            if (self.conf['verbose'] == True):
                print(cpage.title)
                print("  Page age: {age} days. Max age is {max_age} days.".format(
                    age=page_age,
                    max_age=page['max_age']
                    )
                )
            if page_age > page['max_age']:
                self.send_email(cpage,page['email'])
                if (self.conf['verbose'] == True):
                    print("  This page has to be updated.")
            else:
                if (self.conf['verbose'] == True):
                    print("  This page is up to date.")

    # This function expect a ConfluecePage object
    def send_email(self,cpage,recipient):
        sender         = self.conf["sender"]
        # Create message container - the correct MIME type is multipart/alternative.
        msg            = MIMEMultipart('alternative')
        msg['Subject'] = "Confluence page is outdated: "+cpage.title
        msg['From']    = sender

        # if there is a list of recipients configured, join them to on string
        if type(recipient) is list:
            msg['To'] = ", ".join(recipient)
        else:
            msg['To'] = recipient

        # Create the body of the message (a plain-text and an HTML version).
        # Maybe the tamplates should be moved out of the script.
        text_template = [
            "Hello!",
            "The confluence page \"{title}\" is outdated.",
            "Last change was at {last_change}.",
            "Please go to <{webui}> and update the page."
        ]
        text=("\n".join(text_template)).format(
            title=cpage.title,
            last_change=cpage.last_change,
            webui=cpage.webui
        )

        html_template = [
            "<html>",
            "  <head></head>",
            "  <body>",
            "    <h1>Hello!</h1>",
            "    <p>The confluence page \"{title}\" is outdated.</p>",
            "    <p>Last change was at {last_change}.</p>",
            "    <p>Please go to the <a href='{webui}'>link</a> and update the page.</p>",
            "  </body>",
            "</html>"
        ]
        html="\n".join(html_template)

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        # Send the message via local SMTP server.
        s = smtplib.SMTP('localhost')
        # sendmail function takes 3 arguments: sender's address, recipient's address
        # and message to send - here it is sent as one string.
        s.sendmail(sender, recipient, msg.as_string())
        s.quit()


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

