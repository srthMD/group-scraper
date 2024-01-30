#!/usr/bin/python

import requests
import concurrent.futures
import time

def get_group_members(group_id):
      user_ids = set()
      cursor = None
      while True:
          url = f"https://groups.roblox.com/v1/groups/{group_id}/users"
          params = {'limit': 100, 'cursor': cursor} if cursor else {'limit': 100}
          response = requests.get(url, params=params)
          if response.status_code == 200:
              data = response.json()
              user_ids.update(member['user']['userId'] for member in data['data'])
              cursor = data.get("nextPageCursor")
              if not cursor:
                  break
          else:
              # TODO Handle rate limits
              break
      return user_ids

def get_user_groups(user_id):
      group_ids = []
      try:
          response = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
          if response.status_code == 200:
              groups = response.json()['data']
              group_ids = [group['group']['id'] for group in groups]
      except Exception as e:
          # TODO Handle rate limits and errors here
          pass
      return group_ids

def count_group_ids(members_groups, exclude_group_ids):
      group_count = {}
      for groups in members_groups:
          for gid in groups:
              if gid not in exclude_group_ids:
                  group_count[gid] = group_count.get(gid, 0) + 1
      return sorted(group_count.items(), key=lambda x: x[1], reverse=True)

def get_group_ids():
    group_ids = set()
    print("Input a valid roblox group id or multiple ids seperated by a comma. \nType \033[32m\033[5mdone\033[0m to stop prompting ids and run the script.\nType \033[32m\033[5mhelp\033[0m for a list of commands.")
    while True:
        print(">", end=" ")
        user_input = input()
        match user_input:
            case "help":
                print("list - Prints a list of all the ids inputted.")
            case "done":
                if not group_ids:
                    print("You must input atleast one group id!")
                    continue
                return group_ids
            case "list":
                if not group_ids:
                    print("There are no group ids.")
                    continue
                for id in group_ids:
                    print(id)
            case _:
                # TODO allow for multiple ids to be inputted with commas
                result = validate_group_id(user_input)
                if result[0]:
                    group_ids.add(user_input)
                else:
                    print(result[1])
    
def validate_group_id(id):
    try:
         int(id)
    except ValueError:
        return (False, "Id cannot have letters.")

    response = requests.get(f"https://groups.roblox.com/v1/groups/{id}")

    if response.status_code == 400:
        return (False, "The group id does not exist.")
    
    return (True,)

if __name__ == "__main__":
    all_members = set()
    group_ids = get_group_ids()
    for group_id in group_ids:
        print(f"Collecting members from group {group_id}...")
        members = get_group_members(group_id)
        all_members.update(members)
        print(f"Collected {len(members)} members from group {group_id}. Total unique members so far: {len(all_members)}")

    print("Fetching groups for all aggregated members...")
    start_time = time.time()

    members_processed = 0
    members_groups = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(get_user_groups, user_id): user_id for user_id in all_members}
        for future in concurrent.futures.as_completed(futures):
            members_groups.append(future.result())
            members_processed += 1
            if members_processed % 100 == 0:
                elapsed_time = time.time() - start_time
                estimated_total_time = (elapsed_time / members_processed) * len(all_members)
                remaining_time = estimated_total_time - elapsed_time
                print(f"Processed {members_processed}/{len(all_members)} members. Estimated time remaining: {remaining_time:.2f} seconds.")

    group_counts = count_group_ids(members_groups, exclude_group_ids=group_ids)

    with open(f"{time.strftime("%a-%H_%M_%S-%b-%Y", time.localtime())}.txt", 'w') as outfile:
        for gid, count in group_counts:
            outfile.write(f"https://www.roblox.com/groups/{gid}/x - {count}\n")

    print(f"Processing complete. Results saved to {outfile.name}")
