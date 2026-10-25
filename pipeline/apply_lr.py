#!/usr/bin/env python3
"""Write the cull result into Lightroom via the Pic Agent bridge.

reject  -> pick flag -1 (rejected), rating 0
keep    -> rating 1
picks   -> rating 3 + green label, and added to collection <set>/<name>
Usage: apply_lr.py <run_dir> <jpg_folder> [--collection 百天-精选] [--set "Pic Agent"] [--dry-run]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bridge'))

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('folder')
ap.add_argument('--collection', default='百天-精选'); ap.add_argument('--set', default='Pic Agent')
ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()

cull = json.load(open(os.path.join(a.run_dir, 'cull.json'), encoding='utf-8'))['photos']
picks = {f'JBZ{n}.JPG' for n in open(os.path.join(a.run_dir, 'picks.txt')).read().split()}
by_name = {p['name']: p for p in cull}
missing = sorted(picks - by_name.keys())
bad = sorted(n for n in picks if n in by_name and by_name[n]['decision'] != 'keep')
items = []
for p in cull:
    path = os.path.join(a.folder, p['name'])
    if p['name'] in picks:
        items.append({'path': path, 'rating': 3, 'pick': 0, 'label': 'green'})
    elif p['decision'] == 'reject':
        items.append({'path': path, 'rating': 0, 'pick': -1, 'label': 'none'})
    else:
        items.append({'path': path, 'rating': 1, 'pick': 0, 'label': 'none'})
n3 = sum(1 for i in items if i['rating'] == 3); n1 = sum(1 for i in items if i['rating'] == 1); nr = sum(1 for i in items if i['pick'] == -1)
print(f'total {len(items)}: 3-star+green {n3}, 1-star {n1}, rejected {nr}')
if missing or bad:
    print('picks not in run:', missing, ' picks marked reject:', bad)
json.dump(items, open(os.path.join(a.run_dir, 'lr_plan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
if a.dry_run:
    print('dry run: plan written to', os.path.join(a.run_dir, 'lr_plan.json')); sys.exit(0)

from lr_client import LrBridge
with LrBridge() as lr:
    print('set_meta:', lr.set_meta(items, history='Pic Agent: 百天选片'))
    pick_paths = [i['path'] for i in items if i['rating'] == 3]
    print('collection:', lr.collection_add(a.collection, pick_paths, set_name=a.set, replace=True, show=True))
