#!/usr/bin/python

import requests
import concurrent.futures   
import time
import os

class GroupOwner:
    name: str
    id: int
    is_verified: bool   
    is_banned: bool
    
    def __init__(self, json_data: dict):
        if json_data is None:
            self.name = "Banned User 🔨"
            self.is_banned = True
        else:
            self.name = json_data.get("username")
            self.id = int(json_data.get("userId"))
            self.is_verified = bool(json_data.get("hasVerifiedBadge"))
            self.is_banned = False

    def to_string(self) -> str:
        if self.is_banned:
            return self.name
        else:
            string = f"{self.name} ({self.id})"
            if self.is_verified:
                string = f"✅{string}"
            return string
        
    def __str__(self):
        return self.to_string()
        
    def __repr__(self):
        return self.__str__()

class Group:
    is_verified: bool
    is_locked: bool
    id: int
    name: str
    owner: GroupOwner

    def __init__(self, json_data: dict):
        self.id = json_data.get("id")
        self.name = json_data.get("name")
        ownr = json_data.get("owner")
        self.owner = GroupOwner(ownr)
        self.is_verified = json_data.get("hasVerifiedBadge")
        self.is_locked = json_data.get("isLocked") != None  

        if self.is_verified:
            self.name = f"✅{self.name}"

        if self.is_locked:
            self.name = f"🔒{self.name}"

    def to_string(self) -> str:
        return f"{self.name} ({self.id}) - Owner: {self.owner}"

    def __str__(self):
        return self.to_string()
        
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Group):
            return self.id == other.id
        return False
    
    def __hash__(self) -> int:
        return self.id # i dont care
        
def link(uri, label):
    parameters = ''

    # OSC 8 ; params ; URI ST <name> OSC 8 ;; ST 
    escape_mask = '\033]8;{};{}\033\\{}\033]8;;\033\\'

    return escape_mask.format(parameters, uri, label)

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
      groups = set()
      try:
          response = requests.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
          if response.status_code == 200:
              data = response.json().get("data")
              
              for group in data:
                  groups.add(Group(group.get("group")))
      except Exception as e:
          # TODO Handle rate limits and errors here
          pass
      return groups

def count_group_ids(members, excluded_groups) -> list[tuple[Group, int]]:
      group_count = {}
      for groups in members:
          for group in groups:
              if group not in excluded_groups:
                  group_count[group] = group_count.get(group, 0) + 1
      return sorted(group_count.items(), key=lambda x: x[1], reverse=True)

def get_user_inputted_groups():
    groups = set[Group]()
    print("Input a valid Roblox group id or multiple ids separated by a comma. \nType \033[32m\033[5mdone\033[0m to stop prompting ids and run the script.\nType \033[32m\033[5mhelp\033[0m for a list of commands.")
    while True:
        print(">", end=" ")
        user_input = input()
        args = user_input.split(" ")
        match args[0]:
            case "help":
                print("list - Prints a list of all the ids inputted.")
                print("rem <\033[35mids\033[0m> - Removes one or more ids separated by commas from the list.")
                print("del <\033[35mids\033[0m> - Same as rem.")
            case "done":
                if not groups:
                    print("You must input at least one group id!")
                    continue
                return groups
            case "list":
                if not groups:
                    print("There are no group ids.")
                    continue
                for group in groups:
                    print(group)
            case "rem" | "del":
                if len(args) == 1:
                    print("ID(s) cannot be blank!")
                    continue
                
                args.pop(0)
                
                mergedids = ""
                for arg in args:
                    mergedids += arg
                ids = mergedids.replace(" ", "").split(",")

                found_groups = set[Group]()
           
                for group in groups:
                    if str(group.id) in ids:
                        found_groups.add(group)

                if not found_groups:
                    print(f"No matches for {ids} in inputted ids.")
                    continue

                for group in found_groups:
                    groups.remove(group)
                    print(f"Removed group: {group}")
            case _:
                groups = groups.union(validate_group_ids(args[0]))
    
def validate_group_ids(ids):
    valid_groups = set[Group]()

    split_input = str(ids).replace(" ", "").split(",")

    with concurrent.futures.ThreadPoolExecutor() as executor:   
        futures = {executor.submit(validate_single_id, possible_id): possible_id for possible_id in split_input}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            valid_groups.add(result)
            print(f"Added group: {result}")

    return valid_groups

def validate_single_id(id):
    try:
        int(id)
    except ValueError:
        print(f"{id} is not a valid id, ignoring id.")
        return None
    
    response = requests.get(f"https://groups.roblox.com/v1/groups/{id}")

    if response.status_code != 200:
        print(f"The group id {id} does not exist or Roblox did not respond, ignoring id.")  
        return None
    
    return Group(response.json())

if __name__ == "__main__":
    all_members = set()
    groups: set[Group] = get_user_inputted_groups()
    for group in groups:
        print(f"Collecting members from group {group}...")
        members = get_group_members(group.id)
        all_members.update(members)
        print(f"Collected {len(members)} members from group {group.id}. Total unique members so far: {len(all_members)}")

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

    group_counts = count_group_ids(members_groups, groups)

    with open(f"{time.strftime("%a-%H_%M_%S-%b-%Y", time.localtime())}.txt", 'w', encoding="utf-8") as outfile:
        for group, count in group_counts:
            outfile.write(f"{group.name} - https://www.roblox.com/groups/{group.id}/x - {count}" + "occurrence. \n" if count == 1 else "occurrences. \n")

    print(f"Processing complete. Results saved to {outfile.name}")
