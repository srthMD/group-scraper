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
    print("Input a valid Roblox group id or multiple ids separated by a comma. \nType \033[32m\033[5mdone\033[0m to stop prompting ids and run the script.\nType \033[32m\033[5mhelp\033[0m for a list of commands.")
    while True:
        print(">", end=" ")
        user_input = input()
        args = user_input.split(" ")
        match args[0]:
            case "help":
                print("list - Prints a list of all the ids inputted.")
                print("rem <\033[35mid\033[0m> - Removes an id from the input.")
                print("del <\033[35mid\033[0m> - Same as rem.")
            case "done":
                if not group_ids:
                    print("You must input at least one group id!")
                    continue
                return group_ids
            case "list":
                if not group_ids:
                    print("There are no group ids.")
                    continue
                for id in group_ids:
                    print(id)
            case "rem" | "del":
                try:
                    argid = args[1]
                except IndexError:
                    print("ID cannot be blank!")
                    continue

                if argid in group_ids:
                    group_ids.remove(args[1])
                else:
                    print(f"Cannot find {args[1]} in inputted ids.")
                    continue
            case _:
                group_ids = group_ids.union(validate_group_ids(args[0]))
    
def validate_group_ids(id):
    valid_ids = set()

    split_input = str(id).replace(" ", "").split(",")

    for possible_id in split_input:  
        try:
            int(possible_id)
        except ValueError:
            print(f"{possible_id} is not a valid id, ignoring id.")
            continue

        response = requests.get(f"https://groups.roblox.com/v1/groups/{possible_id}")

        if response.status_code == 400:
            print(f"The group id {possible_id} does not exist, ignoring id")
            continue

        valid_ids.add(possible_id)

    return valid_ids

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
