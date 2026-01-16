'''
test cases for a simple http client.
'''
import logging
import sys
from hw1 import retrieve_url

from subprocess import Popen, PIPE

TEST_CASES = [
    'http://www.example.com',  # most basic example (with no slash) 
    'http://serenegoodfinelight.neverssl.com/online/',  # another basic example
    'http://help.websiteos.com/websiteos/htmlpage.jpg',  # is an image
    'http://go.com/doesnotexist',  # causes 404
    'http://www.httpwatch.com/httpgallery/chunked/chunkedimage.aspx', # chunked encoding
    'http://portquiz.net:8080/' # nonstandard port, even curl should fail to fetch complete data, but autograder won't 
    'http://www.urls.net/' 
]

TEST_CASES_BONUS = [
    'https://www.cs.uic.edu/~ajayk/', # https
    'http://www.académie-française.fr',  # special url
    'http://www.fieggen.com/shoelace',  # redirects to trailing slash
    'https://store.steampowered.com/' # dynamic page
]


def extract_status_code(input_url):
    process = Popen(['curl', '-I','-L', input_url, '--http1.1'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if(len(stdout)==0):
        return None
    stdout_arr = str(stdout).split('HTTP/1.1')
    status_code = int(stdout_arr[-1].split(' ')[1])
    if(status_code==200):
        return 200
    return None

def extract_data(input_url):
    if(extract_status_code(input_url)==None):
        return None
    process = Popen(['curl','-L', input_url, '--http1.1'], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    return stdout

def compare_output(url):
    '''
    compare hw1.py output with requests output for ::url::
    '''
    try:
        # download the same page twice to check for dynamic content
        correct_output = extract_data(url)
        dynamic_output = extract_data(url)
        if correct_output != dynamic_output:
            print("this is a dynamic page, skipping: {}".format(url))
            return
    except requests.RequestException as exc:
        logging.debug(
            "something went wrong downloading the page: %s", type(exc).__name__)
        correct_output = None

    try:
        student_output = retrieve_url(url)
    except Exception as exc: 
        print("uncaught exception ({}) for {}".format(type(exc).__name__, url))
        return
    
    if correct_output == student_output:
        print("correct output for {}".format(url))
    else:
        print("incorrect output for {}".format(url))

def main(args):
    if "--debug" in args:
        logging.basicConfig(level=logging.DEBUG)

    print("Trying Base cases:")

    for testcase in TEST_CASES:
        compare_output(testcase)
    
    print("Trying Bonus cases:")
    
    for testcase in TEST_CASES_BONUS:
        compare_output(testcase)

if __name__ == "__main__":
    main(sys.argv[1:])
