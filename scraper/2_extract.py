""" MICROSOFT FORUM TICKET SCRAPER 

Website: answers.microsoft.com
Example: 
> python 2_extract.py --language de-de --product windows

"""
import re
import urllib
import urllib.request
import json
import time
from bs4 import BeautifulSoup
import re
import sys
import os
import os.path
import time
import unidecode
import codecs
from requests import get
import uuid
import argparse

# Run arguments
parser = argparse.ArgumentParser()
parser.add_argument("--language", 
                default="de-de",
                type=str,
                help="'en-us' or 'de-de")
parser.add_argument('--product',
                default='list',
                type=str,
                help="['windows', 'msoffice', 'xbox', 'outlook_com', 'skype', 'surface', 'protect', 'edge','ie','musicandvideo']")  
args = parser.parse_args()


# Set params
lang = args.language
productsel = args.product

# Extract text content
def getText(soup):
    texts = []
    try:
        text = soup.find_all("div", "thread-message-content-body-text thread-full-message")
        for item in text:
            texts.append(item.text)
    except:
        texts = ""
    return texts

# Clean text a little bit
def cleanText(text):
    text = text.replace("\r", "").replace("\n", "")
    text = ' '.join(text.split())
    return text

# Title
def getTitle(soup):
    title = soup.find_all("h1", "c-heading-3")[0].text
    title = cleanText(title)
    return title

# Check whether the case has been closed
def getDone(soup, text):
    if soup.find_all("div", "answered-icon-desc"):
        a_done = "true"
    elif not soup.find_all("div", "answered-icon-desc") and len(text) > 1:
        a_done = "false"
    else:
        a_done = ""
    return a_done

# Get username
def getUsernameQuestion(soup):
    name_question = soup.find_all("a", "c-hyperlink message-user-info-link user-name-show-white-space")[0].text
    return name_question

# Get username of answer (not used)
def getUsernameAnswer(soup):
    name_answer = soup.find_all("a", "c-hyperlink message-user-info-link user-name-show-white-space")[1].text
    return name_answer

# Create date of question
def getDateQuestion(soup):
    date_question = soup.find_all("span", "asking-text-asked-on-link")[0].text.replace("\nErstellt am ", "").replace("\nCréé le ", "").replace("\nCreado el ", "").replace("\nCreato il ", "").replace("\n", "")
    return date_question

# Create date of answer
def getDateAnswer(soup):
    date_answer = soup.find_all("span", "asking-text-asked-on-link")[1].text.replace("\nBeantwortet am ", "").replace("\nRépondu le ", "").replace("\nRespondió el ", "").replace("\nRisposta il ", "").replace("\n", "")
    return date_answer

# Get number of same cases
def getSame(soup):
    same = soup.find_all("div", "thread-message-content-footer-message-action-link")[1].text
    same_number = re.findall(r'\d+', same)[0]
    return int(same_number)

# Get helpful score of answer
def getHelp(soup):
    helpful = soup.find_all("p", "c-paragraph-4 message-voting-text vote-message-default")[0].text
    helpful_number = re.findall(r'\d+', helpful)[0]
    return int(helpful_number)

# Get views of post
def getViews(soup):
    views = soup.find_all("span", id="threadQuestionInfoViews")[0].text
    views_number = re.findall(r'\d+', views)[0]
    return int(views_number)

# Get post tags
def getTags(soup, product):
    tags = []
    try:
        tag = soup.find_all("ul", id="threadQuestionInfoAppliesToItems")
        for item in tag:
            subtag = item.find_all("a", "c-hyperlink")
            for subitem in subtag:
                tags.append(subitem.text.replace(', ', '_').replace(' ', '_'))
    except:
        tags = ""
    return f'{product.capitalize()},{",".join(tags)}'

# Put it all together
def scrapeMe(url, product):
    print(f"[URL] - {url}")
    # GET WEBSITE
    try:
        response = get(url)
    except Exception as e:
        print(f"[ERROR] - There is an issue with the respective website -> {e}.")
    html_soup = BeautifulSoup(response.text, 'html.parser')
    fileid = uuid.uuid4().hex
    
    # GET TEXT
    text = getText(html_soup)
    q_text = cleanText(text[0])
    
    # GET META
    q_title = getTitle(html_soup)
    q_user = getUsernameQuestion(html_soup)
    q_date = getDateQuestion(html_soup)
    q_views = getViews(html_soup)
    q_tags = getTags(html_soup, product)
    q_same = getSame(html_soup)
    
    # PACK Q JSON
    question = {}
    question['title'] = q_title
    question['author'] = q_user
    question['createdAt'] = q_date
    question['text'] = q_text
    question['upvotes'] = q_same
    
    # CHECK IF DONE
    a_done = getDone(html_soup, text)
    
    # HANDLE IF NO ANSWER
    if len(text) < 2:
        a_date = ""
        a_text = ""
        a_upvotes = ""
    else:
        a_date = getDateAnswer(html_soup)
        a_text = cleanText(text[1])
        try:
            a_upvotes = a_upvotes = getHelp(html_soup)
        except:
            a_upvotes = 0
          
    # PACK A JSON
    answer = {}
    answer['markedAsAnswer'] = a_done
    answer['createdAt'] = a_date
    answer['text'] = a_text
    try:
        answer['upvotes'] = a_upvotes
    except:
        answer['upvotes'] = 0
    
    # PACK JSON
    data = {'question': question, 'id': fileid, 'views': q_views, 'appliesTo': q_tags, 'url': url, 'language': lang, 'answer': answer}
    content = json.dumps(data, indent=4, separators=(',', ': '), ensure_ascii=False)
    
    # WRITE TO JSON FILE
    with open(f"output-{lang}.json", "a", encoding='utf-8') as file:
        file.write(content+",")
        print(f"[SUCCESS] - File {fileid}\n")

# LOOP THROUGH THE OUTPUT TEXT FILES AND CREATE JSON
## Check mode
if productsel == "list":
    products = ['windows', 'msoffice', 'xbox', 'outlook_com', 'skype', 'surface', 'protect', 'edge', 'musicandvideo', 'msteams', 'microsoftedge']
else:
    products = [productsel]
## Loop through product
for product in products:
    try:
        ### Read File
        docs = codecs.open(f"output-{product}-{lang}.txt", 'r', encoding='utf-8').read()
        ### Prepare Links
        url_temp = re.findall(r'(https?://answers.microsoft.com/' + lang + r'/' + product + r'/forum/[^\s]+)', docs)
        url_temp2 = [s.strip('"') for s in url_temp]
        url_list = [x for x in url_temp2 if not x.endswith('LastReply')]
        ### Drop duplicates
        url_list = list(dict.fromkeys(url_list))
        failed_url = []
        for i, value in enumerate(url_list):
            i += 1
            try:
                print(f'[STATUS] - {product}, {i}/{len(url_list)}.')
                scrapeMe(value, product)
            except Exception as e:
                failed_url.append(value)
                print(f'[ERROR] - Failed to extract {value}.\n')
                continue
        print(f"[DONE] - List for {product} of failed URLs: {failed_url},\n{len(url_list) - len(failed_url)} successfully extracted.")
        os.rename(f"output-{product}-{lang}.txt", f"_output-{product}-{lang}.txt")
    except:
        print(f"[ERROR] - 'output-{product}-{lang}.txt' does not exist.\n")