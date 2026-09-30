#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from bs4 import BeautifulSoup as BS
from datetime import datetime
from http.client import responses
import re
import requests
import sys

BASE_URL = 'https://yopmail.com/'
hidden_tokens = {'yp':'', 'yj':''}
DEBUG = False

def debug(*args, **kwargs):
    if DEBUG:
        print(*args, file=sys.stderr, **kwargs)

def checkStatusCode(status_code):
    if status_code == 200:
        debug('200: OK')
    else:
        raise RuntimeError("{}: {}".format(status_code, responses[status_code])) from None


class MultiLineFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()  
        return argparse.HelpFormatter._split_lines(self, text, width)


def parse_args():
    parser = argparse.ArgumentParser(formatter_class=MultiLineFormatter)
    parser.add_argument('-v', '--verbose', help='increase output verbosity',
                    action='store_true')
    parser.add_argument('mail', help='mail address (without the @yopmail.com)')
    parser.add_argument('--show', help='show mail with given number', type=int, metavar='number') 
    parser.add_argument('--delete', help='delete mail with given number', type=int, metavar='number')
    parser.add_argument('--delete-all', help='delete all mails in the inbox', action='store_true')
    parser.add_argument('--send', help="R|send an mail, reading from stdin\n"
    "Note that the mail must have the form:\n"
    " To: ADRESSE\n"
    " Subject: SUBJECT\n\n CONTENT" , action='store_true')


    return parser.parse_args()

# Headers sent by the webmail when loading a page inside an iframe
IFRAME_HEADERS = {'Referer': 'https://yopmail.com/en/wm',
    'Sec-Fetch-Dest': 'iframe',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin'}

def GET(session, url, headers=None):
    debug("GET {} ... ".format(url), end='')
    r = session.get(url, headers=headers)
    checkStatusCode(r.status_code)
    return r

def POST(session, url, post_data, headers=None):
    debug("POST {} {} ... ".format(url, post_data))
    r = session.post(url, data=post_data, headers=headers)
    checkStatusCode(r.status_code)
    return r

def main():
    args = parse_args()
    global DEBUG
    DEBUG = args.verbose
    mail = args.mail

    s = requests.session()
    s.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'}

    # Cookies expected by the webmail (refreshed before each request)
    def refresh_cookies():
        s.cookies.set('ytime', datetime.now().strftime('%H:%M'), domain='.yopmail.com')
        s.cookies.set('ywm', mail, domain='.yopmail.com')

    refresh_cookies()

    # Base connection, the login page holds the yp token
    r = GET(s, BASE_URL + 'en/?login=' + mail)

    # Getting yp
    debug("Getting hidden token... ", end='')
    yp_input = BS(r.text, features='html.parser').find('input', id='yp')
    if yp_input is None or not yp_input.get('value'):
        raise RuntimeError("Couldn't find hidden token 'yp'") from None
    hidden_tokens['yp'] = yp_input.get('value')
    debug("yp = {}".format(hidden_tokens['yp']))

    # May need to create the mailbox, the answer is the webmail page
    r = POST(s, BASE_URL + 'en/', {'yp': hidden_tokens['yp'], 'login': mail, 'id': ''})

    # Getting the webmail version and script url from the webmail page
    found = re.search(r"var\s+ver='([^']+)'", r.text)
    if not found:
        raise RuntimeError("Couldn't find webmail version") from None
    version = found.group(1)
    found = re.search(r'<script[^>]+src=["\']([^"\']*webmail\.js)["\']', r.text)
    script_url = found.group(1) if found else 'ver/' + version + '/webmail.js'

    # Getting yj
    r = GET(s, BASE_URL + script_url.lstrip('/'))
    debug("Getting hidden token... ", end='')
    found = re.findall(r'[?&]yj=([A-Za-z0-9]+)&v=', r.text)
    if not found:
        raise RuntimeError("Couldn't find hidden token 'yj'") from None
    hidden_tokens['yj'] = found[0]
    debug("yj = {}".format(hidden_tokens['yj']))

    def inbox_url(d='', mail_id=''):
        return (BASE_URL + 'en/inbox?login=' + mail + '&p=1&d=' + d + '&ctrl=&yp='
        + hidden_tokens['yp'] + '&yj=' + hidden_tokens['yj'] + '&v=' + version
        + '&r_c=&id=' + mail_id + '&ad=0')

    # Checking inbox
    refresh_cookies()
    r = GET(s, inbox_url(), headers=IFRAME_HEADERS)

    # inbox internal representation of mails
    inbox = []
    for div in BS(r.text, 'html.parser').find_all('div', attrs={'class':'m'}):
        lmf = list(div.findChildren(attrs={'class':'lmf'}))
        lms = list(div.findChildren(attrs={'class':'lms'}))
        if len(lmf) != 1:
            raise RuntimeError('0 or >1 FROM fields found for one mail!') from None
        if len(lms) != 1:
            raise RuntimeError('0 or >1 SUBJECT fields found for one mail!') from None
        inbox.append({'class':'m','id':div.get('id'),'from':lmf[0].get_text(),
        'subject':lms[0].get_text(),'content':''})

    # no args -> list inbox
    if args.show is None and args.delete is None and not args.delete_all and not args.send:
        for i in range(0, len(inbox)):
            print("{} from:'{}', subject:'{}'".format(i, inbox[i]['from'], inbox[i]['subject']))

    # --show mail_number
    elif args.show is not None and args.show < len(inbox):
        refresh_cookies()
        url = BASE_URL+'en/mail?b='+mail+'&id=m'+inbox[args.show]['id']
        r = GET(s, url, headers=IFRAME_HEADERS)
        print("From: {}".format(inbox[args.show]['from']))
        print("Subject: {}".format(inbox[args.show]['subject']))
        print()
        div = BS(r.text, 'html.parser').find(id='mail')
        if div.strings:
            for line in div.strings:
                print(line)
        elif div.string:
            print(div.string)

    # --delete mail_number
    elif args.delete is not None and args.delete < len(inbox):
        refresh_cookies()
        GET(s, inbox_url(d=inbox[args.delete]['id']), headers=IFRAME_HEADERS)
        del inbox[args.delete]

    # --delete-all
    elif args.delete_all:
        for i in range(0, len(inbox)):
            refresh_cookies()
            GET(s, inbox_url(d=inbox[i]['id']), headers=IFRAME_HEADERS)
        inbox.clear()
    
    # --send
    elif args.send:
        content = []
        for line in sys.stdin:
            content.append(line)
        
        to = ''
        subject = ''
        if content[0][:3] != 'To:':
            raise RuntimeError("Missing 'To:' field") from None
        else:
            to = content[0][3:].strip()
        if content[1][:8] != 'Subject:':
            raise RuntimeError("Missing 'Subject:' field") from None
        else:
            subject = content[1][8:].strip()

        count_void_lines = 0
        for line in content[2:]:
            if len(line.rstrip()) != 0:
                break
            count_void_lines += 1

        mail_content=''
        count_void_lines += 2
        for line in content[count_void_lines:]:
            mail_content += '<div>'+line.strip()+'</div>'

        post_data = {'msgfrom': mail+'@yopmail.com', 'msgto': to, 'msgsubject': subject, 'msgbody': mail_content}
        POST(s, BASE_URL + 'en/writepost', post_data,
            headers={'Referer': BASE_URL + 'en/write?b=' + mail + '&id='})




if __name__ == '__main__':
    main()

