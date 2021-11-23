# Yopy
-------
A one file script to check, delete or write yopmail mails from command line

## Requirement
```
pip3 install beautifulsoup4
```
Other requirements should already be installed in a standard linux python3 environment

## Usage

```
./yopy.py --help
usage: yopy.py [-h] [-v] [--show number] [--delete number] [--delete-all] [--send] mail

positional arguments:
  mail             mail address (without the @yopmail.com)

optional arguments:
  -h, --help       show this help message and exit
  -v, --verbose    increase output verbosity
  --show number    show mail with given number
  --delete number  delete mail with given number
  --delete-all     delete all mails in the inbox
  --send           send an mail, reading from stdin
                   Note that the mail must have the form:
                    To: ADRESSE
                    Subject: SUBJECT
                   
                    CONTENT
```

Default usage, without args -> list the mails:
```
$ ./yopy.py mail_test_yopy
0 from:'mail_test_yopy2@yopmail.com', subject:'test2'
1 from:'mail_test_yopy2@yopmail.com', subject:'test1'
```

The first number can be used to show a mail:
```
$ ./yopy.py mail_test_yopy --show 1
From: mail_test_yopy2@yopmail.com
Subject: test1

Does it work ?
```

Or delete one:
```
$ ./yopy.py mail_test_yopy --delete 1
$ ./yopy.py mail_test_yopy
0 from:'mail_test_yopy2@yopmail.com', subject:'test2'
```

To write a mail use redirection from a file or heredoc:
(Works even if the sending mail doesn't exist yet)
```
$ ./yopy.py mail_test_yopy2 --send << EOF
> To: mail_test_yopy
> Subject: test5
> 
> Works fine
> It seems
> EOF

$ ./yopy.py mail_test_yopy
0 from:'mail_test_yopy2@yopmail.com', subject:'test5'
1 from:'mail_test_yopy2@yopmail.com', subject:'test3'
2 from:'mail_test_yopy2@yopmail.com', subject:'test2'

$ ./yopy.py mail_test_yopy --show 0
From: mail_test_yopy2@yopmail.com
Subject: test5

Works fine
It seems

$ ./yopy.py mail_test_yopy --show 1
From: mail_test_yopy2@yopmail.com
Subject: test3

Youpi
```



