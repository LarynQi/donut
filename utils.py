import pandas as pd
import json
import random
import time
import sys

ROSTER_PATH = 'roster.csv'
def read_roster(path=ROSTER_PATH):
    df = pd.read_csv(path)
    return list(zip(df['email'], df['pairs']))

JSON_PATH = 'weights.json'
def read_weights(path=JSON_PATH):
    with open(path, 'r') as f:
        return json.loads(f.read())
    
def write_weights(weights, path=JSON_PATH):
    with open(path, 'w') as f:
        f.write(json.dumps(weights, indent=2))
        
def sync_weights(roster, weights):
    for user in roster:
        email = user[0]
        if email not in weights:
            add_email(email, weights)
    return weights

def verify_weights(weights):
    for email in weights:
        for other_email in weights[email]:
            assert weights[email][other_email] == weights.get(other_email, {}).get(email, 'ERROR'), f'{weights[email][other_email]}, {weights.get(other_email, {}).get(email, "ERROR")}'
    return True

def add_email(email, weights):
    init = {}
    for other_email in weights:
        if email != other_email:
            init[other_email] = 1
            weights[other_email][email] = 1
    weights[email] = init
    
def remove_email(email, weights):
    weights.pop(email)
    for other_email in weights:
        try:
            weights[other_email].pop(email)
        except:
            pass

def copy_weights(weights):
    original_weights = {}
    for email in weights:
        init = {}
        for other_email in weights[email]:
            init[other_email] = weights[email][other_email]
        original_weights[email] = init
    assert weights == original_weights
    assert weights is not original_weights
    for email in weights:
        assert weights[email] == original_weights[email]
        assert weights[email] is not original_weights[email]
    return original_weights

def assign(roster, weights, i=0):
    if i > 500:
        return (), {}
    if i > 100:
        for email in weights:
            for other_email in weights[email]:
                weights[email][other_email] = max(1, weights[email][other_email])
    total = sum(map(lambda p: p[1], roster))
    random.seed(time.time())
    assignments = []
    roster_copy = {}
    original_weights = copy_weights(weights)
    for entry in roster:
        if entry[1] != 0:
            roster_copy[entry[0]] = entry[1]
    while len(roster_copy) > 1:
        p0 = random.choice(list(roster_copy.keys()))
        curr_pop = []
        curr_weights = []
        for other_email in weights[p0]:
            curr_pop.append(other_email)
            if other_email not in roster_copy:
                curr_weights.append(0)
            else:
                curr_weights.append(max(weights[p0][other_email] * roster_copy[other_email], 0))
        try:
            p1 = random.choices(curr_pop, weights=curr_weights, k=1)[0]
            weight_of_p1 = curr_weights[curr_pop.index(p1)]
            curr_weights_view = set(curr_weights)
            retries = 1
            while weight_of_p1 < max(curr_weights_view):
                p1 = random.choices(curr_pop, weights=curr_weights, k=1)[0]
                weight_of_p1 = curr_weights[curr_pop.index(p1)]
                if retries % 20 == 0:
                    print('removed')
                    curr_weights_view.remove(max(curr_weights_view))
        except ValueError:
            print('value errored')
            return assign(roster, original_weights, i=i+1)

        weights[p0][p1] = -1
        weights[p1][p0] = -1
        roster_copy[p0] -= 1
        if roster_copy[p0] == 0:
            roster_copy.pop(p0)
        roster_copy[p1] -= 1
        if roster_copy[p1] == 0:
            roster_copy.pop(p1)
            
        assignments.append((p0, p1))    
        
    if len(roster_copy) == 1:
        last_email = list(roster_copy.keys())[0]
        if roster_copy[last_email] > 1:
            return assign(roster, original_weights, i=i+1) 
        elif i > 100 or (total % 2 == 1 and i > 50):
            verify_weights(weights)
            max_happiness = -1
            max_group = None
            for p0, p1 in assignments:
                if p0 == last_email or p1 == last_email:
                    continue
                happiness = weights[last_email][p0] + weights[last_email][p1]
                if happiness > max_happiness:
                    max_happiness = happiness
                    max_group = (p0, p1)
            p0, p1 = max_group
            weights[last_email][p0] = -1
            weights[p0][last_email] = -1
            weights[last_email][p1] = -1
            weights[p1][last_email] = -1
            
            assignments.remove(max_group)
            assignments.append((p0, p1, last_email))
            print('tripled:', (p0.split('@')[0], p1.split('@')[0], last_email.split('@')[0]))
        else:
            return assign(roster, original_weights, i=i+1)
    for email in weights:
        for other_email in weights[email]:
            if weights[email][other_email] == -1:
                weights[email][other_email] = 0
            elif weights[email][other_email] == 0:
                weights[email][other_email] = 1
            else:
                weights[email][other_email] *= 2
    print(i)
    return assignments, weights
        
def init_roster(names, path=ROSTER_PATH):
    with open(path, 'w') as f:
        f.write('email,pairs\n')
        total = 0
        for name in names:
            if name == names[-1] and False:
                val = 2 - (total % 2)
            else:
                val = random.randint(0, 2)
                total += val
            f.write(f'{name.split(" ")[0].lower()}@berkeley.edu,{val}\n')

def update_roster(email, val, path=ROSTER_PATH):
    df = pd.read_csv(path)
    match = df[df['email'] == email]
    if match.shape[0] == 0:
        df = pd.concat([df, pd.DataFrame([[email, val]], columns=df.columns)], ignore_index=True)
    elif match.shape[0] == 1:
        df.loc[df['email'] == email, 'pairs'] = val
    else:
        print('error', email)
        return False
    df.to_csv(path, index=False)
    return True

NAMES = [
]

if __name__ == '__main__':
    init_roster(NAMES, path='roster2.csv')
    roster = read_roster(path='roster2.csv')
    weights = {}
    weights = sync_weights(roster, weights)
    verify_weights(weights)
    counts = {}
    total = sum(map(lambda p: p[1], roster))
    print(total)
    for _ in range(8):
        assignments, weights = assign(read_roster(path='roster2.csv'), weights)
        print(assignments)
        assigned = set()
        for a in assignments:
            for p in a:
                assigned.add(p)
        for email, pairs in read_roster(path='roster2.csv'):
            if pairs == 0:
                assert email not in assigned
        write_weights(weights)
        if _ != 7:
            for email, val in roster:
                update_roster(email, random.randint(0, 2), path='roster2.csv')
            update_roster('new@berkeley.edu', random.randint(0, 2), path='roster2.csv')
            sync_weights(read_roster('roster2.csv'), weights)
