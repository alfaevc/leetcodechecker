import re
import json
import datetime as dt

import requests
import pandas as pd

csrf = '' # COPY BROWSER COOKIE "csrftoken"
session = '' # COPY BROWSER COOKIE "LEETCODE_SESSION"

if csrf == '' or session == '':
    raise NotImplementedError

recentAC_query = 'query recentAcSubmissions($username: String!, $limit: Int!) {\n  recentAcSubmissionList(username: $username, limit: $limit) {\n    id\n    title\n    titleSlug\n    timestamp\n  }\n}\n'
problemdata_query = 'query questionData($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    difficulty\n  }\n}\n'

def graphql(query, variables):
    payload = {
      'query': query,
      'variables': variables
    }
    headers = {
      'referer': 'https://leetcode.com/',
      'x-csrftoken': csrf
    }
    cookies = {
      'csrftoken': csrf
    }
    return requests.post('https://leetcode.com/graphql', json=payload, headers=headers, cookies=cookies).json()

def authenticated_get(link):
    cookies = {
        'csrftoken': csrf,
        'LEETCODE_SESSION': session
    }
    headers = {
        'referer': 'https://leetcode.com/'
    }
    return requests.get(link, cookies=cookies, headers=headers)

if __name__ == '__main__':
    df = pd.read_csv('CMU leetcode 卷王 records - Submission Records.csv')

    users = df.columns[1:].tolist()
    n = len(users)

    profiles = [df.iloc[0,1:].tolist(), df.iloc[1,1:].tolist()]
    leetcode = [None] * n
    codeforces = [None] * n
    for p in profiles:
        for i in range(n):
            if isinstance(p[i], str):
                m = re.match(r'https://leetcode\.com/(.*)/', p[i])
                if m is not None:
                    leetcode[i] = m.groups()[0]
                    continue
                m = re.match(r'https://codeforces\.com/profile/(.*)', p[i])
                if m is not None:
                    codeforces[i] = m.groups()[0]
                    continue
                print(f'WARNING: Unrecognized profile: {p[i]}')

    weekstart = df.loc[df[df.columns[0]] == 'Week17 Sep 19'].index.item()
    starttime = int(dt.datetime(2022,9,19,7,tzinfo=dt.timezone(-dt.timedelta(hours=4))).timestamp())
    endtime = int(dt.datetime(2022,9,26,7,tzinfo=dt.timezone(-dt.timedelta(hours=4))).timestamp())

    with open('allproblems.json', 'r') as f:
        j = json.load(f)
        difficulty = {x['stat']['question__title_slug']: x['difficulty']['level'] for x in j['stat_status_pairs']}

    #import pdb; pdb.set_trace()

    for i in range(n):
        user = users[i]
        lc_name = leetcode[i]
        cf_name = codeforces[i]
        lc_problems = set()
        cf_problems = set()

        if lc_name is not None:
            res = graphql(recentAC_query, {'username': lc_name, 'limit': 16})
            in_range = [x['titleSlug'] for x in res['data']['recentAcSubmissionList'] if starttime <= int(x['timestamp']) < endtime]
            lc_problems.update(in_range)
        if cf_name is not None:
            res = requests.get('https://codeforces.com/api/user.status', params={'handle': cf_name, 'from': 1, 'count': 50}).json()
            in_range = [x['problem']['name'] for x in res['result'] if (x['verdict'] == 'OK' and starttime <= x['creationTimeSeconds'] < endtime)]
            cf_problems.update(in_range)

        for link in df[user].iloc[weekstart:].tolist():
            if isinstance(link, str):
                m = re.match(r'https://leetcode\.com/(.*)submissions/detail/\d*/', link)
                if m is not None:
                    res = authenticated_get(link)
                    searchres = re.search(r"editCodeUrl: '/problems/(.*)/'", res.text)
                    if searchres is not None:
                        lc_problems.add(searchres.groups()[0])
                        continue
                m = re.match(r'https://codeforces\.com/\w*/\d*/submission/\d*', link)
                if m is not None:
                    res = requests.get(link)
                    searchres = re.search(r'title="[A-Z] - (.*)" href', res.text)
                    if searchres is not None:
                        cf_problems.add(searchres.groups()[0])
                        continue
                print(f'WARNING: Unrecognized submission {link}')

        score = 0
        lc_problems_difficulties = [[] for _ in range(3)]

        for problem_name in lc_problems:
            if problem_name not in difficulty:
                res = graphql(problemdata_query, {'titleSlug': problem_name})
                dmap = {'Easy': 1, 'Medium': 2, 'Hard': 3}
                difficulty[problem_name] = dmap[res['data']['question']['difficulty']]
            score += difficulty[problem_name] - 1
            lc_problems_difficulties[difficulty[problem_name]-1].append(problem_name)

        print(f'{user}: score = {score}/5')
        print(f'lc_easy:   {lc_problems_difficulties[0]}')
        print(f'lc_medium: {lc_problems_difficulties[1]}')
        print(f'lc_hard:   {lc_problems_difficulties[2]}')

        print(f'codeforces submissions = {list(cf_problems)}')
        print('\n')



