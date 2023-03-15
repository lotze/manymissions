# take a list of possible missions and a party definition, and make a csv file of instructions (to be used by make_printable.py)
# tasks have tags for both time of party (kickoff, rolling, finale) and location (seated, intimate)
# if a task has no timing tags, it can happen any time
# if a task has no location tags, it can happen anywhere

import argparse
import csv
from datetime import timedelta
from dateutil import parser
import json
import pandas as pd
import random
import re

def flatten(l):
    return [item for sublist in l for item in sublist]

def get_random_mission(missions, segment):
  # TODO: prioritize missions with the tag over missions without any tags
  available_missions = [mission for mission in missions if len(mission['segment_tags']) == 0 or any([tag in segment['tags'] for tag in mission['segment_tags']])]
  return(random.choice(available_missions))

def get_random_site(sites, mission):
  available_sites = [site for site in sites if len(mission['site_tags']) == 0 or all([tag in site['tags'] for tag in mission['site_tags']])]
  return(random.choice(available_sites))

def make_notecards(missions, party_definition):
  notecards = []
  # notecards per hour
  notecards_per_hour = party_definition['n_attendees'] * party_definition['n_per_hour_per_person']

  # identify valid site and segment tags, and categorize mission tags
  segment_tags = set(flatten([segment['tags'] for segment in party_definition['segments']]))
  site_tags = set(flatten([site['tags'] for site in party_definition['sites']]))
  for mission in missions:
    mission['segment_tags'] = []
    mission['site_tags'] = []
    for tag in mission['tags']:
      if tag in segment_tags:
        mission['segment_tags'].append(tag)
      if tag in site_tags:
        mission['site_tags'].append(tag)

  # for each segment, find a number of tasks based on duration, number of people, available missions
  segment_start_time = parser.parse(party_definition['start_time'])
  for segment in party_definition['segments']:
    duration = pd.Timedelta(segment['duration']).to_pytimedelta()
    notecards_needed = notecards_per_hour * duration.seconds / 3600
    print(f"Segment {str(segment)}, need {notecards_needed}")

    missions_for_segment = []

    while notecards_needed > 0:
      next_mission = get_random_mission(missions, segment)
      missions_for_segment.append(next_mission)
      notecards_needed = notecards_needed - len(next_mission['tasks'])
      missions.remove(next_mission)
      print(f"  adding mission {next_mission['title']}, {len(next_mission['tasks'])} tasks")

    # split mission timing amongst the time roughly evenly
    time_between_missions = duration / len(missions_for_segment)

    # for each chosen mission, make a notecard dict for each task
    sites = party_definition['sites'].copy()
    for i, mission in enumerate(missions_for_segment):
      # choose an appropriate site
      site = get_random_site(sites, mission)
      # TODO: ensure no overlapping sites
      # set the time
      mission_start_time = segment_start_time + time_between_missions * i
      # for each task, compute offset time and add to the list of all notecards
      for task in mission['tasks']:
        notecards.append({
          "time": mission_start_time + timedelta(minutes=task['offset_min']),
          "title": mission['title'],
          "instructions": task['instructions']
        })

    segment_start_time = segment_start_time + duration

  return(notecards)


def parse_missions(mission_file):
  with open(mission_file, "r") as f:
    all_lines = f.read()
  mission_strings = all_lines.split("\n\n")
  missions = []
  for mission_string in mission_strings:
    mission_lines = mission_string.split("\n")
    first_line = mission_lines.pop(0)
    tag_section = ""
    title_section = first_line
    sections = re.match(r'^(.*?)\s*//\s*(.*?)$', first_line)
    if sections:
      tag_section = sections.group(1)
      title_section = sections.group(2)
    tags = re.split(r'\s+', tag_section.strip())
    # get multiples from title section
    repeater = re.search(r'\((\d+)x\)', title_section) or re.search(r'\(x(\d+)\)', title_section)
    n_mission_repeats = 1
    if repeater:
      n_mission_repeats = int(repeater.group(1))
      title_section = title_section.replace(repeater.group(0), "").strip()
    # TODO: get time requirements from title section
    for mission_num in range(n_mission_repeats):
      # extract tasks
      tasks = []
      for task_line in mission_lines:
        task_instructions = task_line
        repeater = re.search(r'\((\d+)x\)', task_instructions) or re.search(r'\(x(\d+)\)', task_instructions)
        n_task_repeats = 1
        if repeater:
          n_task_repeats = int(repeater.group(1))
          task_instructions = task_instructions.replace(repeater.group(0), "").strip()
        offset_min = 0
        offset = re.search(r'\(\+?([-0-9]+)m\)', task_instructions)
        if offset:
          offset_min = int(offset.group(1))
          task_instructions = task_instructions.replace(offset.group(0), "").strip()
        if task_instructions:
          for task_num in range(n_task_repeats):
            tasks.append({
              "instructions": task_instructions,
              "offset_min": offset_min
            })
      missions.append({
        "tags": tags,
        "title": title_section,
        "tasks": tasks
      })
  return(missions)

mission_file = 'birthday_2023_missions.txt'
missions = parse_missions(mission_file)
party_file = 'birthday_2023_party.json'
with open(party_file, "r") as f:
  party_definition = json.load(f)

notecards = make_notecards(missions, party_definition)
notecards = sorted(notecards, key=lambda notecard: notecard['time'])
for notecard in notecards:
  notecard['time'] = notecard['time'].strftime("%I:%M %p").strip("0")

notecard_data_file = re.sub('.json', '.csv', party_file)
fieldnames = notecards[0].keys()
with open(notecard_data_file, 'w', newline='') as csvfile:
  writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
  writer.writeheader()
  for notecard in notecards:
    writer.writerow(notecard)

# output can then be manually adjusted (e.g. in excel/Google Sheets) before being made into a printable file