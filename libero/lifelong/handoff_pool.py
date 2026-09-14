"""Read verified terminal states from the completed v2 handoff experiment."""
import json
from pathlib import Path
import numpy as np
from libero.lifelong.diagnose_handoff import file_hash


def load_replay_pool(directory, count, current, layout, eval_seeds):
    directory = Path(directory).resolve()
    manifest_path = directory / 'manifest.json'
    previous = json.loads(manifest_path.read_text(encoding='utf-8'))
    if previous['status'] != 'complete' or previous['protocol'] != 'paired_handoff_ablation_v2':
        raise ValueError('Position experiment requires a completed v2 source evaluation')
    if not 1 <= count <= previous['states_collected']:
        raise ValueError('Requested states exceed the saved source pool')
    if not set(eval_seeds).issubset(previous['eval_seeds']):
        raise ValueError('Use evaluation seeds from the source experiment')
    for field in ('tasks', 'policy_budget', 'control_hz', 'torch', 'robosuite', 'mujoco',
                  'training_seeds', 'initial_state_counts', 'init_states_sha256', 'bddl_sha256'):
        if previous[field] != current[field]:
            raise ValueError(f'Source experiment mismatch: {field}')
    for index in ('2', '3'):
        if previous['checkpoints'][index]['sha256'] != current['checkpoints'][index]['sha256']:
            raise ValueError(f'Checkpoint {index} differs from the source experiment')
    wrapper = 'libero/libero/envs/env_wrapper.py'
    if previous['code_sha256'][wrapper] != current['code_sha256'][wrapper]:
        raise ValueError('Environment wrapper differs from the source experiment')
    if json.loads((directory / 'joint_layout.json').read_text(encoding='utf-8')) != layout:
        raise ValueError('Source joint layout differs')
    collection_path = directory / 'collection.jsonl'
    rows = [json.loads(line) for line in collection_path.read_text(encoding='utf-8').splitlines()]
    accepted = [row for row in rows if row['accepted']]
    by_id = {row['state_id']: row for row in accepted}
    if (len(accepted) != previous['states_collected'] or len(by_id) != len(accepted)
            or set(by_id) != set(range(previous['states_collected']))):
        raise ValueError('Source collection has missing or duplicate state IDs')
    pool = []
    for state_id in range(count):
        sample = by_id[state_id]
        if (not sample['initial_valid']
                or not 0 <= sample['initial_index'] < current['initial_state_counts'][0]
                or not 0 <= sample['reference_index'] < current['initial_state_counts'][1]):
            raise ValueError('Invalid initial-state provenance')
        filename = f'state{state_id:03d}.npz'
        if sample['snapshot'] != filename:
            raise ValueError('Unexpected source snapshot filename')
        path = directory / 'snapshots' / filename
        if file_hash(path) != sample['sha256']:
            raise ValueError(f'Source snapshot checksum failed: {filename}')
        with np.load(path, allow_pickle=False) as data:
            state, reference = data['terminal'].copy(), data['reference'].copy()
        shape = (1 + layout['nq'] + layout['nv'],)
        if (state.shape != shape or reference.shape != shape
                or not np.isfinite(state).all() or not np.isfinite(reference).all()):
            raise ValueError('Invalid saved simulator state')
        pool.append((state, reference, sample))
    provenance = dict(directory=str(directory), manifest_sha256=file_hash(manifest_path),
        collection_sha256=file_hash(collection_path), source_states_collected=len(accepted),
        source_collection_attempts=len(rows))
    return pool, provenance
