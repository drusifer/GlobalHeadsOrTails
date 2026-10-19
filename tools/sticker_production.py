#!/usr/bin/env python3
"""Monitorable detached lanes for the long-running, resumable Rangers art job."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'build/rangers-art'
LANES = {'forward': (8, None), 'middle-a': (2, (400, 700)),
         'middle-b': (2, (700, 900)), 'reverse': (4, None)}


def identity(pid):
    try:
        # Field 22 is process start time, independent of PID reuse.
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return fields[19] if fields[0] != 'Z' else None
    except (OSError, IndexError):
        return None


def live(record):
    return identity(record['pid']) == record['start_time']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'stop', 'clear-quota'])
    parser.add_argument('--lane', choices=LANES, default='forward')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    # Serialize check/start/stop so concurrent invocations cannot duplicate a lane.
    with (WORK / f'production-{args.lane}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        run(args)


def run(args):
    if args.action == 'clear-quota':
        marker = WORK / 'raw/.quota-exhausted'
        if not marker.exists():
            print('No quota marker; no generation was started.')
            return
        report = json.loads((WORK / 'quota-report.json').read_text())
        observed = datetime.fromisoformat(marker.read_text().strip().replace('Z', '+00:00'))
        recorded = datetime.fromisoformat(report['recorded_at'])
        if recorded < observed:
            raise SystemExit('Quota report predates this marker; inspect the latest failure first')
        if datetime.now(timezone.utc).timestamp() < report['resets_at']:
            raise SystemExit(f"Quota has not reset; wait until {report['reset_eastern']}")
        for lane in LANES:
            file = WORK / f'production-{lane}.json'
            if file.exists() and live(json.loads(file.read_text())):
                raise SystemExit(f'Lane still running: {lane}')
        marker.replace(marker.with_name(f'.quota-acknowledged-{report["resets_at"]}'))
        print('Expired quota marker archived; generation remains stopped.')
        return
    state = WORK / f'production-{args.lane}.json'
    record = json.loads(state.read_text()) if state.exists() else None
    if args.action == 'status':
        for lane in LANES:
            file = WORK / f'production-{lane}.json'
            data = json.loads(file.read_text()) if file.exists() else None
            print(lane, 'running' if data and live(data) else 'stopped',
                  f"pid={data['pid']} log={data['log']}" if data else '')
        print('masters:', len(list((WORK / 'raw').glob('nyr-*.png'))), '/ 1162')
        print('Other interactive lanes are monitored separately.')
        return
    if args.action == 'stop':
        if record and live(record):
            if os.getpgid(record['pid']) != record['pid']:
                raise SystemExit('Refusing to signal a different process group')
            os.killpg(record['pid'], signal.SIGTERM)
            print('Stopped verified lane:', args.lane)
        else:
            print('Lane already stopped:', args.lane)
        return
    if record and live(record):
        raise SystemExit('Lane already running; refusing duplicate')
    provider = os.environ.get('ART_BACKEND', 'codex')
    if provider not in {'codex', 'nanobanana', 'agy'}:
        raise SystemExit('ART_BACKEND must be codex, nanobanana, or agy')
    marker = WORK / 'raw/.quota-exhausted'
    if marker.exists():
        report_path = WORK / 'quota-report.json'
        if not report_path.exists():
            raise SystemExit('Quota marker has no provider report; inspect the latest failure before starting a lane')
        report = json.loads(report_path.read_text())
        observed = datetime.fromisoformat(marker.read_text().strip().replace('Z', '+00:00'))
        recorded = datetime.fromisoformat(report['recorded_at'])
        if recorded < observed:
            raise SystemExit('Quota report predates the marker; inspect the latest failure before starting a lane')
        if report.get('provider', 'codex') == provider:
            if datetime.now(timezone.utc).timestamp() < report['resets_at']:
                raise SystemExit(f"{provider} quota has not reset; wait until {report['reset_eastern']}")
            raise SystemExit('Quota expired; use make sticker-production-clear-quota before restarting its provider')
        print(f"Ignoring recorded {report.get('provider', 'codex')} quota for independent {provider} backend")
    available = next(int(line.split()[1]) for line in
                     Path('/proc/meminfo').read_text().splitlines()
                     if line.startswith('MemAvailable:'))
    if available < 1536 * 1024:
        raise SystemExit('Less than 1.5 GiB available; do not add workers')
    parallel, bounds = LANES[args.lane]
    try:
        parallel = int(os.environ.get('ART_PARALLEL', parallel))
    except ValueError as error:
        raise SystemExit('ART_PARALLEL must be an integer from 1 to 8') from error
    if not 1 <= parallel <= 8:
        raise SystemExit('ART_PARALLEL must be an integer from 1 to 8')
    command = ['make', 'MKF_ACTIVE=1', 'sticker-art-generate',
               'STICKER_PACK=rangers-history', f'ART_PARALLEL={parallel}']
    command.append(f'ART_BACKEND={provider}')
    if args.lane == 'reverse':
        command.append('ART_REVERSE=1')
    if bounds:
        catalog = ROOT / 'game_server/src/game_server/sticker_catalog_rangers.json'
        families = json.loads(catalog.read_text())['families'][slice(*bounds)]
        command.append('ART_IDS=' + ','.join(f['id'] for f in families))
    log_path = WORK / f'production-{args.lane}.log'
    with log_path.open('ab') as log:
        child = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
    started = identity(child.pid)
    if started is None:
        raise SystemExit('Lane exited before its identity could be recorded')
    temporary = state.with_suffix('.json.tmp')
    temporary.write_text(json.dumps({'pid': child.pid, 'start_time': started,
                                    'command': command, 'log': str(log_path)}, indent=2) + '\n')
    temporary.replace(state)
    print(f'Started {args.lane}: pid={child.pid}, workers={parallel}, log={log_path}')


if __name__ == '__main__':
    main()
