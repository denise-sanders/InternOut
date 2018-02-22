import requests
from bs4 import BeautifulSoup
import operator
from configobj import ConfigObj

config = ConfigObj("config.ini")


my_mini_profile = config["my_mini_profile"]
HOMEPAGE_URL = config["HOMEPAGE_URL"]
LOGIN_URL = config["LOGIN_URL"]
username = config["username"]
password = config["password"]

client = requests.Session()


html = client.get(HOMEPAGE_URL).content
soup = BeautifulSoup(html, "html5lib")
csrf = soup.find(id="loginCsrfParam-login")['value']

login_information = {
    'session_key': username,
    'session_password': password,
    'loginCsrfParam': csrf,
}

client.post(LOGIN_URL, data=login_information)



def getProfileIdentifiers(company, cutoff=20):
    profile_identifiers = set()

    page = 1
    while True:
        url = 'https://www.linkedin.com/search/results/people/?company={}&origin=FACETED_SEARCH&title=Software%20Intern&page={}'.format(company,page)
        try: 
            getProfileIdentifiersFromSearchPage(url, profile_identifiers)
        except ValueError:
            return profile_identifiers
        
        page += 1
        if page > cutoff: # aint nobody got time to search all of boeing's interns
            return profile_identifiers

        


# look for profiles
def getProfileIdentifiersFromSearchPage(url, profile_identifiers):
    search = client.get(url)
    haystack = search.text.split("miniProfile:")
    if search.status_code != 200:
        raise ValueError("No page found to read.")
    found = 0
    for needle_index in range(4,len(haystack)): # if you start earlier you get your own profile. Yuck 
        end_index = haystack[needle_index].find('&')
        parsed_string = haystack[needle_index][:end_index]
        if '.' not in parsed_string and parsed_string != my_mini_profile:
            profile_identifiers.add(parsed_string)
            found += 1
    if found == 0:
        raise ValueError("Reached end of search results")

class Date:
    def __init__(self, month=None, year = None):
        self.month = month
        self.year = year

    # I am choosing not to care if jobs start at the same time. Because it seems unlikely it will be common enough to screw up the data
    def __lt__(self, other): # less than means "before"
        if self.year < other.year or (self.year == other.year and self.month < other.year):
            return True
        else:
            return False

class Job:
    def __init__(self, job_id=None, company=None, title=None, starting_date=Date(1,0)):
        self.startingDate = starting_date # If no date is provided I make it super early. I think you have to give linkedin dates tho.
        self.company = company
        self.title = title
        self.id = job_id

    def __lt__(self, other):
        return self.startingDate < other.startingDate

def parseGrossWebpage(job_text, search_phrase, stop_phrase):
    # I hate that this works
    index = job_text.find(search_phrase) + len(search_phrase)
    end_index = job_text.find(stop_phrase, index)
    string = job_text[index:end_index]
    print("|" + string + "|")
    return string


def seeOtherInternships(profile_identifier, previous, future):
    url = 'https://www.linkedin.com/in/{}'.format(profile_identifier)
    profile_text = (client.get(url)).text 
    job_split = profile_text.split("organizations&quot;") # this is hacktastic because it will break if someone has this text in a job description or somewhere else
    job_descriptions = job_split[1:]
    job_dates = job_split[0]

    jobs = []
    for job_text in job_descriptions:
        job_id = parseGrossWebpage(job_text, profile_identifier + ",", ")")
        title = parseGrossWebpage(job_text, "title&quot;:&quot;", "&quot;")
        company = parseGrossWebpage(job_text, "&quot;companyName&quot;:&quot;", "&quot;")
        
        date_search_end_index = job_dates.find(profile_identifier + ',' + job_id + '),timePeriod,startDate&')
        date_search_length = 124 # I think this is good
        date_text = job_dates[date_search_end_index - date_search_length: date_search_end_index]
        
        print("JOB_DATES\n\n\n")
        print(date_text)
        print("\n\n\n")

        start_date_month = int(parseGrossWebpage(date_text,"quot;month&quot;:",",")[6:])
        start_date_year = int(parseGrossWebpage(date_text,"&quot;year&quot;:",","))
        date = Date(start_date_month, start_date_year)

        print("MONTH " + str(start_date_month))
        print("YEAR " + str(start_date_year))
        jobs.append(Job(job_id, company, title, date))

    jobs.sort()

    before = True
    for job in jobs:
        # this only works if there is a company that matchese the company in the list. At a higher level I can probably remove a candidate if none match.
        if company.lower() in job.company.lower() or job.company.lower() in company.lower(): # is there a way to do less exact comparison?
            before = False
            continue
        if before:
            if "intern" in job.title.lower(): 
                if company in previous:
                    previous[company] += 1
                else:
                    previous[company] = 1
        else:
            if company in future:
                    future[company] += 1
            else:
                future[company] = 1


def createRankOfFrequencies(profile_identifiers):
    """ Algorithm:
        create dictionaries for previous and future
        add data from profiles
        dictionary -> tuples
        sort tuples
        display data
    """
    previous = {} # only will consider companies that the person had the title "intern" at
    future = {} # includes full time and intern
    for profile_identifier in profile_identifiers:
        seeOtherInternships(profile_identifier, previous, future)

    previous_frequencies = list(previous.items())
    future_frequencies = list(future.items())

    previous_frequencies.sort(key=operator.itemgetter(1))
    future_frequencies.sort(key=operator.itemgetter(1))

    return previous_frequencies, future_frequencies


profile_identifiers = getProfileIdentifiers("Microsoft", 5)
#print(profile_identifiers)
#print(len(profile_identifiers))

previous_frequencies, future_frequencies = createRankOfFrequencies(profile_identifiers)
print(previous_frequencies)
print("\n\n\n")
print(future_frequencies)
